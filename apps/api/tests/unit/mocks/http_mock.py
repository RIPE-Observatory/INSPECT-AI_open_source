"""
Simplified HTTP mock implementation for unit testing.

Provides minimal HTTP response mocking focused on speed and simplicity.
"""

from typing import Any
from unittest.mock import AsyncMock, Mock

from tests.unit.constants import NOT_FOUND_STATUS, SUCCESS_STATUS, TEST_NCT_ID

from .base import AsyncBaseMock, MockResponse


class HTTPClientMock(AsyncBaseMock):
    """Simplified mock for HTTP client operations."""

    def __init__(self):
        super().__init__()
        self._simulate_malformed = False  # Flag for malformed response simulation
        self._responses: dict[str, MockResponse] = {}
        self._default_response = MockResponse(
            data={"status": "success", "message": "Mock HTTP response"}
        )

    def reset(self):
        """Reset all mock state including stored responses."""
        super().reset()
        self._simulate_malformed = False
        self._responses.clear()
        # Reset to default response
        self._default_response = MockResponse(
            data={"status": "success", "message": "Mock HTTP response"}
        )

    def set_response(self, url_key: str, data: Any, status_code: int = SUCCESS_STATUS):
        """Set response for a URL key."""
        self._responses[url_key] = MockResponse(data=data, status_code=status_code)

    def set_json_response(
        self, url_key: str, data: dict[str, Any], status_code: int = SUCCESS_STATUS
    ):
        """Set JSON response for a URL key."""
        self.set_response(url_key, data, status_code)

    def setup_malformed_response(self):
        """Set up mock to return malformed responses."""
        self._simulate_malformed = True

    def create_mock_client(self) -> AsyncMock:
        """Create a simplified mock HTTP client."""
        client = AsyncMock()

        # Mock HTTP methods as simple async context managers
        client.get = Mock(side_effect=self._create_context_manager)
        client.post = AsyncMock(side_effect=self._mock_request)
        client.put = AsyncMock(side_effect=self._mock_request)
        client.delete = AsyncMock(side_effect=self._mock_request)

        # For aiohttp.ClientSession context manager support
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)

        return client

    def _create_context_manager(self, url: str, **kwargs):
        """Create simple async context manager for GET requests."""
        # Create a mock that acts as both the context manager and the response
        mock_cm = AsyncMock()

        async def aenter():
            return await self._mock_request(url, method="GET", **kwargs)

        mock_cm.__aenter__ = AsyncMock(side_effect=aenter)
        mock_cm.__aexit__ = AsyncMock(return_value=None)

        return mock_cm

    async def _mock_request(self, url: str, method: str = "GET", **kwargs) -> Mock:
        """Handle HTTP request with minimal logic."""
        self.record_call(method.lower(), url=url, **kwargs)

        # Simple URL matching - find exact matches first, then substrings
        response = self._find_response(url)

        # Create mock HTTP response
        http_response = Mock()
        http_response.status_code = response.status_code
        http_response.ok = response.ok

        # Handle malformed response simulation
        if self._simulate_malformed:
            self._simulate_malformed = False  # Reset after use
            http_response.json = AsyncMock(side_effect=ValueError("Malformed response"))
            http_response.text = AsyncMock(return_value="malformed")
            http_response.status = response.status_code
            return http_response

        # Simple JSON handling
        if isinstance(response.data, dict):
            http_response.json = AsyncMock(return_value=response.data)
            http_response.text = AsyncMock(return_value=str(response.data))
        else:
            http_response.json = AsyncMock(side_effect=ValueError("Not JSON"))
            http_response.text = AsyncMock(return_value=str(response.data))

        # Add status property for aiohttp compatibility
        http_response.status = response.status_code

        return http_response

    def _find_response(self, url: str) -> MockResponse:
        """Find response for URL with simple matching."""
        # Exact match first
        if url in self._responses:
            return self._responses[url]

        # Check for NCT ID patterns in URL (priority matching)
        for key in self._responses:
            if key.startswith("NCT") and key in url:
                return self._responses[key]

        # General substring match for other patterns
        for key in self._responses:
            if key in url and not key.startswith("NCT"):
                return self._responses[key]

        return self._default_response


class ClinicalTrialsAPIMock(HTTPClientMock):
    """Simplified Clinical Trials API mock."""

    def __init__(self):
        super().__init__()
        self._setup_defaults()

    def reset(self):
        """Reset all mock state and restore defaults."""
        super().reset()
        self._setup_defaults()

    def _setup_defaults(self):
        """Set up realistic default responses matching ClinicalTrials.gov API."""
        # More realistic study response structure
        default_study = {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": TEST_NCT_ID,
                            "briefTitle": "Mock Clinical Trial Study",
                            "officialTitle": "A Randomized, Double-Blind, Placebo-Controlled Study of Mock Drug",
                        },
                        "statusModule": {
                            "studyFirstSubmitQcDate": "2024-01-01",
                            "studyFirstPostDate": "2024-01-05",
                            "lastUpdateSubmitDate": "2024-01-15",
                            "overallStatus": "RECRUITING",
                        },
                        "designModule": {
                            "studyType": "INTERVENTIONAL",
                            "phases": ["PHASE3"],
                            "designInfo": {
                                "allocation": "RANDOMIZED",
                                "interventionModel": "PARALLEL",
                                "primaryPurpose": "TREATMENT",
                                "maskingInfo": {
                                    "masking": "DOUBLE",
                                    "whoMasked": ["PARTICIPANT", "INVESTIGATOR"],
                                },
                            },
                        },
                    }
                }
            ]
        }
        self.set_json_response("studies", default_study)
        self.set_json_response("clinicaltrials.gov", default_study)

    def setup_study_response(self, nct_id: str, data: dict[str, Any] = None):
        """Set realistic response for specific NCT ID."""
        if data is None:
            data = {
                "protocolSection": {
                    "identificationModule": {
                        "nctId": nct_id,
                        "briefTitle": f"Clinical Trial {nct_id}",
                        "officialTitle": f"Study for {nct_id}",
                    },
                    "statusModule": {
                        "studyFirstSubmitQcDate": "2024-01-01",
                        "studyFirstPostDate": "2024-01-05",
                        "overallStatus": "RECRUITING",
                    },
                }
            }
        # For field-specific API calls, return the data directly
        self.set_json_response(nct_id, data)

    def setup_study_not_found(self, nct_id: str):
        """Set 404 for specific NCT ID."""
        self.set_response(
            nct_id, {"error": f"Study {nct_id} not found"}, NOT_FOUND_STATUS
        )


class RetractionWatchAPIMock(HTTPClientMock):
    """Simplified Retraction Watch API mock."""

    def __init__(self):
        super().__init__()
        self._setup_defaults()

    def reset(self):
        """Reset all mock state and restore defaults."""
        super().reset()
        self._setup_defaults()

    def _setup_defaults(self):
        """Set up realistic default responses matching Retraction Watch API."""
        # Default no retraction found - realistic API response structure
        self.set_json_response(
            "retraction", {"results": [], "count": 0, "next": None, "previous": None}
        )

    def setup_retraction(self, doi: str, is_retracted: bool = True):
        """Set realistic retraction status for DOI."""
        if is_retracted:
            data = {
                "results": [
                    {
                        "id": 12345,
                        "doi": doi,
                        "title": f"Study with DOI {doi}",
                        "journal": "Mock Journal",
                        "retraction_date": "2024-01-15",
                        "retraction_doi": f"10.1234/retraction.{doi.split('.')[-1]}",
                        "reason": "Data fabrication concerns",
                        "nature": "RETRACTION",
                    }
                ],
                "count": 1,
                "next": None,
                "previous": None,
            }
        else:
            data = {"results": [], "count": 0, "next": None, "previous": None}
        self.set_json_response(doi, data)


# Factory functions
def create_http_mock() -> HTTPClientMock:
    """Create a simple HTTP mock."""
    return HTTPClientMock()


def create_clinical_trials_mock() -> ClinicalTrialsAPIMock:
    """Create a Clinical Trials API mock."""
    return ClinicalTrialsAPIMock()


def create_retraction_watch_mock() -> RetractionWatchAPIMock:
    """Create a Retraction Watch API mock."""
    return RetractionWatchAPIMock()
