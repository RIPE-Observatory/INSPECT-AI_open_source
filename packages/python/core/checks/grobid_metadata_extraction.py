import logging
import uuid
import time
from typing import Dict, Any
import aiofiles
import logfire

from core.services.grobid_service import GrobidService, validate_doi
from core.config import settings

logger = logging.getLogger(__name__)


class GrobidExtractionCheckError(Exception):
    """Exception for GROBID extraction failures."""

    pass


async def execute_grobid_extraction_check(
    job_id: uuid.UUID,
    pdf_file_path: str,
) -> Dict[str, Any]:
    """
    Extract main publication details and references using GROBID.

    Returns data for retraction watch check.
    """
    with logfire.span("grobid_extraction", job_id=str(job_id)):
        logger.info(f"Starting GROBID extraction for job {job_id}")
        logfire.info("Starting GROBID extraction", job_id=str(job_id))

        start_time = time.time()

        try:
            # Read PDF with async I/O for better concurrency
            try:
                async with aiofiles.open(pdf_file_path, "rb") as f:
                    pdf_content = await f.read()
            except (IOError, OSError, PermissionError) as e:
                logger.error(
                    f"Failed to read PDF file {pdf_file_path} for job {job_id}: {e}"
                )
                logfire.error("Failed to read PDF file", exc_info=True, job_id=str(job_id))
                raise GrobidExtractionCheckError(f"Cannot read PDF file: {e}")
            except MemoryError as e:
                logger.error(
                    f"PDF file too large to read for job {job_id}: {pdf_file_path}"
                )
                raise GrobidExtractionCheckError(f"PDF file too large for processing: {e}")

            # Initialize GROBID service with proper resource management
            async with GrobidService() as grobid_service:
                # Validate PDF once before processing to avoid duplication
                from core.services.grobid_service import validate_pdf

                is_valid, error_msg = validate_pdf(pdf_content)
                if not is_valid:
                    logger.error(f"PDF validation failed for job {job_id}: {error_msg}")
                    raise GrobidExtractionCheckError(f"PDF validation failed: {error_msg}")

                # Extract header and references sequentially to avoid GROBID connection exhaustion
                logger.info(f"Starting sequential GROBID API calls for job {job_id}")

                header_xml = None
                refs_xml = None

                # Handle header extraction first
                try:
                    with logfire.span("grobid.header_extraction", job_id=str(job_id)):
                        header_xml = await grobid_service.process_header_document(
                            pdf_content=pdf_content,
                            consolidate_header=settings.GROBID_CONSOLIDATE_HEADER,
                            skip_validation=True,  # Already validated above
                        )
                        logger.info(f"Header extraction succeeded for job {job_id}")
                        logfire.info("GROBID header extraction successful", job_id=str(job_id))
                except Exception as e:
                    logger.error(f"Header extraction failed for job {job_id}: {e}")
                    logfire.error("GROBID header extraction failed", exc_info=True, job_id=str(job_id))
                    raise e

                # Handle references extraction second (with timeout tolerance)
                try:
                    with logfire.span("grobid.references_extraction", job_id=str(job_id)):
                        refs_xml = await grobid_service.process_references_only(
                            pdf_content=pdf_content,
                            consolidate_citations=settings.GROBID_CONSOLIDATE_CITATIONS,
                            skip_validation=True,  # Already validated above
                        )
                        logger.info(f"References extraction succeeded for job {job_id}")
                        logfire.info("GROBID references extraction successful", job_id=str(job_id))
                except Exception as e:
                    logger.warning(f"References extraction failed for job {job_id}: {e}")
                    logfire.warn("GROBID references extraction failed - graceful degradation", job_id=str(job_id))
                    # Continue with header-only processing
                    refs_xml = None
                    logger.warning(
                        f"Continuing with header-only processing for job {job_id} due to references failure"
                    )

                processing_time = time.time() - start_time

                # Parse header using enhanced parser with error handling
                main_metadata = {}
                if header_xml:
                    try:
                        main_metadata = grobid_service.extract_header_metadata(header_xml)
                    except Exception as e:
                        logger.error(
                            f"Failed to parse header metadata for job {job_id}: {e}"
                        )
                        # Continue with empty metadata rather than failing completely
                        main_metadata = {}

                # Parse references using enhanced parser with error handling
                references = []
                if refs_xml:
                    try:
                        references = grobid_service.extract_references(refs_xml)
                    except Exception as e:
                        logger.error(f"Failed to parse references for job {job_id}: {e}")
                        # Continue with empty references rather than failing completely
                        references = []

            # Extract and validate data for results
            raw_main_doi = main_metadata.get("doi", "")
            main_doi = validate_doi(raw_main_doi) if raw_main_doi else ""
            main_title = main_metadata.get("title", "")

            if raw_main_doi and not main_doi:
                logger.warning(
                    f"Invalid DOI format rejected for job {job_id}: {raw_main_doi}"
                )
            elif main_doi:
                logger.info(f"Valid DOI extracted for job {job_id}: {main_doi}")
            # Build rich author data with professional titles and affiliations
            main_authors = []
            authors_data = main_metadata.get("authors", [])
            if not isinstance(authors_data, list):
                logger.warning(
                    f"Invalid authors data structure for job {job_id}: expected list, got {type(authors_data)}"
                )
                authors_data = []

            for author in authors_data:
                if not isinstance(author, dict):
                    logger.debug(
                        f"Skipping invalid author entry for job {job_id}: {author}"
                    )
                    continue

                # Build name parts
                name_parts = [
                    author.get("forename"),
                    author.get("middle_name"),
                    author.get("surname"),
                ]
                # Filter out None, empty strings, and non-string values
                valid_parts = [
                    part.strip()
                    for part in name_parts
                    if part and isinstance(part, str) and part.strip()
                ]

                if valid_parts:
                    full_name = " ".join(valid_parts)

                    # Create rich author object with preserved metadata
                    author_obj = {
                        "name": full_name,
                        "forename": author.get("forename"),
                        "middle_name": author.get("middle_name"),
                        "surname": author.get("surname"),
                        "lastname": author.get("surname"),
                        "professional_title": author.get("role"),  # MD, PhD, etc.
                        "affiliations": author.get("affiliations", []),  # Institution names
                        "is_corresponding": author.get("is_corresponding", False),
                    }

                    main_authors.append(author_obj)
                else:
                    logger.debug(
                        f"Skipping author with no valid name parts for job {job_id}: {author}"
                    )
            # Validate reference DOIs
            reference_dois = []
            for ref in references:
                raw_doi = ref.get("doi")
                if isinstance(raw_doi, str):
                    validated_doi = validate_doi(raw_doi)
                    if validated_doi:
                        reference_dois.append(validated_doi)
                    else:
                        logger.debug(
                            f"Invalid reference DOI rejected for job {job_id}: {raw_doi}"
                        )

            # Log completion with graceful degradation info
            degradation_msg = (
                " (references timed out, graceful degradation applied)"
                if refs_xml is None
                else ""
            )
            logger.info(
                f"GROBID extraction completed in {processing_time:.2f}s: "
                f"DOI={main_doi}, References={len(reference_dois)}{degradation_msg}"
            )

            # Return results for check 4, 5, and retraction watch
            return {
                "grobid_primary_metadata": {
                    "doi_value": main_doi,
                    "status": "COMPLETED_SUCCESS" if main_doi else "COMPLETED_NOT_FOUND",
                    "main_title": main_title,
                    "main_authors": main_authors,
                    # Add all available main paper metadata
                    "journal": main_metadata.get("journal"),
                    "journal_abbrev": main_metadata.get("journal_abbrev"),
                    "publisher": main_metadata.get("publisher"),
                    "volume": main_metadata.get("volume"),
                    "issue": main_metadata.get("issue"),
                    "pages": main_metadata.get("pages"),
                    "page_from": main_metadata.get("page_from"),
                    "page_to": main_metadata.get("page_to"),
                    "publication_date": main_metadata.get("publication_date"),
                    "year": main_metadata.get("year"),
                    "issn": main_metadata.get("issn"),
                    "eissn": main_metadata.get("eissn"),
                    "total_affiliations": len(main_metadata.get("affiliations", [])),
                    "total_authors": len(main_authors),
                },
                "grobid_reference_metadata": {
                    "status": "COMPLETED_SUCCESS"
                    if reference_dois
                    else (
                        "COMPLETED_NOT_FOUND"
                        if refs_xml is not None
                        else "FAILED_TIMEOUT_GRACEFUL_DEGRADATION"
                    ),
                    "references_full": [
                        {
                            "title": ref.get("title"),
                            "doi": (
                                validate_doi(raw_doi) if isinstance(raw_doi, str) else None
                            ),
                        }
                        for ref in references
                        for raw_doi in [ref.get("doi")]
                        if ref.get("title")
                        or (isinstance(raw_doi, str) and validate_doi(raw_doi))
                    ],
                    "error_message": "References extraction timed out, continuing with header-only processing"
                    if refs_xml is None
                    else None,
                },
                "grobid_metadata": {
                    "processing_time_seconds": processing_time,
                    "total_references": len(references),
                    "references_with_dois": len(reference_dois),
                },
            }

        except Exception as e:
            logger.error(f"GROBID extraction failed for job {job_id}: {e}")
            logfire.error("GROBID extraction failed", exc_info=True, job_id=str(job_id))
            return {
                "grobid_primary_metadata": {
                    "doi_value": "",
                    "status": "FAILED",
                    "error": str(e),
                },
                "grobid_reference_metadata": {
                    "status": "FAILED",
                    "references_full": [],
                    "error_message": str(e),
                },
                "grobid_metadata": {
                    "processing_time_seconds": 0,
                    "total_references": 0,
                    "references_with_dois": 0,
                    "error": str(e),
                },
            }
