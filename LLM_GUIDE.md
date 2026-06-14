# LLM Guide

This guide maps the LLM-related parts of INSPECT-AI to the files that implement them.

## Current LLM Use

The current INSPECT-AI version uses LLM calls for two structured extraction checks over uploaded clinical trial PDFs:

| Check | What it extracts | Stored result key |
| --- | --- | --- |
| Trial ID extraction | Primary trial registration ID and registry type | `trial_llm_extraction` |
| Study timeline extraction | Recruitment start, recruitment finish, and study end dates | `timeline_consistency` |

The extracted values are stored in JSON in the database. They are then used by registry lookup, prospective registration analysis, and the reviewer-facing INSPECT-SR fields.

## Implementation Index

| File | Purpose |
| --- | --- |
| `packages/python/core/prompts/llm_prompts.py` | Prompt text for trial ID and study timeline extraction. |
| `packages/python/core/schemas/llm_outputs.py` | Pydantic response models used to validate LLM outputs. |
| `packages/python/core/services/llm_service.py` | OpenRouter request handling, PDF attachment, JSON extraction, validation, retries, token usage, and cost calculation. |
| `packages/python/core/checks/trial_llm_extraction.py` | Check wrapper for trial registration ID extraction. |
| `packages/python/core/checks/timeline_consistency.py` | Check wrapper for study timeline date extraction. |
| `packages/python/core/checks/registry_crosscheck.py` | Uses the extracted trial ID and registry type to retrieve registry data. |
| `packages/python/core/checks/prospective_registration.py` | Compares the extracted recruitment start date with the registry registration date. |
| `packages/python/core/config/checks_registry.yaml` | Defines the current checks and check dependencies. |
| `packages/python/core/tasks/arq_tasks.py` | Orchestrates job execution and check ordering. |
| `packages/python/core/results/normalize_checks.py` | Normalizes raw check outputs into result envelopes. |
| `packages/python/core/results/populate_inspect_sr.py` | Populates INSPECT-SR reviewer fields from normalized check outputs. |

## Prompts

The prompt file contains:

| Symbol | Used by |
| --- | --- |
| `DEFAULT_SYSTEM_PROMPT` | Shared system prompt. |
| `TRIAL_ID_EXTRACTION_USER_PROMPT` | Trial registration ID extraction. |
| `STUDY_TIMELINE_DATES_USER_PROMPT` | Study timeline date extraction. |

Both extraction prompts require JSON-only output and include rules for absent,
uncertain, or ambiguous values.

## Response Models

The LLM response is parsed into Pydantic models before being stored.

| Model | Fields |
| --- | --- |
| `TrialRegistrationInfo` | `trial_id`, `registry_type`, `comment` |
| `StudyTimelineDates` | `recruitment_start`, `recruitment_finish`, `study_end_date` |
| `DateExtractionDetail` | `normalized_date`, `interpretation_comment` |

`DateExtractionDetail` normalizes accepted date formats to `DD-MM-YYYY` or
`MM-YYYY`. Empty strings are used when a date is unavailable or cannot be
parsed.

## Service Flow

`get_structured_llm_response` in `llm_service.py` handles the shared request and
validation flow:

1. Receives the system prompt, user prompt, response model, and PDF path.
2. Encodes the PDF as base64 and sends it with the prompt through OpenRouter.
3. Uses the configured model from `OPENROUTER_LLM_MODEL`.
4. Uses a Pydantic-derived JSON schema response format outside unit tests.
5. Extracts a JSON object from the response text.
6. Applies light JSON repair for common response formatting issues.
7. Converts null values to schema-compatible defaults.
8. Validates the parsed data with the supplied Pydantic model.
9. Returns the parsed model, token usage, cost information, and model name.

The check wrappers convert the parsed model into job result payloads with status
values such as `COMPLETED_SUCCESS`, `COMPLETED_NOT_FOUND`, or `FAILED`.

## Check Wiring

The current profile in `checks_registry.yaml` wires the LLM-backed checks into the rest of the assessment flow.

```text
trial_llm_extraction
  -> registry_crosscheck
  -> prospective_registration

timeline_consistency
  -> prospective_registration
```

`prospective_registration` uses:

| Input | Source |
| --- | --- |
| Recruitment start date | `timeline_consistency` |
| Registry registration date | `registry_crosscheck` |
| Registry type | `trial_llm_extraction` and `registry_crosscheck` |

The resulting prospective registration output is normalized and used to populate
INSPECT-SR question `Q2.2`.

## Reviewer-Facing Output

The reviewer interface receives automated suggestions through the normalized
results and INSPECT-SR data structure.

`populate_inspect_sr.py` writes:

| INSPECT-SR field | Meaning |
| --- | --- |
| `automated_judgement` | Suggested value from the completed checks. |
| `reviewed_judgement` | Reviewer-entered final value. |
| `comment` | Reviewer rationale. |

This keeps system-generated outputs and reviewer-entered outputs in separate
fields.

## Configuration

LLM settings are read from environment variables.

| Variable | Purpose | Default |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | API key for OpenRouter-backed extraction checks. | none |
| `OPENROUTER_LLM_MODEL` | Model name passed to OpenRouter. | `google/gemini-3-flash-preview:nitro` |
| `LLM_GENERATE_TIMEOUT_SECONDS` | Request timeout for LLM calls. | `120` |
| `LLM_MAX_OUTPUT_TOKENS` | Maximum output tokens for extraction responses. | `131072` |
| `LOW_TEMPERATURE` | Temperature used for extraction calls. | `0.1` |
| `GEMINI_2_0_FLASH_INPUT_COST` | Optional input-token price used for cost calculation. | `0.0000001` |
| `GEMINI_2_0_FLASH_OUTPUT_COST` | Optional output-token price used for cost calculation. | `0.0000004` |

The local setup template is `.env.example`.

## Tests

LLM service unit tests are in:

`apps/api/tests/unit/services/test_llm_service_unit.py`

The tests cover payload construction, response parsing, JSON repair, schema cleaning, Pydantic validation, missing files, and HTTP error handling.
