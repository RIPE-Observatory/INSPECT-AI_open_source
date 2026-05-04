import httpx
from typing import Optional, Dict, List, Any, Tuple
import logging
import re
import asyncio
from core.config import settings
from core.services.grobid_parser import GrobidTEIParser
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

# Pre-compiled regex patterns for better performance
DOI_PREFIX_PATTERN = re.compile(r"^(doi:|https?://(dx\.)?doi\.org/)", re.IGNORECASE)
DOI_FORMAT_PATTERN = re.compile(r"^10\.\d{4,}/[-._;()/:\w\[\]]+$", re.IGNORECASE)


def should_retry_http_error(exception):
    """Determine if an HTTP exception should be retried."""
    if isinstance(exception, httpx.HTTPStatusError):
        # Only retry server errors (5xx), not client errors (4xx)
        return 500 <= exception.response.status_code < 600
    # Retry on ANY connection-related error
    return isinstance(
        exception,
        (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,  # Server disconnection
            httpx.NetworkError,  # Any network error
            httpx.ProtocolError,  # Protocol violations
        ),
    )


def validate_doi(doi: str) -> Optional[str]:
    """Clean and validate DOI with sanitization"""
    if not doi or not isinstance(doi, str):
        return None

    # Remove common prefixes and clean using pre-compiled pattern
    doi = DOI_PREFIX_PATTERN.sub("", doi.strip())

    # Remove trailing punctuation and common artifacts
    doi = doi.rstrip(".,;")

    # Remove query parameters and fragments that might be appended
    if "?" in doi:
        doi = doi.split("?")[0]
    if "#" in doi:
        doi = doi.split("#")[0]

    # Basic DOI format check using pre-compiled pattern
    if DOI_FORMAT_PATTERN.match(doi):
        logger.debug(f"Validated DOI: {doi}")
        return doi

    logger.debug(f"Invalid DOI format rejected: {doi}")
    return None


class GrobidValidationError(Exception):
    """Raised when the PDF input is invalid for GROBID processing."""


class GrobidParsingError(Exception):
    """Raised when TEI XML parsing fails."""


def validate_pdf(pdf_content: Optional[bytes]) -> Tuple[bool, Optional[str]]:
    """Basic PDF validation.

    Returns (is_valid, error_message or None)
    """
    if pdf_content is None:
        return False, "PDF content is None"

    if len(pdf_content) < 1024:
        return False, "PDF file too small"

    max_size = settings.GROBID_MAX_FILE_SIZE_MB * 1024 * 1024
    if len(pdf_content) > max_size:
        return False, f"PDF file too large (> {settings.GROBID_MAX_FILE_SIZE_MB}MB)"

    if pdf_content[:5] != b"%PDF-":
        return False, "Invalid PDF header"

    return True, None


class GrobidService:
    """Service for interacting with GROBID PDF extraction"""

    def __init__(self):
        self.base_url = settings.get_grobid_service_url()
        if not self.base_url.startswith(("http://", "https://")):
            self.base_url = f"http://{self.base_url}"
        self.parser = GrobidTEIParser()

        # Create a shared HTTP client with connection pooling for better performance
        self._client = None
        self._client_lock = asyncio.Lock()
        self._timeout = httpx.Timeout(
            timeout=settings.GROBID_TIMEOUT_SECONDS,
            connect=30.0,  # 30s connection timeout
            read=settings.GROBID_TIMEOUT_SECONDS,  # 300s read timeout
            write=30.0,  # 30s write timeout
            pool=10.0,  # 10s pool timeout
        )

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensure proper cleanup"""
        await self.close()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client with connection pooling"""
        if self._client is None or self._client.is_closed:
            async with self._client_lock:
                # Double-check after acquiring lock
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        timeout=self._timeout,
                        limits=httpx.Limits(
                            max_connections=settings.GROBID_MAX_CONNECTIONS,
                            max_keepalive_connections=settings.GROBID_KEEPALIVE_CONNECTIONS,
                        ),
                    )
                    logger.debug(
                        "Created new GROBID HTTP client with connection pooling"
                    )
        return self._client

    async def close(self):
        """Close the HTTP client connections"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(settings.GROBID_MAX_RETRIES),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        retry=should_retry_http_error,
    )
    async def process_header_document(
        self,
        pdf_content: bytes,
        consolidate_header: Optional[int] = None,
        skip_validation: bool = False,
    ) -> str:
        """
        Process PDF header extraction with configurable consolidation

        Args:
            pdf_content: Raw PDF bytes
            consolidate_header: Consolidation level (0=none, 1=full, 2=DOI only)
            skip_validation: Skip PDF validation if already done

        Returns:
            TEI XML format header data
        """
        if consolidate_header is None:
            consolidate_header = settings.GROBID_CONSOLIDATE_HEADER

        # Validate PDF before processing (unless already validated)
        if not skip_validation:
            is_valid, error_msg = validate_pdf(pdf_content)
            if not is_valid:
                logger.error(f"PDF validation failed: {error_msg}")
                raise GrobidValidationError(str(error_msg))

        # Always request XML format
        headers = {"Accept": "application/xml"}

        # Use shared client with connection pooling
        client = await self._get_client()
        files = {"input": ("document.pdf", pdf_content, "application/pdf")}
        data = {
            "consolidateHeader": str(consolidate_header),
            "includeRawAffiliations": "0",
            "teiCoordinates": "0",
        }

        try:
            logger.info(
                f"Sending PDF to GROBID header extraction ({len(pdf_content)} bytes)"
            )
            response = await client.post(
                f"{self.base_url}/api/processHeaderDocument",
                files=files,
                data=data,
                headers=headers,
            )

            if response.status_code == 200:
                logger.info("GROBID header extraction successful")
                return response.text
            else:
                logger.error(f"GROBID error {response.status_code}: {response.text}")
                raise RuntimeError(
                    f"GROBID error {response.status_code}: {response.text}"
                )

        except httpx.TimeoutException as e:
            logger.warning(
                f"GROBID header request timed out after {settings.GROBID_TIMEOUT_SECONDS}s (will retry): {e}"
            )
            raise  # Let retry decorator handle this
        except httpx.ConnectError as e:
            logger.warning(
                f"Failed to connect to GROBID service at {self.base_url} (will retry): {e}"
            )
            raise  # Let retry decorator handle this
        except Exception as e:
            logger.error(f"GROBID header request failed with unexpected error: {e}")
            raise

    @retry(
        stop=stop_after_attempt(settings.GROBID_MAX_RETRIES),
        wait=wait_random_exponential(multiplier=1, min=2, max=10),
        retry=should_retry_http_error,
    )
    async def process_references_only(
        self,
        pdf_content: bytes,
        consolidate_citations: int = None,  # type: ignore
        skip_validation: bool = False,
    ) -> str:
        """
        Process PDF reference extraction with configurable consolidation

        Args:
            pdf_content: Raw PDF bytes
            consolidate_citations: Consolidation level (0=none, 1=full, 2=DOI only)
            skip_validation: Skip PDF validation if already done

        Returns:
            TEI XML references section
        """
        if consolidate_citations is None:
            consolidate_citations = settings.GROBID_CONSOLIDATE_CITATIONS

        # Validate PDF before processing (unless already validated)
        if not skip_validation:
            is_valid, error_msg = validate_pdf(pdf_content)
            if not is_valid:
                logger.error(f"PDF validation failed: {error_msg}")
                raise GrobidValidationError(str(error_msg))

        # Always request XML format for consistency
        headers = {"Accept": "application/xml"}

        # Use shared client with connection pooling
        client = await self._get_client()
        files = {"input": ("document.pdf", pdf_content, "application/pdf")}
        data = {
            "consolidateCitations": str(consolidate_citations),
            "includeRawCitations": "0",
        }

        try:
            logger.info(
                f"Sending PDF to GROBID reference extraction ({len(pdf_content)} bytes)"
            )
            response = await client.post(
                f"{self.base_url}/api/processReferences",
                files=files,
                data=data,
                headers=headers,
            )

            if response.status_code == 200:
                logger.info("GROBID reference extraction successful")
                return response.text
            else:
                logger.error(f"GROBID error {response.status_code}: {response.text}")
                raise RuntimeError(
                    f"GROBID error {response.status_code}: {response.text}"
                )

        except httpx.TimeoutException as e:
            logger.warning(
                f"GROBID references request timed out after {settings.GROBID_TIMEOUT_SECONDS}s (will retry): {e}"
            )
            raise  # Let retry decorator handle this
        except httpx.ConnectError as e:
            logger.warning(
                f"Failed to connect to GROBID service at {self.base_url} (will retry): {e}"
            )
            raise  # Let retry decorator handle this
        except Exception as e:
            logger.error(f"GROBID references request failed with unexpected error: {e}")
            raise

    def extract_header_metadata(self, tei_xml: str) -> Dict[str, Any]:
        """
        Extract structured header metadata from TEI XML using enhanced parser

        Returns:
            Dictionary with main article metadata (enhanced with new parser)
        """
        try:
            # Use new enhanced parser - it returns a dict now
            metadata = self.parser.parse_string(tei_xml)

            # Add year field for backward compatibility with type safety
            result = metadata.copy()
            pub_date = metadata["publication_date"]
            if pub_date and isinstance(pub_date, str) and len(pub_date) >= 4:
                result["year"] = pub_date[:4]
            else:
                result["year"] = None
            result["date"] = metadata["publication_date"]

            logger.info(
                f"Enhanced parser extracted: title={bool(result['title'])}, doi={bool(result['doi'])}, authors={len(result['authors'])}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Enhanced parser failed for header metadata (XML length: {len(tei_xml)} chars): {e}"
            )
            raise GrobidParsingError(str(e))

    def extract_references(self, tei_xml: str) -> List[Dict[str, Any]]:
        """
        Extract structured reference data from TEI XML using enhanced parser

        Returns:
            List of references with full structured metadata (enhanced with new parser)
        """
        try:
            # Use new enhanced parser - it returns a list of dicts now
            references = self.parser.parse_references_string(tei_xml)

            logger.info(f"Enhanced parser extracted {len(references)} references")
            return references

        except Exception as e:
            logger.error(
                f"Enhanced reference parser failed (XML length: {len(tei_xml)} chars): {e}"
            )
            raise GrobidParsingError(str(e))
