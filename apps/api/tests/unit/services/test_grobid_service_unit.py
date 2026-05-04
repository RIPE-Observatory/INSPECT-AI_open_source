"""
Unit tests for GROBID service.

Tests the GROBID PDF processing service HTTP mocking functionality.
All external dependencies are mocked for fast, isolated testing.
"""

import pytest

from core.services.grobid_service import (
    GrobidParsingError,
    GrobidService,
    GrobidValidationError,
    validate_pdf,
)
from tests.unit.constants import (
    MIN_PDF_SIZE,
    MOCK_PDF_CONTENT,
    SERVICE_UNAVAILABLE_ERROR,
    UNIT_TEST_MAX_MS,
    VALID_PDF_HEADER,
)


@pytest.mark.unit
class TestGrobidServiceUnit:
    """Unit tests for GROBID service functionality."""

    def test_grobid_service_initialization(self):
        """Test GROBID service initializes correctly."""
        service = GrobidService()

        # Verify initialization
        assert hasattr(service, "base_url")
        assert hasattr(service, "_timeout")
        assert hasattr(service, "parser")
        assert service.base_url is not None

    def test_pdf_validation_functions(self, test_timer):
        """Test PDF validation utilities."""
        # Test valid PDF (with proper header and size)
        is_valid, error_msg = validate_pdf(MOCK_PDF_CONTENT)
        assert is_valid is True
        assert error_msg is None

        # Test invalid PDF (too small)
        invalid_pdf = b"small"
        is_valid, error_msg = validate_pdf(invalid_pdf)
        assert is_valid is False
        assert "too small" in error_msg.lower()

        # Test invalid PDF (no header)
        no_header_pdf = b"No PDF header " * 100
        is_valid, error_msg = validate_pdf(no_header_pdf)
        assert is_valid is False
        assert "header" in error_msg.lower()

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "PDF validation")

    @pytest.mark.asyncio
    async def test_process_header_document_with_mock(
        self, mock_grobid_service_http, test_timer
    ):
        """Test successful header document processing with mocked HTTP."""
        service = GrobidService()

        result = await service.process_header_document(MOCK_PDF_CONTENT)

        # Verify response structure
        assert result is not None
        assert isinstance(result, str)
        assert "<TEI" in result  # Should contain TEI XML
        assert "Mock Clinical Trial Paper" in result

        # Verify mock was called exactly once
        mock_grobid_service_http.assert_called_once("post")

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Header processing")

    @pytest.mark.asyncio
    async def test_process_references_with_mock(
        self, mock_grobid_service_http, test_timer
    ):
        """Test successful references processing with mocked HTTP."""
        service = GrobidService()

        result = await service.process_references_only(MOCK_PDF_CONTENT)

        # Verify response structure
        assert result is not None
        assert isinstance(result, str)
        assert "<TEI" in result
        assert "Reference Paper 1" in result

        # Verify mock was called exactly once
        mock_grobid_service_http.assert_called_once("post")

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "References processing")

    @pytest.mark.asyncio
    async def test_http_error_simulation(self, mock_grobid_service_http, test_timer):
        """Test HTTP error response simulation."""
        # Setup mock to return error
        mock_grobid_service_http.setup_error_response(SERVICE_UNAVAILABLE_ERROR, 503)

        service = GrobidService()

        with pytest.raises(Exception) as exc_info:
            await service.process_header_document(MOCK_PDF_CONTENT)

        # Should contain the HTTP error, not PDF validation error
        error_message = str(exc_info.value)
        assert SERVICE_UNAVAILABLE_ERROR in error_message or "503" in error_message

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Error simulation")

    def test_pdf_validation_edge_cases(self, test_timer):
        """Test PDF validation with edge cases."""
        # Test exact minimum size
        min_size_pdf = VALID_PDF_HEADER + b"x" * (MIN_PDF_SIZE - len(VALID_PDF_HEADER))
        is_valid, error_msg = validate_pdf(min_size_pdf)
        assert is_valid is True
        assert error_msg is None

        # Test one byte under minimum
        under_min_pdf = VALID_PDF_HEADER + b"x" * (
            MIN_PDF_SIZE - len(VALID_PDF_HEADER) - 1
        )
        is_valid, error_msg = validate_pdf(under_min_pdf)
        assert is_valid is False
        assert "too small" in error_msg.lower()

        # Test empty input
        is_valid, error_msg = validate_pdf(b"")
        assert is_valid is False
        assert error_msg is not None

        # Test None input - should be handled gracefully
        is_valid, error_msg = validate_pdf(None)
        assert is_valid is False
        assert error_msg is not None
        assert "None" in error_msg

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "PDF validation edge cases")

    def test_extract_header_metadata_error_handling(self, test_timer):
        """Test that parsing methods raise proper exceptions for malformed XML."""
        service = GrobidService()

        # Test with malformed XML
        malformed_xml = "<tei><header>incomplete xml"

        with pytest.raises(GrobidParsingError) as exc_info:
            service.extract_header_metadata(malformed_xml)

        # Should contain parsing error information
        assert (
            "parse" in str(exc_info.value).lower()
            or "xml" in str(exc_info.value).lower()
        )

        test_timer.assert_under_ms(
            UNIT_TEST_MAX_MS, "Header metadata parsing error handling"
        )

    def test_extract_references_error_handling(self, test_timer):
        """Test that references parsing raises proper exceptions for malformed XML."""
        service = GrobidService()

        # Test with malformed XML
        malformed_xml = "<tei><listBibl>incomplete xml"

        with pytest.raises(GrobidParsingError) as exc_info:
            service.extract_references(malformed_xml)

        # Should contain parsing error information
        assert (
            "parse" in str(exc_info.value).lower()
            or "xml" in str(exc_info.value).lower()
        )

        test_timer.assert_under_ms(
            UNIT_TEST_MAX_MS, "References parsing error handling"
        )

    @pytest.mark.asyncio
    async def test_pdf_validation_none_input(self, test_timer):
        """Test that None PDF content raises proper validation error."""
        service = GrobidService()

        # Test with None PDF content - should raise GrobidValidationError
        with pytest.raises(GrobidValidationError) as exc_info:
            await service.process_header_document(None)

        # Should contain validation error information
        assert "PDF content is None" in str(exc_info.value)

        test_timer.assert_under_ms(
            UNIT_TEST_MAX_MS, "None PDF validation error handling"
        )


@pytest.mark.unit
class TestGrobidServiceMockIntegration:
    """Test GROBID service HTTP mock integration."""

    @pytest.mark.asyncio
    async def test_custom_xml_response(self, mock_grobid_service_http, test_timer):
        """Test processing with custom XML response."""
        # Setup custom XML response
        custom_xml = (
            "<TEI><titleStmt><title>Custom Test Paper</title></titleStmt></TEI>"
        )
        mock_grobid_service_http.setup_header_response(custom_xml)

        service = GrobidService()
        result = await service.process_header_document(MOCK_PDF_CONTENT)

        assert "Custom Test Paper" in result
        assert "titleStmt" in result

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Custom XML test")

    @pytest.mark.asyncio
    async def test_mock_call_tracking(self, mock_grobid_service_http, test_timer):
        """Test that HTTP mock properly tracks calls."""
        service = GrobidService()

        # Process header
        await service.process_header_document(MOCK_PDF_CONTENT)
        header_calls = mock_grobid_service_http.call_count

        # Reset and process references
        mock_grobid_service_http.reset()
        await service.process_references_only(MOCK_PDF_CONTENT)
        refs_calls = mock_grobid_service_http.call_count

        # Both should have made exactly one call each
        assert header_calls == 1
        assert refs_calls == 1

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Call tracking test")

    @pytest.mark.asyncio
    async def test_sequential_processing(self, mock_grobid_service_http, test_timer):
        """Test sequential document processing."""
        service = GrobidService()

        # Process multiple documents
        pdf_contents = [MOCK_PDF_CONTENT] * 3

        for pdf_content in pdf_contents:
            result = await service.process_header_document(pdf_content)
            assert result is not None
            assert isinstance(result, str)

        # Should have made 3 calls total
        assert mock_grobid_service_http.call_count == 3

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Sequential processing test")

    @pytest.mark.asyncio
    async def test_network_timeout_error(self, mock_grobid_service_http, test_timer):
        """Test handling of network timeouts."""
        # Setup timeout simulation
        mock_grobid_service_http.setup_timeout_error(timeout_delay=2.0)

        service = GrobidService()

        with pytest.raises(Exception) as exc_info:
            await service.process_header_document(MOCK_PDF_CONTENT)

        # Should contain timeout information
        error_message = str(exc_info.value)
        assert (
            "timeout" in error_message.lower() or "timed out" in error_message.lower()
        )

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Timeout error handling")

    @pytest.mark.asyncio
    async def test_connection_error_handling(
        self, mock_grobid_service_http, test_timer
    ):
        """Test handling of connection errors."""
        # Setup connection error
        mock_grobid_service_http.setup_connection_error()

        service = GrobidService()

        with pytest.raises((ConnectionError, Exception)) as exc_info:
            await service.process_references_only(MOCK_PDF_CONTENT)

        # Should contain connection error information
        error_message = str(exc_info.value)
        assert (
            "connection" in error_message.lower() or "refused" in error_message.lower()
        )

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Connection error handling")

    @pytest.mark.asyncio
    async def test_malformed_xml_response(self, mock_grobid_service_http, test_timer):
        """Test handling of malformed XML responses."""
        # Setup malformed response
        mock_grobid_service_http.setup_malformed_response()

        service = GrobidService()

        # Process document - should get malformed XML from GROBID
        result = await service.process_header_document(MOCK_PDF_CONTENT)

        # Verify we got the malformed XML
        assert result is not None
        assert "malformed" in result
        assert "incomplete" in result

        # Now test that parsing this malformed XML raises GrobidParsingError
        with pytest.raises(GrobidParsingError) as exc_info:
            service.extract_header_metadata(result)

        # Should contain parsing error information
        assert (
            "parse" in str(exc_info.value).lower()
            or "xml" in str(exc_info.value).lower()
        )

        test_timer.assert_under_ms(UNIT_TEST_MAX_MS, "Malformed XML handling")
