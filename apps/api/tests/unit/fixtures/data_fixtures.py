"""
Data fixtures for unit testing.

Provides sample data structures for testing without external dependencies.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest


@pytest.fixture
def sample_check_results() -> dict[str, dict[str, Any]]:
    """Sample check results for all core analyses."""
    return {
        "trial_llm_extraction": {
            "status": "COMPLETED_SUCCESS",
            "title": "Test Clinical Trial",
            "doi": "10.1234/test.2024.001",
            "publication_year": 2024,
            "authors": ["Test A", "Mock B"],
            "trial_registration": {
                "registry": "ClinicalTrials.gov",
                "identifier": "NCT99999999",
            },
        },
        "registry_crosscheck": {
            "status": "COMPLETED_SUCCESS",
            "registry_found": True,
            "registry_data": {
                "nct_id": "NCT99999999",
                "title": "Test Clinical Trial",
                "status": "COMPLETED",
            },
        },
        "timeline_consistency": {
            "status": "COMPLETED_SUCCESS",
            "timeline_consistent": True,
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "registration_date": "2022-12-01",
        },
        "grobid_primary_metadata": {
            "status": "COMPLETED_SUCCESS",
            "doi_found": True,
            "doi_value": "10.1234/test.2024.001",
        },
        "grobid_reference_metadata": {
            "status": "COMPLETED_SUCCESS",
            "references_found": 25,
            "valid_dois": 23,
            "invalid_dois": 2,
        },
        "prospective_registration_analysis": {
            "status": "COMPLETED_SUCCESS",
            "prospectively_registered": True,
            "registration_date": "2022-12-01",
            "study_start_date": "2023-01-01",
        },
        "retraction_watch_monitor": {
            "status": "COMPLETED_SUCCESS",
            "retraction_found": False,
            "retraction_data": None,
        },
    }


@pytest.fixture
def sample_job_data() -> dict[str, Any]:
    """Sample job data for testing."""
    return {
        "id": uuid.uuid4(),
        "identifier": "test_paper.pdf",
        "file_path": "/uploads/test_paper.pdf",
        "status": "COMPLETED",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "source": "upload",
        "metadata": {"file_size": 1024000, "upload_ip": "127.0.0.1"},
    }


@pytest.fixture
def performance_baseline():
    """Performance baseline for unit test timing."""
    from tests.unit.constants import SETUP_MAX_MS, UNIT_TEST_MAX_MS

    return {
        "max_test_time_ms": UNIT_TEST_MAX_MS,  # Use consistent constants
        "max_setup_time_ms": SETUP_MAX_MS,  # Setup time limit
        "max_teardown_time_ms": 5,  # Teardown should be < 5ms
    }
