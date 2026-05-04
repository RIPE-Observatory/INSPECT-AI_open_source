"""
Service-related fixtures for unit testing.

Provides pre-configured mocks for essential external services.
"""

from unittest.mock import patch

import pytest

from tests.unit.mocks import (
    DatabaseMock,
    HTTPClientMock,
    create_clinical_trials_mock,
    create_database_mock,
    create_http_mock,
    create_retraction_watch_mock,
)


@pytest.fixture
def database_mock() -> DatabaseMock:
    """Provide a mock database session for unit tests."""
    mock = create_database_mock()

    # Patch the session factory
    with patch("core.db.session.get_db_session") as mock_get_session:
        mock_get_session.return_value = mock.create_mock_session()
        yield mock


@pytest.fixture
def http_client_mock() -> HTTPClientMock:
    """Provide a mock HTTP client for unit tests."""
    mock = create_http_mock()

    # Patch httpx.AsyncClient
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = mock.create_mock_client()
        yield mock


@pytest.fixture
def clinical_trials_mock():
    """Provide a mock ClinicalTrials.gov API for unit tests."""
    mock = create_clinical_trials_mock()

    # Patch the aiohttp.ClientSession used by RegistryService
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session_class.return_value = mock.create_mock_client()
        yield mock


@pytest.fixture
def retraction_watch_mock():
    """Provide a mock Retraction Watch API for unit tests."""
    mock = create_retraction_watch_mock()

    # Patch the HTTP client used by RetractionWatchService
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client_class.return_value = mock.create_mock_client()
        yield mock


@pytest.fixture
def all_services_mocked(database_mock, clinical_trials_mock, retraction_watch_mock):
    """Provide all service mocks at once for comprehensive unit tests."""
    return {
        "database": database_mock,
        "clinical_trials": clinical_trials_mock,
        "retraction_watch": retraction_watch_mock,
    }


@pytest.fixture
def fast_unit_test_env(monkeypatch):
    """Configure environment for fast unit tests."""
    # Disable all external API calls
    monkeypatch.setenv("DISABLE_EXTERNAL_APIS", "true")
    monkeypatch.setenv("TEST_MODE", "unit")

    # Disable logging for performance
    monkeypatch.setenv("LOG_LEVEL", "CRITICAL")

    # Disable any background tasks
    monkeypatch.setenv("DISABLE_BACKGROUND_TASKS", "true")
