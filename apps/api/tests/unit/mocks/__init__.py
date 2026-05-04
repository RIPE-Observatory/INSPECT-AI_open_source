"""
Unit test mocks for INSPECT-AI.

This module provides standardized mocks for all external dependencies
to enable fast, isolated unit testing.
"""

from .base import BaseMock, MockResponse
from .database_mock import DatabaseMock, create_database_mock
from .http_mock import (
    ClinicalTrialsAPIMock,
    HTTPClientMock,
    RetractionWatchAPIMock,
    create_clinical_trials_mock,
    create_http_mock,
    create_retraction_watch_mock,
)

__all__ = [
    "BaseMock",
    "MockResponse",
    "DatabaseMock",
    "HTTPClientMock",
    "ClinicalTrialsAPIMock",
    "RetractionWatchAPIMock",
    "create_database_mock",
    "create_http_mock",
    "create_clinical_trials_mock",
    "create_retraction_watch_mock",
]
