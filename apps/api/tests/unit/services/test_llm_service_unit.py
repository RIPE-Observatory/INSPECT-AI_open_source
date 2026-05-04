"""
Unit tests for the OpenRouter-backed LLM service.

External HTTP calls are mocked; these tests exercise payload construction,
response parsing, validation, and error handling.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

from core.services import llm_service
from tests.unit.constants import UNIT_TEST_MAX_MS


class MockClinicalTrialOutput(BaseModel):
    trial_id: str
    title: str
    authors: list[str] | None = None
    journal: str | None = None
    doi: str | None = None
    sample_size: int | None = None
    study_design: str | None = None


class MockTestOutput(BaseModel):
    test: str


class _MockAsyncClient:
    def __init__(self, response: Mock):
        self.response = response
        self.post = AsyncMock(return_value=response)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _openrouter_response(content: str, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.text = content
    response.json.return_value = {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    return response


@pytest.mark.unit
class TestLLMServiceUnit:
    def test_llm_service_functions_exist(self):
        assert hasattr(llm_service, "get_structured_llm_response")
        assert hasattr(llm_service, "clean_json_response")
        assert hasattr(llm_service, "extract_json_candidate")
        assert hasattr(llm_service, "repair_json_text")
        assert hasattr(llm_service, "fix_null_values")
        assert hasattr(llm_service, "clean_schema_for_gemini")

    @pytest.mark.asyncio
    async def test_structured_llm_response_success(self, tmp_path, monkeypatch, test_timer):
        monkeypatch.setattr(llm_service.settings, "OPENROUTER_API_KEY", "test-key")
        monkeypatch.setattr(llm_service.settings, "OPENROUTER_LLM_MODEL", "test/model")
        monkeypatch.setenv("TEST_MODE", "unit")
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        response = _openrouter_response(
            '{"trial_id":"NCT12345678","title":"Mock Trial","authors":["A"],"doi":"10.1/test"}'
        )
        client = _MockAsyncClient(response)

        with patch("core.services.llm_service.httpx.AsyncClient", return_value=client):
            result = await llm_service.get_structured_llm_response(
                system_prompt="system",
                user_prompt_template="user",
                response_model=MockClinicalTrialOutput,
                pdf_file_path=str(pdf_path),
                max_retries_override=1,
            )

        assert result is not None
        assert result["parsed_info"].trial_id == "NCT12345678"
        assert result["parsed_info"].title == "Mock Trial"
        assert result["token_usage"]["total_tokens"] == 15
        assert result["model_used"] == "test/model"
        client.post.assert_awaited_once()
        payload = client.post.await_args.kwargs["json"]
        assert payload["response_format"]["type"] == "json_object"
        assert payload["messages"][0]["content"][1]["file"]["filename"] == "paper.pdf"

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "OpenRouter response")

    @pytest.mark.asyncio
    async def test_http_error_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(llm_service.settings, "OPENROUTER_API_KEY", "test-key")
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        response = _openrouter_response('{"error":"quota"}', status_code=429)
        response.text = "quota exceeded"
        client = _MockAsyncClient(response)

        with patch("core.services.llm_service.httpx.AsyncClient", return_value=client):
            with pytest.raises(Exception, match="LLM processing failed after retries"):
                await llm_service.get_structured_llm_response(
                    system_prompt="system",
                    user_prompt_template="user",
                    response_model=MockTestOutput,
                    pdf_file_path=str(pdf_path),
                    max_retries_override=1,
                )
        client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_file_handling(self, tmp_path, monkeypatch):
        monkeypatch.setattr(llm_service.settings, "OPENROUTER_API_KEY", "test-key")
        missing_pdf = tmp_path / "missing.pdf"

        with pytest.raises(FileNotFoundError):
            await llm_service.get_structured_llm_response(
                system_prompt="system",
                user_prompt_template="user",
                response_model=MockTestOutput,
                pdf_file_path=str(missing_pdf),
                max_retries_override=1,
            )

    def test_json_cleaning_functions(self, test_timer):
        dirty_json = '```json\n{"key": "value"}\n```'
        assert llm_service.clean_json_response(dirty_json) == '{"key": "value"}'

        mixed = 'prefix {"key": "value"} suffix'
        assert llm_service.extract_json_candidate(mixed) == '{"key": "value"}'

        repaired = llm_service.repair_json_text('{"key": "value",}')
        assert repaired == '{"key": "value"}'

        fixed_data = llm_service.fix_null_values({"valid": "data", "null_field": None})
        assert fixed_data["null_field"] == ""
        assert llm_service.fix_null_values(None) == {}

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "JSON cleaning")

    def test_schema_cleaning(self, test_timer):
        schema = {
            "type": "object",
            "examples": [{"field": "value"}],
            "properties": {
                "field": {
                    "type": "string",
                    "examples": ["value"],
                    "additionalProperties": False,
                }
            },
        }

        cleaned_schema = llm_service.clean_schema_for_gemini(schema)

        assert "examples" not in cleaned_schema
        assert "additionalProperties" not in cleaned_schema["properties"]["field"]
        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Schema cleaning")
