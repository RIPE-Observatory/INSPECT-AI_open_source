from typing import Optional, List
from pydantic import BaseModel, Field


class RetractionWatchRecord(BaseModel):
    """Direct mapping of Retraction Watch CSV fields - no interpretation"""

    record_id: Optional[int] = Field(None, description="Record ID from CSV")
    title: Optional[str] = Field(None, description="Title from CSV")
    subject: Optional[str] = Field(None, description="Subject from CSV")
    institution: Optional[str] = Field(None, description="Institution from CSV")
    journal: Optional[str] = Field(None, description="Journal from CSV")
    publisher: Optional[str] = Field(None, description="Publisher from CSV")
    country: Optional[str] = Field(None, description="Country from CSV")
    author: Optional[str] = Field(None, description="Author from CSV")
    urls: Optional[str] = Field(None, description="URLS from CSV (raw string)")
    article_type: Optional[str] = Field(None, description="ArticleType from CSV")
    retraction_date: Optional[str] = Field(None, description="RetractionDate from CSV")
    retraction_doi: Optional[str] = Field(None, description="RetractionDOI from CSV")
    retraction_pubmed_id: Optional[int] = Field(
        None, description="RetractionPubMedID from CSV"
    )
    original_paper_date: Optional[str] = Field(
        None, description="OriginalPaperDate from CSV"
    )
    original_paper_doi: Optional[str] = Field(
        None, description="OriginalPaperDOI from CSV"
    )
    original_paper_pubmed_id: Optional[int] = Field(
        None, description="OriginalPaperPubMedID from CSV"
    )
    retraction_nature: Optional[str] = Field(
        None, description="RetractionNature from CSV"
    )
    reason: Optional[str] = Field(None, description="Reason from CSV")
    paywalled: Optional[str] = Field(None, description="Paywalled from CSV")
    notes: Optional[str] = Field(None, description="Notes from CSV")


class RetractionLookupResult(BaseModel):
    """Result of looking up a single paper"""

    searched_doi: Optional[str] = Field(None, description="DOI that was searched")
    searched_title: Optional[str] = Field(None, description="Title that was searched")
    found_in_database: bool = Field(False, description="Whether found in RW database")
    lookup_method: Optional[str] = Field(
        None, description="'doi' or 'title' or 'not_found'"
    )
    retraction_records: List[RetractionWatchRecord] = Field(
        default_factory=list, description="All matching Retraction Watch records"
    )
    error_message: Optional[str] = Field(None, description="Error if lookup failed")


class RetractionWatchMonitorOutput(BaseModel):
    """Structured output emitted by the retraction watch monitor."""

    check_name: str = Field(
        default="retraction_watch_monitor", description="Name of the check"
    )
    csv_timestamp: Optional[str] = Field(
        None, description="When Retraction Watch CSV was last modified"
    )

    main_paper_result: Optional[RetractionLookupResult] = Field(
        None, description="Lookup result for the main paper"
    )
    reference_results: List[RetractionLookupResult] = Field(
        default_factory=list, description="Lookup results for reference papers"
    )

    summary_message: Optional[str] = Field(
        None, description="Simple summary of what was found"
    )
    error_message: Optional[str] = Field(
        None, description="Overall error if check failed"
    )
