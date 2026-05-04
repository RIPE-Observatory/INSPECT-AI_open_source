from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class PubPeerAPIResult(BaseModel):
    """PubPeer API response structure"""

    found: bool
    status: Optional[str]
    feedbacks: Optional[List[Dict[str, Any]]]


class PublicationStatus(BaseModel):
    """Publication status notice (e.g., retraction, correction)"""

    status: str
    link: str


class PubPeerComment(BaseModel):
    """Individual PubPeer comment with rich metadata"""

    id: int
    comment: str
    author: str
    date: str
    links: List[str] = []
    is_reply: bool = False
    reply_to: Optional[int] = None
    is_author_response: bool = False


class PubPeerScrapedData(BaseModel):
    """Structured scraped data from PubPeer page"""

    publication_status: List[PublicationStatus] = []
    comments: List[PubPeerComment] = []


class PubPeerLookupResult(BaseModel):
    """Complete result for a single DOI"""

    doi: str
    found: bool
    api_result: Optional[PubPeerAPIResult]
    scraped_comments: Optional[PubPeerScrapedData]
    total_cost: float = 0.0
    total_time: float = 0.0
    error: Optional[str]


class PubPeerSignalAnalysisOutput(BaseModel):
    """Structured output from the PubPeer signal analysis."""

    check_name: str = "pubpeer_signal_analysis"
    status: str  # COMPLETED_SUCCESS, COMPLETED_NOT_FOUND, FAILED
    main_paper_result: Optional[PubPeerLookupResult]
    reference_results: List[PubPeerLookupResult]

    summary: Dict[str, Any] = {}
    processing_info: Dict[str, Any] = {}

    error_message: Optional[str] = None
