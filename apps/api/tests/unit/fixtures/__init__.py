"""
Unit test fixtures for INSPECT-AI.

Provides reusable test fixtures that are fast and isolated.
"""

from .data_fixtures import (
    performance_baseline,
    sample_check_results,
    sample_job_data,
)
from .service_fixtures import (
    all_services_mocked,
    clinical_trials_mock,
    database_mock,
    fast_unit_test_env,
    http_client_mock,
    retraction_watch_mock,
)
from .http_fixtures import (
    http_mock,
    grobid_mock,
    genai_mock,
    mock_httpx_client,
    mock_aiohttp_session,
    mock_registry_service_http,
    mock_grobid_service_http,
    mock_llm_service_genai,
)

__all__ = [
    # Service fixtures
    "database_mock",
    "http_client_mock",
    "clinical_trials_mock",
    "retraction_watch_mock",
    "all_services_mocked",
    "fast_unit_test_env",
    # Data fixtures
    "sample_check_results",
    "sample_job_data",
    "performance_baseline",
    # HTTP fixtures
    "http_mock",
    "grobid_mock",
    "genai_mock",
    "mock_httpx_client",
    "mock_aiohttp_session",
    "mock_registry_service_http",
    "mock_grobid_service_http",
    "mock_llm_service_genai",
]
