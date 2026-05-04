"""
INSPECT-SR 1.3: Author Retraction History

Check each author of the main article for their retraction history.
Returns up to 20 most recent retractions per author (exact name match, case-insensitive).
"""

import logging
import uuid
from typing import Optional, Dict, Any
import logfire

from core.db.session import AsyncSessionFactory
from core.db.crud.retraction import find_retractions_by_author

logger = logging.getLogger(__name__)


async def execute_author_retraction_history_check(
    job_id: uuid.UUID,
    main_doi_payload: Optional[Dict[str, Any]],
    reference_dois_payload: Optional[Dict[str, Any]],  # Not used, but kept for API consistency
) -> Dict[str, Any]:
    """
    INSPECT-SR 1.3: Author Retraction History

    Check each author of the main article for their retraction history.
    Returns up to 20 most recent retractions per author.
    Uses exact full name matching (case-insensitive).

    Args:
        job_id: Job UUID for logging
        main_doi_payload: Main article metadata from GROBID (main_authors with full names)
        reference_dois_payload: Not used (kept for API consistency)

    Returns:
        Dictionary with author_results (list of authors with their retraction histories)
    """
    with logfire.span("author_retraction_history", job_id=str(job_id)):
        logger.info(f"[Job {job_id}] Starting author retraction history check (INSPECT-SR 1.3)")
        logfire.info("Starting author retraction history check", job_id=str(job_id))

        output = {
            "author_results": [],
            "summary": {
                "total_authors_checked": 0,
                "authors_with_retractions": 0,
                "total_retractions_found": 0,
            },
            "error_message": None,
        }

        try:
            async with AsyncSessionFactory() as db:
                # Extract authors from main article
                if main_doi_payload:
                    main_authors = main_doi_payload.get("main_authors", [])

                    if not main_authors:
                        logger.warning(f"[Job {job_id}] No authors found in main article metadata")
                        output["summary"]["message"] = "No authors found in main article"
                        return output

                    output["summary"]["total_authors_checked"] = len(main_authors)

                    # Check each author
                    for author_data in main_authors:
                        author_result = await check_author_retraction_history(
                            db=db,
                            author_data=author_data,
                            job_id=job_id
                        )
                        output["author_results"].append(author_result)

                        if author_result.get("has_retractions", False):
                            output["summary"]["authors_with_retractions"] += 1
                            output["summary"]["total_retractions_found"] += len(author_result.get("retractions", []))

                # Generate summary message
                authors_with_retractions = output["summary"]["authors_with_retractions"]
                total_authors = output["summary"]["total_authors_checked"]
                total_retractions = output["summary"]["total_retractions_found"]

                if authors_with_retractions > 0:
                    output["summary"]["message"] = (
                        f"{authors_with_retractions}/{total_authors} author(s) have mentions in Retraction Watch "
                        f"({total_retractions} total mentions found)."
                    )
                    logfire.warn("Authors with retraction history found", job_id=str(job_id), count=authors_with_retractions)
                else:
                    output["summary"]["message"] = f"No mentions in Retraction Watch found for {total_authors} author(s)."

                logger.info(
                    f"[Job {job_id}] Author retraction history check completed: {output['summary']['message']}"
                )

        except Exception as e:
            logger.error(
                f"[Job {job_id}] Error during author retraction history check: {e}",
                exc_info=True
            )
            logfire.error("Author retraction history check failed", exc_info=True, job_id=str(job_id))
            output["error_message"] = f"Check failed: {str(e)}"
            output["summary"]["message"] = "Check failed due to internal error"

        return output


async def check_author_retraction_history(
    db,
    author_data: Dict[str, Any],
    job_id: uuid.UUID,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Check a single author's retraction history.

    Uses exact full name matching (case-insensitive).
    Returns up to 'limit' most recent retractions.

    Args:
        db: Database session
        author_data: Author metadata from GROBID (contains 'name' field)
        job_id: Job UUID for logging
        limit: Maximum number of retractions to return per author (default: 20)

    Returns:
        Dictionary with author info and their retractions
    """
    author_name = author_data.get("name", "").strip()

    result = {
        "author_name": author_name,
        "author_metadata": {
            "forename": author_data.get("forename"),
            "middle_name": author_data.get("middle_name"),
            "surname": author_data.get("surname"),
            "professional_title": author_data.get("professional_title"),
            "affiliations": author_data.get("affiliations", []),
            "is_corresponding": author_data.get("is_corresponding", False),
        },
        "has_retractions": False,
        "retractions": [],
        "error": None,
    }

    if not author_name:
        logger.debug(f"[Job {job_id}] Skipping author with empty name")
        result["error"] = "No author name available"
        return result

    try:
        retractions = await find_retractions_by_author(db, author_name, limit=limit)

        if retractions:
            result["has_retractions"] = True
            result["retractions"] = [format_retraction(r) for r in retractions]
            logger.info(
                f"[Job {job_id}] Found {len(retractions)} mention(s) in Retraction Watch for author: {author_name}"
            )
        else:
            logger.debug(f"[Job {job_id}] No mentions in Retraction Watch found for author: {author_name}")

    except Exception as e:
        logger.error(
            f"[Job {job_id}] Error checking Retraction Watch mentions for author {author_name}: {e}",
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
        "country": retraction.country,
        "institution": retraction.institution,
        "subject": retraction.subject,
        "reason": retraction.reason,
        "authors": [
            {
                "name": author.author_name,
                "position": author.author_position,
            }
            for author in retraction.authors
        ],
    }
