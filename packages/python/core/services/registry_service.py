import logging
import asyncio
import aiohttp
from aiohttp import DummyCookieJar, ClientTimeout
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, cast
import httpx
from bs4 import BeautifulSoup
import re
import logfire

from core.schemas.registry_outputs import RegistryLookupDetail

logger = logging.getLogger(__name__)

# ClinicalTrials.gov API V2 base URL
CTG_API_BASE_URL = "https://clinicaltrials.gov/api/v2/"
WHO_ICTRP_BASE_URL = "https://trialsearch.who.int/Trial2.aspx"

# Rate limiting settings for CTG API calls from this service
MIN_CTG_REQUEST_INTERVAL = 1.0  # Minimum time between requests to CTG API in seconds

# WHO ICTRP scraping configuration
WHO_TIMEOUT_SECONDS = 30.0
WHO_MAX_RETRIES = 3
WHO_BACKOFF_SECONDS = 2.0
WHO_USER_AGENT = "INSPECT-AI/1.0 (+https://inspect.ai)"


class RegistryService:
    def __init__(self):
        self._ctg_api_lock = asyncio.Lock()
        self._last_ctg_api_request_time = 0.0

    async def _rate_limited_ctg_request(self):
        async with self._ctg_api_lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last_request = current_time - self._last_ctg_api_request_time
            if time_since_last_request < MIN_CTG_REQUEST_INTERVAL:
                sleep_duration = MIN_CTG_REQUEST_INTERVAL - time_since_last_request
                logger.debug(f"CTG API Rate limit: Sleeping for {sleep_duration:.2f}s")
                await asyncio.sleep(sleep_duration)
            self._last_ctg_api_request_time = asyncio.get_event_loop().time()

    async def _fetch_from_ctg_api(
        self, trial_id: str, fields: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        with logfire.span("registry.ctg_api_fetch", trial_id=trial_id):
            await self._rate_limited_ctg_request()

            url = f"{CTG_API_BASE_URL}studies/{trial_id}"
            if fields:
                url += f"?fields={fields}"
            logger.info(f"Fetching from ClinicalTrials.gov API (using aiohttp): {url}")
            logfire.info("Fetching from ClinicalTrials.gov API", trial_id=trial_id, url=url)

            request_headers = {"Accept": "application/json", "Cookie": ""}

            try:
                async with aiohttp.ClientSession(
                    cookie_jar=DummyCookieJar(), skip_auto_headers=["Cookie"]
                ) as session:
                    async with session.get(
                        url, headers=request_headers, timeout=ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            logfire.info("CTG API fetch successful", trial_id=trial_id)
                            return await response.json(), None
                        elif response.status == 404:
                            logger.warning(
                                f"Trial ID {trial_id} not found on ClinicalTrials.gov (HTTP 404). URL: {url}"
                            )
                            logfire.warn("Trial not found on ClinicalTrials.gov (404)", trial_id=trial_id)
                            return (
                                None,
                                f"Trial ID {trial_id} not found on ClinicalTrials.gov (HTTP 404).",
                            )
                        error_text = await response.text()
                        logger.error(
                            f"HTTP error {response.status} fetching {trial_id} from CTG: {error_text}. URL: {url}"
                        )
                        logfire.error("CTG API HTTP error", status_code=response.status, trial_id=trial_id)
                        response.raise_for_status()
                        return (
                            None,
                            f"HTTP error {response.status} while fetching {trial_id} from ClinicalTrials.gov.",
                        )
            except aiohttp.ClientResponseError as e_resp:
                logger.error(
                    f"aiohttp.ClientResponseError (HTTP {e_resp.status}) fetching {trial_id} from CTG: {e_resp.message}. URL: {url}"
                )
                logfire.error("CTG API response error", exc_info=True, trial_id=trial_id)
                return (
                    None,
                    f"HTTP error {e_resp.status} while fetching {trial_id} from ClinicalTrials.gov.",
                )
            except aiohttp.ClientError as e_client:
                logger.error(
                    f"aiohttp.ClientError fetching {trial_id} from CTG: {e_client}. URL: {url}"
                )
                logfire.error("CTG API client error", exc_info=True, trial_id=trial_id)
                return (
                    None,
                    f"Request error while fetching {trial_id} from ClinicalTrials.gov: {e_client}",
                )
            except asyncio.TimeoutError:
                logger.error(f"Request timed out fetching {trial_id} from CTG. URL: {url}")
                logfire.error("CTG API timeout", trial_id=trial_id)
                return (
                    None,
                    f"Request timed out while fetching {trial_id} from ClinicalTrials.gov.",
                )
            except Exception as e_general:
                logger.exception(
                    f"Unexpected error fetching {trial_id} from CTG with aiohttp: {e_general}. URL: {url}"
                )
                logfire.error("CTG API unexpected error", exc_info=True, trial_id=trial_id)
                # Surface underlying error text to help callers detect 429 / rate limit, etc.
                return (
                    None,
                    str(e_general),
                )

    async def _fetch_ctg_qc_date(
        self, trial_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        normalized_nct_id = (
            trial_id.replace(" ", "").replace("-", "").replace("_", "").upper()
        )
        if not (
            normalized_nct_id.startswith("NCT")
            and len(normalized_nct_id) == 11
            and normalized_nct_id[3:].isdigit()
        ):
            logger.warning(
                f"Invalid NCT ID format for QC date fetch: {trial_id} (Normalized: {normalized_nct_id})"
            )
            return None, None

        raw_data, error_msg = await self._fetch_from_ctg_api(
            normalized_nct_id,
            fields="protocolSection.statusModule.studyFirstSubmitQcDate",
        )
        if error_msg or not raw_data:
            logger.warning(
                f"Could not fetch QC date for {normalized_nct_id}: {error_msg or 'No data'}"
            )
            return None, error_msg or "No data"

        qc_date_str: Optional[str] = None
        try:
            qc_date_str = (
                raw_data.get("protocolSection", {})
                .get("statusModule", {})
                .get("studyFirstSubmitQcDate")
            )
            if qc_date_str:
                dt_object = datetime.strptime(qc_date_str, "%Y-%m-%d")
                formatted_date = dt_object.strftime("%d-%m-%Y")
                logger.info(
                    f"Successfully fetched and formatted QC date for {normalized_nct_id}: {formatted_date}"
                )
                return formatted_date, None
            else:
                logger.warning(
                    f"studyFirstSubmitQcDate field not found in QC date response for {normalized_nct_id}."
                )
                return None, "studyFirstSubmitQcDate not found"
        except ValueError as e_parse:
            logger.error(
                f"Error parsing QC submission date '{qc_date_str}' for {normalized_nct_id}: {e_parse}"
            )
            return None, f"Parse error: {e_parse}"
        except Exception as e_qc:
            logger.error(
                f"Unexpected error processing QC date for {normalized_nct_id}: {e_qc}",
                exc_info=True,
            )
            return None, f"Unexpected error: {e_qc}"

    async def _fetch_from_who_ictrp(self, trial_id: str) -> Optional[str]:
        """
        Fetches the registration date for a given Trial ID from the WHO ICTRP portal.
        """
        if not trial_id:
            logger.error("(WHO ICTRP) Trial ID cannot be empty.")
            return None

        search_url = f"{WHO_ICTRP_BASE_URL}?TrialID={trial_id}"
        logger.info(
            f"(WHO ICTRP) Fetching data for Trial ID: {trial_id} from {search_url}"
        )
        logfire.info("Scraping WHO ICTRP", trial_id=trial_id)

        headers = {"User-Agent": WHO_USER_AGENT}
        timeout = httpx.Timeout(WHO_TIMEOUT_SECONDS)

        for attempt in range(1, WHO_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout, follow_redirects=True, headers=headers
                ) as client:
                    response = await client.get(search_url)
                    response.raise_for_status()
                    page_content = response.text
                    logger.info(
                        f"(WHO ICTRP) Successfully fetched page for {trial_id}. Status: {response.status_code} (attempt {attempt})"
                    )

                soup = BeautifulSoup(page_content, "html.parser")
                date_pattern_dmY = r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}$"
                date_pattern_Ymd = r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$"

                date_span_by_id = soup.find(
                    "span", id=re.compile(r"_Date_registrationLabel$")
                )
                if date_span_by_id:
                    registration_date = date_span_by_id.get_text(strip=True)
                    if re.match(date_pattern_dmY, registration_date) or re.match(
                        date_pattern_Ymd, registration_date
                    ):
                        logger.info(
                            f"(WHO ICTRP ID Search) Extracted '{registration_date}' for {trial_id}."
                        )
                        logfire.info("WHO ICTRP scrape successful", trial_id=trial_id, date=registration_date)
                        return registration_date
                    else:
                        logger.warning(
                            f"(WHO ICTRP ID Search) Found span, but text '{registration_date}' format unexpected for {trial_id}."
                        )
                else:
                    logger.info(
                        f"(WHO ICTRP ID Search) Span with ID ending '_Date_registrationLabel' not found for {trial_id}."
                    )

                label_td = None
                for td in soup.find_all("td"):
                    td_tag = cast(Any, td)
                    td_text_stripped = td_tag.get_text(strip=True)
                    if td_text_stripped == "Date of registration:":
                        label_td = td_tag
                        break
                    strong_tag = td_tag.find("strong")
                    if (
                        strong_tag
                        and cast(Any, strong_tag).get_text(strip=True)
                        == "Date of registration:"
                    ):
                        label_td = td_tag
                        break

                if label_td:
                    logger.info(
                        f"(WHO ICTRP Text Search) Found label_td for 'Date of registration:' for {trial_id}."
                    )
                    parent_tr = cast(Any, label_td).find_parent("tr")
                    if parent_tr:
                        all_tds_in_row = cast(Any, parent_tr).find_all(
                            "td", recursive=False
                        )
                        try:
                            label_td_index = all_tds_in_row.index(label_td)
                            if label_td_index + 1 < len(all_tds_in_row):
                                value_td = all_tds_in_row[label_td_index + 1]
                                registration_date_text = cast(Any, value_td).get_text(
                                    strip=True
                                )

                                span_in_value_td = cast(Any, value_td).find(
                                    "span",
                                    attrs={
                                        "id": re.compile(r"_Date_registrationLabel$")
                                    },
                                )
                                if span_in_value_td:
                                    date_from_span = cast(
                                        Any, span_in_value_td
                                    ).get_text(strip=True)
                                    if re.match(
                                        date_pattern_dmY, date_from_span
                                    ) or re.match(date_pattern_Ymd, date_from_span):
                                        logger.info(
                                            f"(WHO ICTRP Text Search - Span in Value) Extracted '{date_from_span}' for {trial_id}."
                                        )
                                        return date_from_span
                                    else:
                                        logger.warning(
                                            f"(WHO ICTRP Text Search) Span in value cell, text '{date_from_span}' unexpected for {trial_id}."
                                        )

                                if re.match(
                                    date_pattern_dmY, registration_date_text
                                ) or re.match(date_pattern_Ymd, registration_date_text):
                                    logger.info(
                                        f"(WHO ICTRP Text Search - Direct Value) Extracted '{registration_date_text}' for {trial_id}."
                                    )
                                    return registration_date_text
                                else:
                                    logger.warning(
                                        f"(WHO ICTRP Text Search) Text '{registration_date_text}' from value cell unexpected for {trial_id}."
                                    )
                            else:
                                logger.warning(
                                    f"(WHO ICTRP Text Search) Label td was last cell in row for {trial_id}."
                                )
                        except ValueError:
                            logger.warning(
                                f"(WHO ICTRP Text Search) Label td not direct child of parent TR's TDs for {trial_id}."
                            )
                    else:
                        logger.warning(
                            f"(WHO ICTRP Text Search) Label td has no parent 'tr' for {trial_id}."
                        )
                else:
                    logger.warning(
                        f"(WHO ICTRP Text Search) Could not find 'Date of registration:' label td for {trial_id}."
                    )

                logger.error(
                    f"(WHO ICTRP) Failed to extract valid registration date for {trial_id} after parsing."
                )
                return None

            except httpx.TimeoutException as e_timeout:
                logger.warning(
                    f"(WHO ICTRP) Timeout fetching {trial_id} on attempt {attempt}: {e_timeout}"
                )
            except httpx.HTTPStatusError as e_http:
                logger.error(
                    f"(WHO ICTRP) HTTP error {e_http.response.status_code} for {trial_id}: {e_http.response.text[:200]}"
                )
                return None
            except httpx.RequestError as e_req:
                logger.warning(
                    f"(WHO ICTRP) Request error for {trial_id} on attempt {attempt}: {e_req}"
                )
            except Exception as e_gen:
                logger.error(
                    f"(WHO ICTRP) Unexpected error for {trial_id} on attempt {attempt}: {e_gen}",
                    exc_info=True,
                )
                return None

            if attempt < WHO_MAX_RETRIES:
                backoff = WHO_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.info(
                    f"(WHO ICTRP) Retrying fetch for {trial_id} in {backoff:.1f}s (attempt {attempt + 1}/{WHO_MAX_RETRIES})"
                )
                await asyncio.sleep(backoff)

        logger.error(
            f"(WHO ICTRP) Exhausted retries fetching registration date for {trial_id}."
        )
        logfire.error("WHO ICTRP scrape failed after retries", trial_id=trial_id, max_retries=WHO_MAX_RETRIES)
        return None

    async def lookup_trial_in_registry(
        self, trial_id: str, registry_type: str
    ) -> RegistryLookupDetail:
        """
        Looks up a trial ID in the specified registry.
        - For ClinicalTrials.gov (NCT IDs), uses the CTG API.
        - For other registries, attempts to scrape data from WHO ICTRP.
        """
        logger.info(
            f"Lookup initiated for Trial ID: {trial_id}, Registry Type: {registry_type}"
        )
        logfire.info("Registry lookup started", trial_id=trial_id, registry_type=registry_type)

        if not trial_id:
            logger.warning("Lookup attempt with empty Trial ID.")
            logfire.warn("Empty trial ID provided to registry lookup")
            return RegistryLookupDetail(
                trial_id_original=trial_id,
                registry_name=registry_type,
                lookup_successful=False,
                error_message="Trial ID cannot be empty.",
            )

        normalized_registry_type = (
            registry_type.lower().replace(" ", "").replace(".", "")
        )
        is_nct_type = (
            "clinicaltrialsgov" in normalized_registry_type
            or "nct" == normalized_registry_type
        )
        is_nct_id_format = trial_id.lower().startswith("nct")

        if is_nct_type or is_nct_id_format:
            logger.info(f"Routing to ClinicalTrials.gov API for {trial_id}")
            qc_date, fetch_error_msg = None, None
            try:
                qc_date, fetch_error_msg = await self._fetch_ctg_qc_date(trial_id)
                if not qc_date and not fetch_error_msg:
                    fetch_error_msg = f"StudyFirstSubmitQCDate not found or could not be retrieved for {trial_id} via CTG API."
            except Exception as e_qc_fetch:
                logger.error(
                    f"Error during _fetch_ctg_qc_date call for {trial_id}: {e_qc_fetch}",
                    exc_info=True,
                )
                fetch_error_msg = f"Failed to fetch StudyFirstSubmitQCDate due to an exception: {str(e_qc_fetch)}"

            normalized_nct_id_for_url = (
                trial_id.replace(" ", "").replace("-", "").replace("_", "").upper()
            )

            return RegistryLookupDetail(
                trial_id_original=trial_id,
                registry_name="ClinicalTrials.gov",
                study_first_submit_qc_date=qc_date if qc_date else "",
                url=f"https://clinicaltrials.gov/study/{normalized_nct_id_for_url}"
                if normalized_nct_id_for_url.startswith("NCT")
                else f"https://clinicaltrials.gov/search?id={trial_id}",
                lookup_successful=bool(qc_date),
                error_message=fetch_error_msg
                if not qc_date and fetch_error_msg
                else None,
            )
        else:
            logger.info(
                f"Routing to WHO ICTRP scraper for {trial_id} (Registry: {registry_type})"
            )
            registration_date = await self._fetch_from_who_ictrp(trial_id)
            if registration_date:
                return RegistryLookupDetail(
                    trial_id_original=trial_id,
                    registry_name=f"{registry_type} (via WHO ICTRP)",
                    study_first_submit_qc_date=registration_date,
                    url=f"{WHO_ICTRP_BASE_URL}?TrialID={trial_id}",
                    lookup_successful=True,
                    error_message="",
                )
            else:
                return RegistryLookupDetail(
                    trial_id_original=trial_id,
                    registry_name=f"{registry_type} (via WHO ICTRP)",
                    study_first_submit_qc_date="",
                    url=f"{WHO_ICTRP_BASE_URL}?TrialID={trial_id}",
                    lookup_successful=False,
                    error_message=f"Failed to extract registration date from WHO ICTRP for {trial_id}.",
                )
