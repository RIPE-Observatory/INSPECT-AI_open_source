import asyncio
import logging
import os
import json
import base64
import re
from typing import Optional, Type, Dict, Any, cast
from pydantic import BaseModel, ValidationError

import httpx
import logfire

from core.config import get_settings
from core.schemas.llm_outputs import LLMTokenUsage

logger = logging.getLogger(__name__)

settings = get_settings()

# Timeouts
DEFAULT_GENERATE_TIMEOUT_SECONDS = float(
    os.getenv("LLM_GENERATE_TIMEOUT_SECONDS", "120")
)

# Max output tokens — set high to avoid truncation on large extractions
MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "131072"))

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


def clean_json_response(response_text: str) -> str:
    """Clean JSON response by removing markdown code blocks."""
    response_text = response_text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    return response_text.strip()


def extract_json_candidate(response_text: str) -> str:
    """Extract the most likely JSON object from a mixed text response."""
    response_text = response_text.strip()

    fenced_match = re.search(
        r"```(?:json)?\s*([\s\S]*?)```", response_text, re.IGNORECASE
    )
    if fenced_match:
        return fenced_match.group(1).strip()

    cleaned = clean_json_response(response_text)
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    start = response_text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", response_text, 0)

    depth = 0
    in_string = False
    escape = False

    for idx in range(start, len(response_text)):
        ch = response_text[idx]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return response_text[start : idx + 1]

    raise json.JSONDecodeError("Unbalanced JSON object", response_text, start)


def repair_json_text(response_text: str) -> str:
    """Apply light, deterministic fixes for near-valid JSON."""
    repaired = response_text.strip()
    repaired = repaired.replace("\r\n", "\n")
    repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
    repaired = repaired.replace("\u2018", "'").replace("\u2019", "'")
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
    return repaired


def fix_null_values(data: Optional[dict]) -> dict:
    """Convert null values to appropriate defaults for pydantic validation."""
    if data is None:
        return {}
    if isinstance(data, dict):
        for key, value in data.items():
            if value is None:
                if (
                    key.endswith("_count")
                    or key == "total_groups"
                    or key == "decimal_places"
                ):
                    data[key] = 0
                else:
                    data[key] = ""
            elif isinstance(value, dict):
                data[key] = fix_null_values(value)
            elif isinstance(value, list):
                data[key] = [
                    fix_null_values(item) if isinstance(item, dict) else item
                    for item in value
                ]
    return data


def clean_schema_for_gemini(schema: dict) -> dict:
    """Remove fields that Gemini/OpenRouter doesn't support from JSON schema."""

    def remove_unsupported_fields(obj: Any) -> Any:
        if isinstance(obj, dict):
            cleaned = {
                k: remove_unsupported_fields(v)
                for k, v in obj.items()
                if k not in ["examples", "additionalProperties"]
            }
            return cleaned
        if isinstance(obj, list):
            return [remove_unsupported_fields(item) for item in obj]
        return obj

    cleaned_schema = remove_unsupported_fields(schema.copy())
    return cast(dict, cleaned_schema)


def calculate_costs(prompt_tokens: int, completion_tokens: int) -> dict:
    """Calculate costs using environment variable pricing."""
    input_cost_per_token = float(os.getenv("GEMINI_2_0_FLASH_INPUT_COST", "0.0000001"))
    output_cost_per_token = float(
        os.getenv("GEMINI_2_0_FLASH_OUTPUT_COST", "0.0000004")
    )

    input_cost = prompt_tokens * input_cost_per_token
    output_cost = completion_tokens * output_cost_per_token
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "cost_breakdown": f"${input_cost:.6f} (input) + ${output_cost:.6f} (output) = ${total_cost:.6f}",
    }


# Keep legacy aliases for backward compatibility
def calculate_gemini_costs(usage_metadata: LLMTokenUsage) -> dict:
    return calculate_costs(
        usage_metadata.prompt_token_count, usage_metadata.candidates_token_count
    )


async def cleanup_job_files(job_id: str, redis_client: Any) -> None:
    """No-op: OpenRouter doesn't require server-side file cleanup."""
    logger.debug(f"cleanup_job_files called for job {job_id} (no-op with OpenRouter)")


async def get_structured_llm_response(
    system_prompt: str,
    user_prompt_template: str,
    response_model: Type[BaseModel],
    pdf_file_path: Optional[str] = None,
    original_filename_for_logging: str = "N/A",
    max_retries_override: int = 3,
    job_id: Optional[str] = None,
    redis_client: Optional[Any] = None,
    use_json_schema: bool = True,
    preserve_nulls: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Get a structured response from an LLM via OpenRouter.
    Handles multimodal (PDF) input with custom retry logic.
    Returns a dictionary with 'parsed_info' (the Pydantic model instance)
    and 'token_usage_info' (LLMTokenUsage or None).
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        logger.error("OPENROUTER_API_KEY not configured")
        raise RuntimeError("OPENROUTER_API_KEY not available")

    if not pdf_file_path:
        raise ValueError("pdf_file_path must be provided")
    if not os.path.exists(pdf_file_path):
        raise FileNotFoundError(f"PDF not found: {pdf_file_path}")

    model_name = settings.OPENROUTER_LLM_MODEL
    full_prompt = f"{system_prompt}\n\n{user_prompt_template}"
    test_mode = os.getenv("TEST_MODE", "").lower() == "unit"

    # Base64-encode the PDF
    with open(pdf_file_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

    logger.info(
        f"PDF encoded for {original_filename_for_logging} ({len(pdf_b64)} chars base64)"
    )

    # Build schema for json_schema mode
    if not test_mode and use_json_schema:
        pydantic_schema = response_model.model_json_schema()
        gemini_schema = clean_schema_for_gemini(pydantic_schema)
    else:
        gemini_schema = {}

    temperature = float(os.getenv("LOW_TEMPERATURE", "0.1"))

    # Build the OpenRouter payload
    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": full_prompt},
                    {
                        "type": "file",
                        "file": {
                            "filename": os.path.basename(pdf_file_path),
                            "file_data": f"data:application/pdf;base64,{pdf_b64}",
                        },
                    },
                ],
            }
        ],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": temperature,
    }

    # Use json_schema mode with the Pydantic-derived schema when enabled.
    if gemini_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "extraction_output", "schema": gemini_schema},
        }
    elif test_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with logfire.span(
        "llm.structured_response",
        job_id=job_id or "unknown",
        model=model_name,
        filename=original_filename_for_logging,
    ):
        logfire.info(
            f"Starting LLM structured response for {original_filename_for_logging}",
            job_id=job_id,
            model=model_name,
        )

        for attempt in range(max_retries_override):
            with logfire.span(
                "llm.generate_content",
                attempt=attempt + 1,
                max_retries=max_retries_override,
                model=model_name,
            ):
                try:
                    logger.info(
                        f"Attempt {attempt + 1}/{max_retries_override}: Calling OpenRouter ({model_name}) "
                        f"for {original_filename_for_logging}..."
                    )
                    logfire.info(
                        f"Calling OpenRouter (attempt {attempt + 1}/{max_retries_override})",
                        model=model_name,
                    )

                    # Make the HTTP call with timeout
                    async with httpx.AsyncClient(timeout=DEFAULT_GENERATE_TIMEOUT_SECONDS) as client:
                        response = await client.post(
                            OPENROUTER_BASE_URL,
                            headers=headers,
                            json=payload,
                        )

                    if response.status_code != 200:
                        error_body = response.text
                        logger.error(
                            f"OpenRouter HTTP {response.status_code} on attempt {attempt + 1}: {error_body}"
                        )
                        logfire.error(
                            "OpenRouter HTTP error",
                            status_code=response.status_code,
                            attempt=attempt + 1,
                        )
                        if attempt < max_retries_override - 1:
                            logger.info("Retrying due to HTTP error...")
                            await asyncio.sleep(2)
                            continue
                        raise RuntimeError(
                            f"OpenRouter API error {response.status_code}: {error_body}"
                        )

                    rj = response.json()

                    # Check for API-level error
                    if "error" in rj:
                        logger.error(
                            f"OpenRouter API error on attempt {attempt + 1}: {rj['error']}"
                        )
                        if attempt < max_retries_override - 1:
                            logger.info("Retrying due to API error...")
                            await asyncio.sleep(2)
                            continue
                        raise RuntimeError(f"OpenRouter API error: {rj['error']}")

                    # Extract usage
                    usage = rj.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)

                    logger.info(
                        f"OpenRouter response for {original_filename_for_logging}: "
                        f"{total_tokens} tokens ({prompt_tokens} prompt + {completion_tokens} completion)"
                    )

                    costs = calculate_costs(prompt_tokens, completion_tokens)
                    logfire.info(
                        "LLM response received",
                        total_tokens=total_tokens,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        cost_usd=costs.get("total_cost", 0),
                    )

                    # Extract content
                    raw_content = rj["choices"][0]["message"]["content"]
                    finish_reason = rj["choices"][0].get("finish_reason", "unknown")

                    if not raw_content:
                        logger.warning(
                            f"Empty response on attempt {attempt + 1} for {original_filename_for_logging}"
                        )
                        if attempt < max_retries_override - 1:
                            continue
                        return None

                    if finish_reason == "length":
                        logger.warning(
                            f"Response truncated (finish_reason=length) for {original_filename_for_logging} "
                            f"({len(raw_content)} chars). May produce invalid JSON."
                        )

                    # Parse JSON
                    try:
                        json_candidate = extract_json_candidate(raw_content)
                        repaired_response = repair_json_text(json_candidate)
                        data = json.loads(repaired_response)
                        processed_data = data if preserve_nulls else fix_null_values(data)
                        parsed_info = response_model(**processed_data)

                        logger.info(
                            f"Pydantic validation successful for {original_filename_for_logging}"
                        )
                        logfire.info("Pydantic validation successful")

                        return {
                            "parsed_info": parsed_info,
                            "token_usage": {
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "total_tokens": total_tokens,
                            },
                            "cost_info": costs,
                            "model_used": model_name,
                        }

                    except json.JSONDecodeError as je:
                        logger.error(
                            f"JSON parsing failed on attempt {attempt + 1} for "
                            f"{original_filename_for_logging}: {je}"
                        )
                        logfire.error("JSON parsing failed", exc_info=True)
                        if attempt < max_retries_override - 1:
                            logger.info("Retrying due to JSON error...")
                            continue

                    except ValidationError as ve:
                        logger.error(
                            f"Pydantic validation failed on attempt {attempt + 1} for "
                            f"{original_filename_for_logging}: {ve}"
                        )
                        logfire.error("Pydantic validation failed", exc_info=True)
                        if attempt < max_retries_override - 1:
                            logger.info("Retrying due to validation error...")
                            continue

                except httpx.TimeoutException:
                    logger.error(
                        f"OpenRouter timed out after {DEFAULT_GENERATE_TIMEOUT_SECONDS}s "
                        f"on attempt {attempt + 1} for {original_filename_for_logging}"
                    )
                    logfire.error(
                        f"OpenRouter timed out after {DEFAULT_GENERATE_TIMEOUT_SECONDS}s",
                        attempt=attempt + 1,
                    )
                    if attempt < max_retries_override - 1:
                        logger.info("Retrying due to timeout...")
                        continue
                    raise

                except Exception as e:
                    logger.error(
                        f"API call failed on attempt {attempt + 1} for "
                        f"{original_filename_for_logging}: {e}"
                    )
                    logfire.error("API call failed", exc_info=True)
                    if attempt < max_retries_override - 1:
                        logger.info("Retrying due to API error...")
                        await asyncio.sleep(2)
                        continue

        logger.error(
            f"All {max_retries_override} attempts failed for {original_filename_for_logging}"
        )
        logfire.error("All LLM attempts failed", max_retries=max_retries_override)
        raise Exception("LLM processing failed after retries")
