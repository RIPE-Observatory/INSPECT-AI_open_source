"""
Simplified Google GenAI mock for unit testing.

Provides minimal responses for Google Gemini API calls.
"""

import json
from typing import Any
from unittest.mock import Mock

from tests.unit.constants import TEST_NCT_ID, TEST_PAPER_TITLE

from .base import AsyncBaseMock


class GoogleGenAIMock(AsyncBaseMock):
    """Simplified mock for Google Generative AI client."""

    def __init__(self):
        super().__init__()
        self._default_extraction_response = {
            "trial_id": TEST_NCT_ID,
            "title": TEST_PAPER_TITLE,
            "doi": "10.1234/mock.2024.001",
            "authors": ["Dr. John Doe", "Dr. Jane Smith", "Dr. Bob Johnson"],
            "journal": "Journal of Mock Clinical Medicine",
            "publication_year": 2024,
            "sample_size": 150,
            "study_design": "randomized controlled trial",
            "primary_outcome": "change in disease severity score from baseline to 12 weeks",
            "registry_info": {
                "registry": "ClinicalTrials.gov",
                "identifier": TEST_NCT_ID,
                "registration_date": "2023-12-01",
            },
        }
        self._extraction_response = self._default_extraction_response.copy()

    def reset(self):
        """Reset all mock state including extraction responses."""
        super().reset()
        self._extraction_response = self._default_extraction_response.copy()

    def create_mock_client(self) -> Mock:
        """Create a simplified GenAI client mock."""
        client = Mock()

        # Simplified files API
        files_api = Mock()
        files_api.upload = Mock(side_effect=self._mock_file_upload)
        files_api.delete = Mock(return_value=None)
        client.files = files_api

        # Simplified models API
        models_api = Mock()
        models_api.generate_content = Mock(side_effect=self._mock_generate_content)
        client.models = models_api

        return client

    def _mock_file_upload(self, path: str = None, **kwargs) -> Mock:
        """Simple file upload mock."""
        self.record_call("file_upload", path=path, **kwargs)

        # Return minimal file response
        file_response = Mock()
        file_response.name = "files/mock-file-id"
        file_response.uri = "mock://file/uri"

        return file_response

    def _mock_generate_content(self, contents: Any = None, **kwargs) -> Mock:
        """Simple content generation mock."""
        self.record_call("generate_content", contents=contents, **kwargs)

        # Create minimal response
        response = Mock()
        response.text = json.dumps(self._extraction_response)

        # Minimal candidates structure
        candidate = Mock()
        candidate.content = Mock()
        candidate.content.parts = [Mock()]
        candidate.content.parts[0].text = response.text
        response.candidates = [candidate]

        # Simple usage metadata with proper integer values
        usage_metadata = Mock()
        usage_metadata.total_token_count = 100
        usage_metadata.prompt_token_count = 50
        usage_metadata.candidates_token_count = 50
        response.usage_metadata = usage_metadata

        return response

    def setup_extraction_response(self, data: dict[str, Any]):
        """Set custom extraction response."""
        self._extraction_response = data

    def setup_error_response(self, error_message: str):
        """Set up error response."""

        def mock_error(*args, **kwargs):
            # args and kwargs are required by the signature but not used
            _ = args, kwargs  # Explicitly mark as intentionally unused
            raise Exception(error_message)

        # Override mock methods to raise errors
        self._mock_generate_content = mock_error
        self._mock_file_upload = mock_error


def create_genai_mock() -> GoogleGenAIMock:
    """Create a Google GenAI mock."""
    return GoogleGenAIMock()
