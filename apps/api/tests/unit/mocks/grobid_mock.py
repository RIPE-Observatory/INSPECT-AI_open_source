"""
Simplified GROBID API mock for unit testing.

Provides minimal responses for GROBID PDF processing endpoints.
"""

from unittest.mock import AsyncMock, Mock

from tests.unit.constants import SERVICE_UNAVAILABLE_STATUS, SUCCESS_STATUS

from .base import AsyncBaseMock, MockResponse


class GROBIDAPIMock(AsyncBaseMock):
    """Simplified mock for GROBID PDF processing service."""

    def __init__(self):
        super().__init__()
        self._simulate_malformed = False  # Flag for malformed response simulation
        self._default_header_response = MockResponse(
            data="""<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title>Mock Clinical Trial Paper</title>
            </titleStmt>
            <publicationStmt>
                <publisher>Mock Journal</publisher>
                <date when="2024">2024</date>
            </publicationStmt>
            <sourceDesc>
                <biblStruct>
                    <analytic>
                        <title>A Randomized Controlled Trial of Mock Intervention</title>
                        <author>
                            <persName><surname>Doe</surname><forename>John</forename></persName>
                        </author>
                    </analytic>
                    <monogr>
                        <title>Journal of Mock Medicine</title>
                        <imprint>
                            <date when="2024-01">2024-01</date>
                        </imprint>
                    </monogr>
                </biblStruct>
            </sourceDesc>
        </fileDesc>
    </teiHeader>
</TEI>""",
            status_code=SUCCESS_STATUS,
        )
        self._default_references_response = MockResponse(
            data="""<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <text>
        <back>
            <div type="references">
                <listBibl>
                    <biblStruct xml:id="b0">
                        <analytic>
                            <title>Reference Paper 1: Systematic Review</title>
                            <author>
                                <persName><surname>Smith</surname><forename>Jane</forename></persName>
                            </author>
                        </analytic>
                        <monogr>
                            <title>Medical Reviews</title>
                            <imprint>
                                <date when="2023">2023</date>
                            </imprint>
                        </monogr>
                    </biblStruct>
                    <biblStruct xml:id="b1">
                        <analytic>
                            <title>Reference Paper 2: Clinical Guidelines</title>
                        </analytic>
                        <monogr>
                            <title>Clinical Practice</title>
                            <imprint>
                                <date when="2022">2022</date>
                            </imprint>
                        </monogr>
                    </biblStruct>
                </listBibl>
            </div>
        </back>
    </text>
</TEI>""",
            status_code=SUCCESS_STATUS,
        )
        self._header_response = self._default_header_response
        self._references_response = self._default_references_response

    def reset(self):
        """Reset all mock state including responses."""
        super().reset()
        self._simulate_malformed = False
        self._header_response = self._default_header_response
        self._references_response = self._default_references_response

    def create_mock_client(self) -> AsyncMock:
        """Create a simplified mock HTTP client for GROBID."""
        client = AsyncMock()
        client.post = AsyncMock(side_effect=self._mock_post)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        return client

    async def _mock_post(self, url: str, **kwargs) -> Mock:
        """Simple POST request mock."""
        self.record_call("post", url=url, **kwargs)

        # Check if malformed response is requested
        if self._simulate_malformed:
            response = MockResponse(
                data="<malformed><incomplete>xml", status_code=SUCCESS_STATUS
            )
        else:
            # Simple endpoint detection
            if "processHeaderDocument" in url:
                response = self._header_response
            elif "processReferences" in url:
                response = self._references_response
            else:
                response = MockResponse(
                    data="Unknown endpoint", status_code=SERVICE_UNAVAILABLE_STATUS
                )

        # Create simple HTTP response
        http_response = Mock()
        http_response.status_code = response.status_code
        http_response.ok = response.ok
        http_response.text = response.data

        if response.error:
            http_response.raise_for_status = Mock(side_effect=Exception(response.error))
        else:
            http_response.raise_for_status = Mock()

        return http_response

    def setup_header_response(self, xml_content: str):
        """Set custom header processing response."""
        self._header_response = MockResponse(
            data=xml_content, status_code=SUCCESS_STATUS
        )

    def setup_references_response(self, xml_content: str):
        """Set custom references processing response."""
        self._references_response = MockResponse(
            data=xml_content, status_code=SUCCESS_STATUS
        )

    def setup_malformed_response(self):
        """Set up mock to return malformed XML."""
        self._simulate_malformed = True

    def setup_error_response(
        self, error_message: str, status_code: int = SERVICE_UNAVAILABLE_STATUS
    ):
        """Set up error response for all endpoints."""
        error_response = MockResponse(
            data=error_message, status_code=status_code, error=error_message
        )
        self._header_response = error_response
        self._references_response = error_response


def create_grobid_mock() -> GROBIDAPIMock:
    """Create a GROBID API mock."""
    return GROBIDAPIMock()
