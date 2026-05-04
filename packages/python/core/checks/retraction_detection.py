"""
INSPECT-SR 1.1: Retraction Detection

Check main article and references for retractions in the Retraction Watch database.
Only returns records with retraction_nature='Retraction' (excludes EOC and corrections).
"""

import asyncio
import logging
import uuid
from typing import Optional, Dict, Any, cast
import logfire

from sqlalchemy.ext.asyncio import AsyncSession
from core.db.session import AsyncSessionFactory
from core.db.crud.retraction import find_retractions_by_doi, find_retractions_by_title

logger = logging.getLogger(__name__)

# Limit concurrent database queries for parallel reference checking
# This now limits concurrent CPU-bound work, not DB connections
_db_semaphore = asyncio.Semaphore(15)


async def execute_retraction_detection_check(
    job_id: uuid.UUID,
    main_doi_payload: Optional[Dict[str, Any]],
    reference_dois_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    INSPECT-SR 1.1: Retraction Detection

    Check main article and all references for retractions in Retraction Watch database.
    Uses DOI first (exact match), falls back to title (fuzzy match) if DOI unavailable.

    OPTIMIZATION: Uses a single database session for all checks (main + all references)
    to avoid connection pool exhaustion.

    Args:
        job_id: Job UUID for logging
        main_doi_payload: Main article metadata from GROBID (doi_value, main_title)
        reference_dois_payload: Reference metadata from GROBID (references_full)

    Returns:
        Dictionary with main_article_result and reference_results
    """
    with logfire.span("retraction_detection", job_id=str(job_id)):
        logger.info(f"[Job {job_id}] Starting retraction detection check (INSPECT-SR 1.1)")
        logfire.info("Starting retraction detection check", job_id=str(job_id))

        output = {
            "main_article_result": None,
            "reference_results": [],
            "summary": {
                "main_article_retracted": False,
                "references_checked": 0,
                "references_retracted": 0,
            },
            "error_message": None,
        }

        try:
            # Create ONE database session for entire check (main + all references)
            async with AsyncSessionFactory() as db:
                # Check main article
                if main_doi_payload:
                    main_doi = main_doi_payload.get("doi_value", "").strip() if isinstance(main_doi_payload.get("doi_value"), str) else None
                    main_title = main_doi_payload.get("main_title", "").strip() if isinstance(main_doi_payload.get("main_title"), str) else None

                    if main_doi or main_title:
                        main_result = await check_paper_for_retraction_with_session(
                            db=db,
                            doi=main_doi,
                            title=main_title,
                            paper_type="main_article",
                            job_id=job_id
                        )
                        output["main_article_result"] = main_result
                        output["summary"]["main_article_retracted"] = main_result.get("found", False)

                        if main_result.get("found", False):
                            logfire.warn("RETRACTION FOUND for main article", job_id=str(job_id), doi=main_doi)
                    else:
                        logger.warning(f"[Job {job_id}] No DOI or title found for main article")
                        output["main_article_result"] = {
                            "found": False,
                            "searched_doi": None,
                            "searched_title": None,
                            "lookup_method": "not_searched",
                            "error": "No DOI or title available for main article",
                        }

                # Check references (parallel execution with SAME session)
                if reference_dois_payload:
                    references_full = reference_dois_payload.get("references_full", [])
                    output["summary"]["references_checked"] = len(references_full)

                    # Build list of tasks for parallel execution (all use same db session)
                    tasks = []
                    for idx, ref in enumerate(references_full):
                        ref_doi = ref.get("doi", "").strip() if ref.get("doi") else None
                        ref_title = ref.get("title", "").strip() if ref.get("title") else None

                        if ref_doi or ref_title:
                            task = check_paper_for_retraction_with_session(
                                db=db,  # Pass same session to all tasks
                                doi=ref_doi,
                                title=ref_title,
                                paper_type=f"reference_{idx + 1}",
                                job_id=job_id
                            )
                            tasks.append(task)

                    # Execute all reference checks in parallel
                    if tasks:
                        ref_results = await asyncio.gather(*tasks, return_exceptions=True)

                        # Process results
                        for ref_result in ref_results:
                            # Handle exceptions from individual checks
                            if isinstance(ref_result, Exception):
                                logger.error(
                                    f"[Job {job_id}] Reference check failed: {ref_result}",
                                    exc_info=ref_result
                                )
                                continue

                            # Type guard: ref_result is Dict[str, Any] here
                            result_dict = cast(Dict[str, Any], ref_result)
                            output["reference_results"].append(result_dict)

                            if result_dict.get("found", False):
                                output["summary"]["references_retracted"] += 1

            # Generate summary message
            main_status = "RETRACTED" if output["summary"]["main_article_retracted"] else "CLEAN"
            refs_retracted = output["summary"]["references_retracted"]
            refs_total = output["summary"]["references_checked"]

            output["summary"]["message"] = (
                f"Main article: {main_status}. "
                f"References: {refs_retracted}/{refs_total} retracted."
            )

            logger.info(
                f"[Job {job_id}] Retraction detection completed: {output['summary']['message']}"
            )

            if output["summary"]["references_retracted"] > 0:
                logfire.warn(
                    f"Found {output['summary']['references_retracted']} retracted references",
                    job_id=str(job_id),
                    retracted_count=output["summary"]["references_retracted"],
                )

        except Exception as e:
            logger.error(
                f"[Job {job_id}] Error during retraction detection check: {e}",
                exc_info=True
            )
            logfire.error("Retraction detection check failed", exc_info=True, job_id=str(job_id))
            output["error_message"] = f"Check failed: {str(e)}"
            output["summary"]["message"] = "Check failed due to internal error"

        return output


async def check_paper_for_retraction_with_session(
    db: AsyncSession,
    doi: Optional[str],
    title: Optional[str],
    paper_type: str,
    job_id: uuid.UUID,
    similarity_threshold: float = 0.9
) -> Dict[str, Any]:
    """
    Check a single paper (main or reference) for retraction using provided session.

    Strategy:
    1. Try DOI lookup first (exact match)
    2. Fall back to title lookup (fuzzy match) if DOI unavailable
    3. Return structured result with retraction details if found

    Args:
        db: Database session (passed in, NOT created here)
        doi: Paper DOI (optional)
        title: Paper title (optional)
        paper_type: Description for logging (e.g., "main_article", "reference_1")
        job_id: Job UUID for logging
        similarity_threshold: Minimum similarity score for title matching

    Returns:
        Dictionary with found status and retraction details
    """
    result = {
        "found": False,
        "searched_doi": doi,
        "searched_title": title,
        "lookup_method": None,
        "retractions": [],
    }

    try:
        # Semaphore now only limits concurrent CPU-bound work, not DB connections
        async with _db_semaphore:
            # Try DOI lookup first
            if doi:
                retractions = await find_retractions_by_doi(db, doi)
                if retractions:
                    result["found"] = True
                    result["lookup_method"] = "doi"
                    result["retractions"] = [format_retraction(retractions[0])]  # Return only top match
                    logger.info(
                        f"[Job {job_id}] Found retraction for {paper_type} via DOI: {doi}"
                    )
                    return result

            # Fall back to title lookup
            if title:
                retractions = await find_retractions_by_title(db, title, similarity_threshold)
                if retractions:
                    result["found"] = True
                    result["lookup_method"] = "title"
                    result["retractions"] = [format_retraction(retractions[0])]  # Return only top match
                    logger.info(
                        f"[Job {job_id}] Found retraction for {paper_type} via title match (similarity: {retractions[0].title})"
                    )
                    return result

            # No retractions found
            result["lookup_method"] = "doi" if doi else ("title" if title else "not_searched")
            logger.debug(f"[Job {job_id}] No retractions found for {paper_type}")

    except Exception as e:
        logger.error(
            f"[Job {job_id}] Error checking {paper_type} for retraction: {e}",
            exc_info=True
        )
        result["error"] = str(e)

    return result


def format_retraction(retraction) -> Dict[str, Any]:
    """
    Format a Retraction ORM object into a serializable dictionary.

    Args:
        retraction: Retraction ORM object from database

    Returns:
        Dictionary with retraction details
    """
    return {
        "record_id": retraction.record_id,
        "title": retraction.title,
        "original_paper_doi": retraction.original_paper_doi,
        "retraction_doi": retraction.retraction_doi,
        "retraction_nature": retraction.retraction_nature,
        "retraction_date": retraction.retraction_date.isoformat() if retraction.retraction_date else None,
        "original_paper_date": retraction.original_paper_date.isoformat() if retraction.original_paper_date else None,
        "journal": retraction.journal,
        "publisher": retraction.publisher,
        "reason": retraction.reason,
        "authors": [
            {
                "name": author.author_name,
                "position": author.author_position,
            }
            for author in retraction.authors
        ],
    }
