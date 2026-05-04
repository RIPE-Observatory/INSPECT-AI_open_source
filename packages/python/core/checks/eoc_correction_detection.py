"""
INSPECT-SR 1.2: Expression of Concern & Correction Detection

Check main article ONLY for expressions of concern and corrections in Retraction Watch database.
Does NOT check references (only main article).
Only returns records with retraction_nature in ['Expression of concern', 'Correction'].
"""

import logging
import uuid
from typing import Optional, Dict, Any
import logfire

from core.db.session import AsyncSessionFactory
from core.db.crud.retraction import find_eoc_corrections_by_doi, find_eoc_corrections_by_title

logger = logging.getLogger(__name__)


async def execute_eoc_correction_detection_check(
    job_id: uuid.UUID,
    main_doi_payload: Optional[Dict[str, Any]],
    reference_dois_payload: Optional[Dict[str, Any]],  # Not used, but kept for API consistency
) -> Dict[str, Any]:
    """
    INSPECT-SR 1.2: Expression of Concern & Correction Detection

    Check ONLY main article for EOC/corrections in Retraction Watch database.
    References are NOT checked (INSPECT-SR 1.2 specification).
    Uses DOI first (exact match), falls back to title (fuzzy match) if DOI unavailable.

    Args:
        job_id: Job UUID for logging
        main_doi_payload: Main article metadata from GROBID (doi_value, main_title)
        reference_dois_payload: Not used (kept for API consistency)

    Returns:
        Dictionary with main_article_result only (no references)
    """
    with logfire.span("eoc_correction_detection", job_id=str(job_id)):
        logger.info(f"[Job {job_id}] Starting EOC/correction detection check (INSPECT-SR 1.2)")
        logfire.info("Starting EOC/correction detection check", job_id=str(job_id))

        output = {
            "main_article_result": None,
            "summary": {
                "main_article_has_eoc_or_correction": False,
                "total_notices": 0,
            },
            "error_message": None,
        }

        try:
            async with AsyncSessionFactory() as db:
                # Check main article only
                if main_doi_payload:
                    main_doi = main_doi_payload.get("doi_value", "").strip() if isinstance(main_doi_payload.get("doi_value"), str) else None
                    main_title = main_doi_payload.get("main_title", "").strip() if isinstance(main_doi_payload.get("main_title"), str) else None

                    if main_doi or main_title:
                        main_result = await check_paper_for_eoc_correction(
                            db=db,
                            doi=main_doi,
                            title=main_title,
                            job_id=job_id
                        )
                        output["main_article_result"] = main_result
                        output["summary"]["main_article_has_eoc_or_correction"] = main_result.get("found", False)
                        output["summary"]["total_notices"] = len(main_result.get("notices", []))

                        if main_result.get("found", False):
                            logfire.warn("EOC/CORRECTION FOUND for main article", job_id=str(job_id), doi=main_doi, count=output["summary"]["total_notices"])
                    else:
                        logger.warning(f"[Job {job_id}] No DOI or title found for main article")
                        output["main_article_result"] = {
                            "found": False,
                            "searched_doi": None,
                            "searched_title": None,
                            "lookup_method": "not_searched",
                            "error": "No DOI or title available for main article",
                        }

                # Generate summary message
                if output["summary"]["main_article_has_eoc_or_correction"]:
                    total_notices = output["summary"]["total_notices"]
                    output["summary"]["message"] = f"Main article has {total_notices} EOC/correction notice(s)."
                else:
                    output["summary"]["message"] = "Main article: No EOC/correction notices found."

                logger.info(
                    f"[Job {job_id}] EOC/correction detection completed: {output['summary']['message']}"
                )

        except Exception as e:
            logger.error(
                f"[Job {job_id}] Error during EOC/correction detection check: {e}",
                exc_info=True
            )
            logfire.error("EOC/correction detection check failed", exc_info=True, job_id=str(job_id))
            output["error_message"] = f"Check failed: {str(e)}"
            output["summary"]["message"] = "Check failed due to internal error"

        return output


async def check_paper_for_eoc_correction(
    db,
    doi: Optional[str],
    title: Optional[str],
    job_id: uuid.UUID,
    similarity_threshold: float = 0.9
) -> Dict[str, Any]:
    """
    Check main article for EOC/correction notices.

    Strategy:
    1. Try DOI lookup first (exact match)
    2. Fall back to title lookup (fuzzy match) if DOI unavailable
    3. Return structured result with EOC/correction details if found

    Args:
        db: Database session
        doi: Paper DOI (optional)
        title: Paper title (optional)
        job_id: Job UUID for logging
        similarity_threshold: Minimum similarity score for title matching

    Returns:
        Dictionary with found status and EOC/correction details
    """
    result = {
        "found": False,
        "searched_doi": doi,
        "searched_title": title,
        "lookup_method": None,
        "notices": [],
    }

    try:
        # Try DOI lookup first
        if doi:
            notices = await find_eoc_corrections_by_doi(db, doi)
            if notices:
                result["found"] = True
                result["lookup_method"] = "doi"
                result["notices"] = [format_notice(notices[0])]  # Return only top match
                logger.info(
                    f"[Job {job_id}] Found EOC/correction notice for main article via DOI: {doi}"
                )
                return result

        # Fall back to title lookup
        if title:
            notices = await find_eoc_corrections_by_title(db, title, similarity_threshold)
            if notices:
                result["found"] = True
                result["lookup_method"] = "title"
                result["notices"] = [format_notice(notices[0])]  # Return only top match
                logger.info(
                    f"[Job {job_id}] Found EOC/correction notice for main article via title match"
                )
                return result

        # No notices found
        result["lookup_method"] = "doi" if doi else ("title" if title else "not_searched")
        logger.debug(f"[Job {job_id}] No EOC/correction notices found for main article")

    except Exception as e:
        logger.error(
            f"[Job {job_id}] Error checking main article for EOC/correction: {e}",
            exc_info=True
        )
        result["error"] = str(e)

    return result


def format_notice(notice) -> Dict[str, Any]:
    """
    Format a Retraction ORM object (EOC/Correction) into a serializable dictionary.

    Args:
        notice: Retraction ORM object from database (with retraction_nature = EOC or Correction)

    Returns:
        Dictionary with notice details
    """
    return {
        "record_id": notice.record_id,
        "title": notice.title,
        "original_paper_doi": notice.original_paper_doi,
        "retraction_doi": notice.retraction_doi,
        "retraction_nature": notice.retraction_nature,
        "retraction_date": notice.retraction_date.isoformat() if notice.retraction_date else None,
        "original_paper_date": notice.original_paper_date.isoformat() if notice.original_paper_date else None,
        "journal": notice.journal,
        "publisher": notice.publisher,
        "reason": notice.reason,
        "notes": notice.notes,
        "authors": [
            {
                "name": author.author_name,
                "position": author.author_position,
            }
            for author in notice.authors
        ],
    }
