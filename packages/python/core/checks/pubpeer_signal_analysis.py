import logging
import uuid
import time
from typing import Optional, Dict, Any
from pydantic import ValidationError
import logfire

from core.schemas.pubpeer_results import (
    PubPeerSignalAnalysisOutput,
    PubPeerLookupResult,
    PubPeerAPIResult,
)
from core.services.pubpeer_service import PubPeerService


logger = logging.getLogger(__name__)


async def execute_pubpeer_analysis_check(
    job_id: uuid.UUID,
    main_doi_payload: Optional[Dict[str, Any]],
) -> PubPeerSignalAnalysisOutput:
    """
    Run the PubPeer signal analysis workflow.

    The process looks up the main study DOI, queries the PubPeer API, performs
    optional scraping for additional context, and returns a structured summary of
    any post-publication discussions.

    Args:
        job_id: UUID of the processing job
        main_doi_payload: Payload containing the primary DOI sourced from the metadata extraction step.

    Returns:
        PubPeerSignalAnalysisOutput with main paper results and statistics
    """
    with logfire.span("pubpeer_signal_analysis", job_id=str(job_id)):
        logger.info(f"Starting PubPeer analysis for job {job_id}")
        logfire.info("Starting PubPeer signal analysis", job_id=str(job_id))
        start_time = time.time()
        api_calls_made = 0
        scraping_attempts = 0

        try:
            # Extract main paper DOI from previously collected metadata
            main_doi = None
            if main_doi_payload and main_doi_payload.get("status") == "COMPLETED_SUCCESS":
                main_doi = main_doi_payload.get("doi_value")
                if main_doi:
                    logger.info(f"Processing main paper DOI for job {job_id}: {main_doi}")

            # Note: We only process the main paper DOI, not reference DOIs
            # PubPeer analysis focuses on the main paper being analyzed

            # Ensure a primary DOI is available before invoking downstream services
            if not main_doi:
                logger.warning(
                    f"No main DOI available for PubPeer analysis in job {job_id}"
                )
                return PubPeerSignalAnalysisOutput(
                    status="COMPLETED_NOT_FOUND",
                    main_paper_result=None,
                    reference_results=[],
                    error_message="No primary DOI available for PubPeer analysis",
                )

            # Initialize service
            pubpeer_service = PubPeerService()

            # Process main paper
            logger.info(f"Processing main DOI for job {job_id}: {main_doi}")
            api_calls_made += 1  # Track API call
            main_data = await pubpeer_service.lookup_doi_and_scrape(main_doi)

            # Track scraping attempt if URL was found
            if main_data.get("found") and main_data.get("api_result", {}).get("feedbacks"):
                scraping_attempts += 1

            # Convert to structured result - use all data from service
            api_result = None
            if main_data.get("api_result"):
                api_result = PubPeerAPIResult(**main_data["api_result"])

            main_result = PubPeerLookupResult(
                doi=main_data["doi"],
                found=main_data["found"],
                api_result=api_result,
                scraped_comments=main_data.get(
                    "scraped_comments"
                ),  # Already validated PubPeerScrapedData
                total_cost=main_data.get("total_cost", 0.0),
                total_time=main_data.get("total_time", 0.0),
                error=main_data.get("error"),
            )

            processing_time = time.time() - start_time

            # Determine status - cleaner logic
            has_scraped_data = main_result.found and main_result.scraped_comments
            if main_result.error:
                status = "FAILED"
            else:
                status = "COMPLETED_SUCCESS" if has_scraped_data else "COMPLETED_NOT_FOUND"

            if has_scraped_data:
                logfire.warn("PubPeer discussions found for main article", job_id=str(job_id), doi=main_doi, cost_usd=main_result.total_cost)

            result = PubPeerSignalAnalysisOutput(
                status=status,
                main_paper_result=main_result,
                reference_results=[],
                summary={},
                processing_info={
                    "processing_time_seconds": round(processing_time, 2),
                    "api_calls_made": api_calls_made,
                    "scraping_attempts": scraping_attempts,
                    "scraping_successes": 1 if has_scraped_data else 0,
                    "total_scraping_time_seconds": main_result.total_time,
                },
            )

            logger.info(
                f"PubPeer analysis completed for job {job_id} in {processing_time:.2f}s"
            )

            return result

        except ValidationError as e:
            processing_time = time.time() - start_time
            logger.error(
                f"PubPeer analysis validation failed for job {job_id}: {e}", exc_info=True
            )
            logfire.error("PubPeer analysis validation failed", exc_info=True, job_id=str(job_id))

            return PubPeerSignalAnalysisOutput(
                status="FAILED",
                main_paper_result=None,
                reference_results=[],
                error_message=f"Data validation failed: {str(e)}",
                processing_info={
                    "processing_time_seconds": round(processing_time, 2),
                    "api_calls_made": api_calls_made,
                    "scraping_attempts": scraping_attempts,
                    "scraping_successes": 0,
                    "total_scraping_time_seconds": 0.0,
                },
            )
        except ValueError as e:
            processing_time = time.time() - start_time
            logger.error(
                f"PubPeer analysis value error for job {job_id}: {e}", exc_info=True
            )
            logfire.error("PubPeer analysis value error", exc_info=True, job_id=str(job_id))

            return PubPeerSignalAnalysisOutput(
                status="FAILED",
                main_paper_result=None,
                reference_results=[],
                error_message=f"Service error: {str(e)}",
                processing_info={
                    "processing_time_seconds": round(processing_time, 2),
                    "api_calls_made": api_calls_made,
                    "scraping_attempts": scraping_attempts,
                    "scraping_successes": 0,
                    "total_scraping_time_seconds": 0.0,
                },
            )
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"PubPeer analysis unexpected error for job {job_id}: {e}", exc_info=True
            )
            logfire.error("PubPeer analysis unexpected error", exc_info=True, job_id=str(job_id))

            return PubPeerSignalAnalysisOutput(
                status="FAILED",
                main_paper_result=None,
                reference_results=[],
                error_message=f"Unexpected error: {str(e)}",
                processing_info={
                    "processing_time_seconds": round(processing_time, 2),
                    "api_calls_made": api_calls_made,
                    "scraping_attempts": scraping_attempts,
                    "scraping_successes": 0,
                    "total_scraping_time_seconds": 0.0,
                },
            )
