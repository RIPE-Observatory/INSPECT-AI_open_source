import httpx
import asyncio
import json
import logging
import re
import time
from typing import Optional, Dict, Any, List, cast
from bs4 import BeautifulSoup
from pydantic import ValidationError

from core.config import settings
from core.schemas.pubpeer_results import (
    PubPeerComment,
    PubPeerScrapedData,
    PublicationStatus,
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_COST = 0.0
DEFAULT_TIME = 0.0
MAX_CONCURRENT_REQUESTS = 3
API_TIMEOUT_SECONDS = 30.0
SCRAPE_TIMEOUT_SECONDS = 30.0
PUBPEER_USER_AGENT = "INSPECT-AI/1.0 (+https://inspect.ai)"


class PubPeerService:
    """Service for PubPeer API integration and comment scraping"""

    def __init__(self):
        self.api_url = settings.PUBPEER_API_URL
        self.dev_key = settings.PUBPEER_DEV_KEY

    def _log_doi_status(self, doi: str, message: str, level: str = "info") -> None:
        """Centralized DOI logging helper"""
        log_msg = f"DOI {doi}: {message}"
        if level == "warning":
            logger.warning(log_msg)
        elif level == "error":
            logger.error(log_msg)
        else:
            logger.info(log_msg)

    def _build_result(
        self,
        doi: str,
        found: bool,
        api_result: Optional[Dict[str, Any]] = None,
        scraped_data: Optional[PubPeerScrapedData] = None,
        cost: float = DEFAULT_COST,
        time: float = DEFAULT_TIME,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build standardized result dictionary"""
        return {
            "doi": doi,
            "found": found,
            "api_result": api_result,
            "scraped_comments": scraped_data,
            "total_cost": cost,
            "total_time": time,
            "error": error,
        }

    def _extract_pubpeer_url(self, pubpeer_info: Dict[str, Any]) -> Optional[str]:
        """Extract PubPeer URL from API response"""
        feedbacks = pubpeer_info.get("feedbacks", [])
        if not feedbacks or len(feedbacks) == 0:
            return None
        # Get URL from first feedback entry
        first_feedback = feedbacks[0]
        if not isinstance(first_feedback, dict):
            return None
        return first_feedback.get("url")

    def _clean_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _extract_links(self, element: Any) -> List[str]:
        links: List[str] = []
        for anchor in cast(Any, element).find_all("a", href=True):
            href = str(anchor.get("href", "")).strip()
            if href and href not in links:
                links.append(href)
        return links

    def _extract_links_from_text(self, value: str) -> List[str]:
        links = re.findall(r"https?://[^\s)>\"]+", value)
        return list(dict.fromkeys(link.rstrip(".,;") for link in links))

    def _extract_publication_status(self, soup: BeautifulSoup) -> List[PublicationStatus]:
        statuses: List[PublicationStatus] = []
        status_keywords = ("retraction", "correction", "expression of concern", "erratum")
        for anchor in soup.find_all("a", href=True):
            anchor_tag = cast(Any, anchor)
            text = self._clean_text(anchor_tag.get_text(" ", strip=True))
            if not text:
                continue
            if any(keyword in text.lower() for keyword in status_keywords):
                statuses.append(PublicationStatus(status=text, link=str(anchor_tag["href"])))
        return statuses

    def _extract_publication_status_from_component(
        self, soup: BeautifulSoup
    ) -> List[PublicationStatus]:
        publication_page = soup.find("publication-page")
        if not publication_page:
            return []

        raw_publication = cast(Any, publication_page).attrs.get(":data-publication")
        if not raw_publication:
            return []

        try:
            publication = json.loads(str(raw_publication))
        except json.JSONDecodeError:
            return []

        statuses: List[PublicationStatus] = []
        updates = publication.get("updates", [])
        if isinstance(updates, dict):
            updates = updates.get("data", [])

        for update in updates if isinstance(updates, list) else []:
            if not isinstance(update, dict):
                continue
            action = str(update.get("action") or update.get("type") or "").strip()
            content = update.get("content")
            link = ""
            if isinstance(content, str):
                try:
                    content_data = json.loads(content)
                    identifier = content_data.get("identifier", {})
                    if isinstance(identifier, dict) and identifier.get("pubmed"):
                        link = f"https://pubmed.ncbi.nlm.nih.gov/{identifier['pubmed']}/"
                    action = action or str(content_data.get("type") or "")
                except json.JSONDecodeError:
                    link_candidates = self._extract_links_from_text(content)
                    link = link_candidates[0] if link_candidates else ""
            if action:
                statuses.append(PublicationStatus(status=action, link=link))

        return statuses

    def _comments_from_component(self, soup: BeautifulSoup) -> List[PubPeerComment]:
        timeline = soup.find("comment-timeline")
        if not timeline:
            return []

        raw_comments = cast(Any, timeline).attrs.get(":data-comments")
        if not raw_comments:
            return []

        try:
            data = json.loads(str(raw_comments))
        except json.JSONDecodeError:
            logger.warning("Unable to parse PubPeer embedded comment JSON")
            return []

        comments: List[PubPeerComment] = []
        for index, item in enumerate(data if isinstance(data, list) else [], start=1):
            if not isinstance(item, dict):
                continue

            markdown = str(item.get("markdown") or "").strip()
            html_value = str(item.get("html") or "").strip()
            html_text = (
                self._clean_text(BeautifulSoup(html_value, "html.parser").get_text(" ", strip=True))
                if html_value
                else ""
            )
            comment_text = markdown or html_text
            if not comment_text:
                continue

            user_value = item.get("user")
            user = cast(Dict[str, Any], user_value) if isinstance(user_value, dict) else {}
            author = (
                item.get("user_alias")
                or user.get("display_name")
                or user.get("name")
                or "Unknown"
            )
            html_links = (
                self._extract_links(BeautifulSoup(html_value, "html.parser"))
                if html_value
                else []
            )
            text_links = self._extract_links_from_text(markdown)

            reply_to = None
            for key in ("parent_id", "reply_to", "parent_comment_id"):
                if item.get(key) is not None:
                    try:
                        reply_to = int(item[key])
                    except (TypeError, ValueError):
                        reply_to = None
                    break

            comments.append(
                PubPeerComment(
                    id=int(item.get("inner_id") or item.get("id") or index),
                    comment=comment_text,
                    author=str(author),
                    date=str(item.get("accepted_at") or item.get("created_at") or ""),
                    links=list(dict.fromkeys([*html_links, *text_links])),
                    is_reply=reply_to is not None,
                    reply_to=reply_to,
                    is_author_response=bool(item.get("is_from_author")),
                )
            )

        return comments

    def _find_comment_nodes(self, soup: BeautifulSoup) -> List[Any]:
        selectors = [
            "[id^='comment']",
            "[data-comment-id]",
            ".comment",
            ".comment-wrapper",
            ".feedback-comment",
            "article",
        ]
        seen: set[int] = set()
        nodes: List[Any] = []
        for selector in selectors:
            for node in soup.select(selector):
                node_id = id(node)
                text = self._clean_text(cast(Any, node).get_text(" ", strip=True))
                if node_id not in seen and len(text) >= 20:
                    seen.add(node_id)
                    nodes.append(node)
        return nodes

    def _extract_first_text(self, node: Any, selectors: List[str]) -> str:
        for selector in selectors:
            match = cast(Any, node).select_one(selector)
            if match:
                text = self._clean_text(cast(Any, match).get_text(" ", strip=True))
                if text:
                    return text
        return ""

    def _comment_from_node(self, node: Any, fallback_id: int) -> Optional[PubPeerComment]:
        node_tag = cast(Any, node)
        raw_id = (
            node_tag.get("data-comment-id")
            or node_tag.get("data-id")
            or str(node_tag.get("id", ""))
        )
        id_match = re.search(r"\d+", str(raw_id))
        comment_id = int(id_match.group(0)) if id_match else fallback_id

        author = self._extract_first_text(
            node_tag,
            [".author", ".comment-author", ".username", "[itemprop='author']"],
        )
        date = self._extract_first_text(
            node_tag,
            ["time", ".date", ".comment-date", ".timestamp"],
        )
        comment = self._extract_first_text(
            node_tag,
            [".comment-body", ".comment-content", ".content", ".body", "[itemprop='text']"],
        )
        if not comment:
            comment = self._clean_text(node_tag.get_text(" ", strip=True))

        if not comment:
            return None

        classes = " ".join(str(cls).lower() for cls in node_tag.get("class", []))
        is_reply = "reply" in classes or bool(node_tag.find_parent(class_=re.compile("reply", re.I)))
        reply_to = None
        reply_attr = node_tag.get("data-parent-id") or node_tag.get("data-reply-to")
        if reply_attr:
            reply_match = re.search(r"\d+", str(reply_attr))
            reply_to = int(reply_match.group(0)) if reply_match else None

        return PubPeerComment(
            id=comment_id,
            comment=comment,
            author=author or "Unknown",
            date=date or "",
            links=self._extract_links(node_tag),
            is_reply=is_reply,
            reply_to=reply_to,
            is_author_response="author" in classes and "response" in classes,
        )

    async def lookup_doi_and_scrape(self, doi: str) -> Dict[str, Any]:
        """Complete pipeline: API lookup + scraping if URL found"""
        self._log_doi_status(doi, "Starting analysis")

        # Step 1: API lookup
        pubpeer_info = await self._api_lookup(doi)
        if pubpeer_info and pubpeer_info.get("error"):
            error_message = str(pubpeer_info["error"])
            self._log_doi_status(doi, error_message, "error")
            return self._build_result(doi, found=False, error=error_message)

        if not pubpeer_info or not pubpeer_info.get("found"):
            self._log_doi_status(doi, "Not found in PubPeer database")
            return self._build_result(doi, found=False)

        # Step 2: Extract URL
        pubpeer_url = self._extract_pubpeer_url(pubpeer_info)
        if not pubpeer_url:
            self._log_doi_status(doi, "No scraping URL available", "warning")
            return self._build_result(
                doi,
                found=True,
                api_result=pubpeer_info,
                error="No feedbacks or URL found",
            )

        # Step 3: Scrape comments
        try:
            logger.info(f"Scraping: {pubpeer_url}")
            scrape_result = await self._scrape_comments(pubpeer_url)
            self._log_doi_status(doi, "Scraping completed successfully")

            return self._build_result(
                doi,
                found=True,
                api_result=pubpeer_info,
                scraped_data=scrape_result["scraped_data"],
                cost=scrape_result["total_cost"],
                time=scrape_result["total_time"],
            )
        except (ValueError, ValidationError) as e:
            self._log_doi_status(doi, f"Data validation failed: {e}", "error")
            return self._build_result(
                doi,
                found=True,
                api_result=pubpeer_info,
                error=f"Validation failed: {str(e)}",
            )
        except httpx.TimeoutException as e:
            self._log_doi_status(doi, f"Scraping timeout: {e}", "error")
            return self._build_result(
                doi, found=True, api_result=pubpeer_info, error=f"Timeout: {str(e)}"
            )
        except Exception as e:
            self._log_doi_status(doi, f"Scraping failed: {e}", "error")
            return self._build_result(
                doi,
                found=True,
                api_result=pubpeer_info,
                error=f"Scraping failed: {str(e)}",
            )

    async def _api_lookup(self, doi: str) -> Optional[Dict[str, Any]]:
        """Call PubPeer API for DOI lookup"""
        payload = {"dois": [doi]}
        headers = {"Content-Type": "application/json;charset=UTF-8"}

        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{self.api_url}?devkey={self.dev_key}",
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    message = "PubPeer API rate limit exceeded"
                    if retry_after:
                        message = f"{message}; retry after {retry_after} seconds"
                    logger.error(f"{message} for DOI {doi}")
                    return {"found": False, "error": message}
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "good" and data.get("feedbacks"):
                    return {
                        "found": True,
                        "status": data["status"],
                        "feedbacks": data["feedbacks"],
                    }
                else:
                    return {"found": False}

        except httpx.TimeoutException as e:
            logger.error(f"PubPeer API timeout for DOI {doi}: {e}")
            return {"found": False, "error": f"PubPeer API timeout: {e}"}
        except httpx.HTTPStatusError as e:
            logger.error(
                f"PubPeer API HTTP error for DOI {doi}: {e.response.status_code}"
            )
            return {
                "found": False,
                "error": f"PubPeer API HTTP error: {e.response.status_code}",
            }
        except httpx.RequestError as e:
            logger.error(f"PubPeer API request error for DOI {doi}: {e}")
            return {"found": False, "error": f"PubPeer API request error: {e}"}
        except Exception as e:
            logger.error(f"PubPeer API unexpected error for DOI {doi}: {e}")
            return {"found": False, "error": f"PubPeer API unexpected error: {e}"}

    async def _scrape_comments(self, url: str) -> Dict[str, Any]:
        """Scrape comments from a PubPeer URL without LLM-generated summaries."""
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(SCRAPE_TIMEOUT_SECONDS),
                follow_redirects=True,
                headers={"User-Agent": PUBPEER_USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            comments = self._comments_from_component(soup)
            if not comments:
                comments = [
                    comment
                    for index, node in enumerate(self._find_comment_nodes(soup), start=1)
                    if (comment := self._comment_from_node(node, fallback_id=index))
                ]
            validated_data = PubPeerScrapedData(
                publication_status=(
                    self._extract_publication_status_from_component(soup)
                    or self._extract_publication_status(soup)
                ),
                comments=comments,
            )
            total_time = time.perf_counter() - start_time
            logger.info(
                f"Scraped {len(validated_data.comments)} comments - Time: {total_time:.2f}s"
            )

            return {
                "scraped_data": validated_data,
                "total_cost": DEFAULT_COST,
                "total_time": total_time,
            }

        except ValidationError as e:
            logger.error(f"PubPeer data validation failed for {url}: {e}")
            raise ValidationError(f"Data validation failed: {str(e)}")
        except asyncio.TimeoutError as e:
            logger.error(f"PubPeer scraping timeout for {url}: {e}")
            raise ValueError(f"Scraping timeout: {str(e)}")
        except Exception as e:
            logger.error(f"PubPeer scraping failed for {url}: {e}", exc_info=True)
            raise ValueError(f"PubPeer scraping failed: {str(e)}")

    async def batch_lookup_and_scrape(self, dois: List[str]) -> List[Dict[str, Any]]:
        """Process multiple DOIs with controlled concurrency"""
        if not dois:
            return []

        # Limit concurrent requests to avoid overwhelming services
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def process_single_doi(doi: str):
            async with semaphore:
                return await self.lookup_doi_and_scrape(doi)

        logger.info(f"Starting batch processing of {len(dois)} DOIs")
        tasks = [process_single_doi(doi) for doi in dois]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions with specific error types
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_type = type(result).__name__
                self._log_doi_status(
                    dois[i], f"Processing failed ({error_type}): {result}", "error"
                )
                processed_results.append(
                    self._build_result(
                        dois[i],
                        found=False,
                        error=f"Processing failed ({error_type}): {str(result)}",
                    )
                )
            else:
                processed_results.append(result)

        logger.info(f"Batch processing completed for {len(dois)} DOIs")
        return processed_results
