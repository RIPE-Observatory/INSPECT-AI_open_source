import logging
import os
import csv
from typing import List, Optional, Dict
from datetime import datetime

from core.config import get_settings
from core.schemas.retraction_watch_results import (
    RetractionWatchRecord,
    RetractionLookupResult,
)


def _normalize_retraction_date(raw: Optional[str], context: str) -> Optional[str]:
    """Normalize Retraction Watch dates to DD-MM-YYYY when possible."""

    if not raw or not isinstance(raw, str):
        return raw

    candidate = raw.strip()
    if not candidate:
        return ""

    # Strip time components or additional annotations after whitespace or 'T'
    candidate = candidate.replace("T", " ")
    candidate = candidate.split()[0]

    # Replace dot separators with hyphen for easier parsing (e.g., 2021.08.06)
    candidate = candidate.replace(".", "-")

    from datetime import datetime

    formats_to_try = [
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
    ]

    for fmt in formats_to_try:
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue

    # Retry with the cleaned candidate (after stripping time/dots)
    candidate_formats = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
    ]
    for fmt in candidate_formats:
        try:
            dt = datetime.strptime(candidate, fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue

    logger.warning(
        "Could not normalize Retraction Watch date '%s' for %s; keeping original.",
        raw,
        context,
    )
    return raw


def _optional_int(raw: Optional[str]) -> Optional[int]:
    if raw is None:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    try:
        return int(candidate)
    except ValueError:
        logger.warning("Could not parse integer field value '%s'; using null.", raw)
        return None


logger = logging.getLogger(__name__)
SETTINGS = get_settings()

# Column Name Constants from CSV - All 20 fields
COL_RECORD_ID = "Record ID"
COL_TITLE = "Title"
COL_SUBJECT = "Subject"
COL_INSTITUTION = "Institution"
COL_JOURNAL = "Journal"
COL_PUBLISHER = "Publisher"
COL_COUNTRY = "Country"
COL_AUTHOR = "Author"
COL_URLS = "URLS"
COL_ARTICLE_TYPE = "ArticleType"
COL_RETRACTION_DATE = "RetractionDate"
COL_RETRACTION_DOI = "RetractionDOI"
COL_RETRACTION_PUBMED_ID = "RetractionPubMedID"
COL_ORIGINAL_PAPER_DATE = "OriginalPaperDate"
COL_ORIGINAL_PAPER_DOI = "OriginalPaperDOI"  # Primary key for lookup
COL_ORIGINAL_PAPER_PUBMED_ID = "OriginalPaperPubMedID"
COL_RETRACTION_NATURE = "RetractionNature"
COL_REASON = "Reason"
COL_PAYWALLED = "Paywalled"
COL_NOTES = "Notes"

INDEX_COLUMN = COL_ORIGINAL_PAPER_DOI


class RetractionWatchService:
    _records_by_doi: Optional[Dict[str, List[Dict[str, str]]]] = None
    _records: Optional[List[Dict[str, str]]] = None
    _csv_path: str = os.environ.get(
        "RETRACTION_WATCH_CSV_PATH", SETTINGS.RETRACTION_WATCH_CSV_PATH
    )
    _last_loaded_timestamp: Optional[datetime] = None

    @classmethod
    def _load_data(cls) -> bool:
        """
        Loads or reloads the Retraction Watch CSV data.
        Indexes rows by 'OriginalPaperDOI' for efficient lookup.
        Only reloads if the file has been modified since last load or not loaded yet.
        """
        try:
            if not os.path.exists(cls._csv_path):
                logger.error(f"Retraction Watch CSV file not found at: {cls._csv_path}")
                cls._records = None
                cls._records_by_doi = None
                return False

            current_file_mod_time = datetime.fromtimestamp(
                os.path.getmtime(cls._csv_path)
            )

            if (
                cls._records is not None
                and cls._records_by_doi is not None
                and cls._last_loaded_timestamp == current_file_mod_time
            ):
                logger.debug("Retraction Watch data is already loaded and up-to-date.")
                return True

            logger.info(f"Loading Retraction Watch data from: {cls._csv_path}")

            with open(cls._csv_path, newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file)
                if not reader.fieldnames:
                    logger.error(f"Retraction Watch CSV file is empty: {cls._csv_path}")
                    cls._records = None
                    cls._records_by_doi = None
                    return False
                if INDEX_COLUMN not in reader.fieldnames:
                    logger.error(f"'{INDEX_COLUMN}' not found in CSV. Cannot set index.")
                    cls._records = None
                    cls._records_by_doi = None
                    return False

                records = [{key: value or "" for key, value in row.items()} for row in reader]

            records_by_doi: Dict[str, List[Dict[str, str]]] = {}
            for row in records:
                normalized_doi = str(row.get(INDEX_COLUMN, "")).lower().strip()
                if normalized_doi:
                    records_by_doi.setdefault(normalized_doi, []).append(row)

            cls._records = records
            cls._records_by_doi = records_by_doi
            cls._last_loaded_timestamp = current_file_mod_time
            logger.info(
                "Successfully loaded and indexed Retraction Watch data. Rows: %s",
                len(records),
            )
            return True
        except Exception as e:
            logger.error(f"Error loading Retraction Watch CSV: {e}", exc_info=True)
            cls._records = None
            cls._records_by_doi = None
        return False

    @classmethod
    def _get_records(cls) -> Optional[List[Dict[str, str]]]:
        """Ensures data is loaded and returns records."""
        if cls._records is None or cls._records_by_doi is None or not cls._is_data_current():
            cls._load_data()
        return cls._records

    @classmethod
    def _is_data_current(cls) -> bool:
        """Checks if the loaded data is current with the CSV file on disk."""
        if (
            cls._records is None
            or cls._records_by_doi is None
            or cls._last_loaded_timestamp is None
        ):
            return False
        try:
            if not os.path.exists(cls._csv_path):
                return False  # File removed after loading
            current_file_mod_time = datetime.fromtimestamp(
                os.path.getmtime(cls._csv_path)
            )
            return cls._last_loaded_timestamp == current_file_mod_time
        except Exception:
            return False

    @classmethod
    def get_csv_file_timestamp_str(cls) -> Optional[str]:
        """
        Returns the last modification timestamp of the Retraction Watch CSV file as an ISO 8601 string.
        Returns None if the file doesn't exist or timestamp cannot be read.
        """
        # Ensure data is loaded to potentially update _last_loaded_timestamp if file changed
        cls._get_records()
        if cls._last_loaded_timestamp:
            return cls._last_loaded_timestamp.isoformat()

        # Fallback if data wasn't loaded but file exists
        try:
            if os.path.exists(cls._csv_path):
                return datetime.fromtimestamp(
                    os.path.getmtime(cls._csv_path)
                ).isoformat()
        except Exception as e:
            logger.warning(f"Could not get timestamp for {cls._csv_path}: {e}")
        return None

    @classmethod
    def _lookup_single_doi_in_records(cls, doi: str) -> Optional[List[Dict[str, str]]]:
        """Looks up all rows matching a normalized DOI."""
        records = cls._get_records()
        if records is None or cls._records_by_doi is None:
            logger.error(f"Retraction Watch records not available for DOI lookup: {doi}")
            return None
        try:
            return cls._records_by_doi.get(doi) or None
        except Exception as e:
            logger.error(
                f"Error looking up DOI {doi} in Retraction Watch records: {e}",
                exc_info=True,
            )
            return None

    @classmethod
    def _lookup_by_title_in_records(cls, title: str) -> Optional[List[Dict[str, str]]]:
        """Looks up all rows matching a title."""
        records = cls._get_records()
        if records is None:
            logger.error(f"Retraction Watch records not available for title lookup: {title}")
            return None

        try:
            normalized_title = title.lower().strip()
            exact_matches = [
                row
                for row in records
                if str(row.get(COL_TITLE, "")).lower().strip() == normalized_title
            ]
            if exact_matches:
                return exact_matches

            fuzzy_matches = [
                row
                for row in records
                if normalized_title in str(row.get(COL_TITLE, "")).lower()
            ]
            if fuzzy_matches:
                logger.info(f"Found fuzzy title matches for '{title[:50]}...'")
                return fuzzy_matches

            return None  # Title not found

        except Exception as e:
            logger.error(
                f"Error looking up title '{title[:50]}...' in Retraction Watch records: {e}",
                exc_info=True,
            )
            return None

    @classmethod
    def _row_to_record(cls, row: Dict[str, str]) -> RetractionWatchRecord:
        """Convert CSV row to RetractionWatchRecord - direct field mapping."""
        record = RetractionWatchRecord(
            record_id=_optional_int(row.get(COL_RECORD_ID)),
            title=row.get(COL_TITLE),
            subject=row.get(COL_SUBJECT),
            institution=row.get(COL_INSTITUTION),
            journal=row.get(COL_JOURNAL),
            publisher=row.get(COL_PUBLISHER),
            country=row.get(COL_COUNTRY),
            author=row.get(COL_AUTHOR),
            urls=row.get(COL_URLS),  # Raw string, no parsing
            article_type=row.get(COL_ARTICLE_TYPE),
            retraction_date=row.get(COL_RETRACTION_DATE),
            retraction_doi=row.get(COL_RETRACTION_DOI),
            retraction_pubmed_id=_optional_int(row.get(COL_RETRACTION_PUBMED_ID)),
            original_paper_date=row.get(COL_ORIGINAL_PAPER_DATE),
            original_paper_doi=row.get(COL_ORIGINAL_PAPER_DOI),
            original_paper_pubmed_id=_optional_int(row.get(COL_ORIGINAL_PAPER_PUBMED_ID)),
            retraction_nature=row.get(COL_RETRACTION_NATURE),
            reason=row.get(COL_REASON),
            paywalled=row.get(COL_PAYWALLED),
            notes=row.get(COL_NOTES),
        )

        context = record.title or record.original_paper_doi or "unknown"
        record.retraction_date = _normalize_retraction_date(
            record.retraction_date,
            context,
        )

        return record

    @classmethod
    def get_retraction_data_for_papers(
        cls, papers: List[Dict[str, Optional[str]]]
    ) -> List[RetractionLookupResult]:
        """
        Looks up papers in the Retraction Watch data using DOI first, then title as fallback.
        Returns raw CSV data without interpretation.

        Args:
            papers: List of dicts with 'doi' and 'title' keys

        Returns:
            List of RetractionLookupResult objects
        """
        results: List[RetractionLookupResult] = []

        for paper in papers:
            doi = paper.get("doi")
            title = paper.get("title")

            # Try DOI lookup first if available
            if doi and isinstance(doi, str) and doi.strip():
                normalized_doi = doi.lower().strip()
                row_data = cls._lookup_single_doi_in_records(normalized_doi)

                if row_data is not None:
                    if row_data:
                        records = [cls._row_to_record(row) for row in row_data]
                        results.append(
                            RetractionLookupResult(
                                searched_doi=doi,
                                searched_title=title,
                                found_in_database=True,
                                lookup_method="doi",
                                retraction_records=records,
                                error_message=None,
                            )
                        )
                        continue  # Skip title lookup since we found by DOI

            # Try title lookup if DOI lookup failed or no DOI provided
            if title and isinstance(title, str) and title.strip():
                row_data = cls._lookup_by_title_in_records(title)

                if row_data is not None:
                    if row_data:
                        records = [cls._row_to_record(row) for row in row_data]
                        results.append(
                            RetractionLookupResult(
                                searched_doi=doi,
                                searched_title=title,
                                found_in_database=True,
                                lookup_method="title",
                                retraction_records=records,
                                error_message=None,
                            )
                        )
                        continue

            # Not found by DOI or title
            identifier = (
                doi
                if doi
                else (f"Title: {title[:50]}..." if title else "No identifier")
            )
            results.append(
                RetractionLookupResult(
                    searched_doi=doi,
                    searched_title=title,
                    found_in_database=False,
                    lookup_method="not_found",
                    error_message=f"Not found in Retraction Watch database: {identifier}",
                )
            )

        return results
