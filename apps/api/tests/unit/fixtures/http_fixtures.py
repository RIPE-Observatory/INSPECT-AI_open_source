"""
HTTP client fixtures and patching utilities for unit tests.

Provides pytest fixtures for mocking HTTP clients across different services.
"""

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from tests.unit.mocks.genai_mock import create_genai_mock
from tests.unit.mocks.grobid_mock import create_grobid_mock
from tests.unit.mocks.http_mock import (
    create_clinical_trials_mock,
    create_http_mock,
    create_retraction_watch_mock,
)


@pytest.fixture
def http_mock():
    """Basic HTTP client mock."""
    return create_http_mock()


@pytest.fixture
def clinical_trials_mock():
    """Clinical Trials API mock."""
    return create_clinical_trials_mock()


@pytest.fixture
def retraction_watch_mock():
    """Retraction Watch API mock."""
    return create_retraction_watch_mock()


@pytest.fixture
def grobid_mock():
    """GROBID service mock."""
    return create_grobid_mock()


@pytest.fixture
def genai_mock():
    """Google GenAI client mock."""
    return create_genai_mock()


@pytest.fixture
def mock_httpx_client(http_mock):
    """Mock httpx.AsyncClient with automatic patching."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = http_mock.create_mock_client()
        yield mock_client_class


@pytest.fixture
def mock_aiohttp_session(http_mock):
    """Mock aiohttp.ClientSession with automatic patching."""
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session_class.return_value = http_mock.create_mock_client()
        yield mock_session_class


@asynccontextmanager
async def mock_http_context(mock_instance):
    """Context manager for HTTP client mocking."""
    try:
        yield mock_instance
    finally:
        mock_instance.reset()


# Service-specific fixtures with automatic patching
@pytest.fixture
def mock_registry_service_http(clinical_trials_mock):
    """Mock HTTP client for Registry Service."""
    with patch("httpx.AsyncClient") as mock_httpx:
        with patch("aiohttp.ClientSession") as mock_aiohttp:
            mock_httpx.return_value = clinical_trials_mock.create_mock_client()
            mock_aiohttp.return_value = clinical_trials_mock.create_mock_client()
            yield clinical_trials_mock


@pytest.fixture
def mock_grobid_service_http(grobid_mock):
    """Mock HTTP client for GROBID Service."""
    with patch("httpx.AsyncClient") as mock_httpx:
        mock_httpx.return_value = grobid_mock.create_mock_client()
        yield grobid_mock


@pytest.fixture
def mock_llm_service_genai(genai_mock):
    """Mock Google GenAI client for LLM Service."""
    with patch("google.genai.Client") as mock_client_class:
        mock_client_class.return_value = genai_mock.create_mock_client()
        yield genai_mock
