import logging
import os
import sys
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
import time
import requests
import xml.etree.ElementTree as ET
import shutil

from selenium import webdriver # type: ignore
from selenium.webdriver.chrome.service import Service as ChromeService # type: ignore
from webdriver_manager.chrome import ChromeDriverManager # type: ignore
from selenium.webdriver.chrome.options import Options as ChromeOptions # type: ignore
from selenium.common.exceptions import ( # type: ignore
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
)
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Try importing app modules, add to path if needed
try:
    from ...packages.python.core.config import settings
    from ...packages.python.core.schemas.enums import JobSourceEnum
except ImportError:
    # Add project root to path as fallback for direct script execution
    PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    sys.path.insert(0, PROJECT_ROOT)
    from ...packages.python.core.config import settings
    from ...packages.python.core.schemas.enums import JobSourceEnum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# NCBI E-utils Configuration
# TODO: move API_KEY, EMAIL, TOOL_NAME to settings.
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "goutham.indukuri@abdn.ac.uk")
NCBI_TOOL_NAME = os.getenv("NCBI_TOOL_NAME", "InspectAI_Automated_Fetcher_v2.2024")
NCBI_SEARCH_TERM = os.getenv("NCBI_SEARCH_TERM", "randomized controlled trial[pt]")
NCBI_MAX_RESULTS = int(os.getenv("NCBI_MAX_RESULTS", 500))
NCBI_REQUEST_TIMEOUT = int(os.getenv("NCBI_REQUEST_TIMEOUT", 30))  # seconds
SELENIUM_DOWNLOAD_TIMEOUT = int(
    os.getenv("SELENIUM_DOWNLOAD_TIMEOUT", 120)
)  # seconds for individual PDF download
DOWNLOAD_LIMIT_PER_RUN = int(os.getenv("DOWNLOAD_LIMIT_PER_RUN", 500))
SUBMISSION_LIMIT_PER_RUN = int(os.getenv("SUBMISSION_LIMIT_PER_RUN", 500))

BASE_URL_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
BASE_URL_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


# PDF Download Configuration
DOWNLOAD_FOLDER_BASE = os.path.join(os.path.dirname(__file__), "downloaded_pdfs")
SELENIUM_TEMP_DOWNLOAD_DIR = os.path.join(
    DOWNLOAD_FOLDER_BASE, "temp_selenium_downloads"
)

ARTICLE_URL_TEMPLATE = "https://www.ncbi.nlm.nih.gov/pmc/articles/{}/"

# State Management (SQLite)
DB_PATH = os.path.join(os.path.dirname(__file__), "fetcher_state.db")
# Define a batch size for EFetch requests
EFETCH_BATCH_SIZE = 50


class ArticleStatus:
    PENDING_DOWNLOAD = "PENDING_DOWNLOAD"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    DOWNLOADED = "DOWNLOADED"
    SUBMISSION_FAILED = "SUBMISSION_FAILED"
    SUBMITTED_TO_API = "SUBMITTED_TO_API"
    PROCESSING_ERROR = "PROCESSING_ERROR"


def init_state_db():
    """Initializes the SQLite database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # 1. Ensure the table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_pmc_articles (
                    pmc_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_attempted TIMESTAMP,
                    submitted_job_id TEXT
                    -- filepath column will be added next if it doesn't exist
                )
            """)
            conn.commit()

            # 2. Check if 'filepath' column exists
            cursor.execute("PRAGMA table_info(processed_pmc_articles)")
            columns = [column[1] for column in cursor.fetchall()]
            if "filepath" not in columns:
                cursor.execute(
                    "ALTER TABLE processed_pmc_articles ADD COLUMN filepath TEXT"
                )
                logger.info("Added 'filepath' column to processed_pmc_articles table.")
                conn.commit()

        logger.info(f"State database initialized successfully at {DB_PATH}")
    except sqlite3.Error as e:
        logger.error(
            f"Error initializing state database at {DB_PATH}: {e}", exc_info=True
        )
        raise


def get_article_details(pmc_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves all details for a given PMC ID."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM processed_pmc_articles WHERE pmc_id = ?", (pmc_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error getting details for PMC ID {pmc_id}: {e}", exc_info=True)
        return None


def add_or_update_article_status(
    pmc_id: str,
    status: str,
    job_id: Optional[str] = None,
    filepath: Optional[str] = None,
):
    """Adds/updates article status, job_id, and filepath. Updates last_attempted."""
    current_timestamp = datetime.now()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            updates: Dict[str, Any] = {
                "status": status,
                "last_attempted": current_timestamp,
            }
            if job_id is not None:
                updates["submitted_job_id"] = job_id
            if filepath is not None:
                updates["filepath"] = filepath

            # Updates dictionary prepared for SQL query

            sql = """
                INSERT INTO processed_pmc_articles (pmc_id, status, last_attempted, submitted_job_id, filepath, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(pmc_id) DO UPDATE SET
                    status = excluded.status,
                    last_attempted = excluded.last_attempted,
                    submitted_job_id = CASE WHEN excluded.submitted_job_id IS NOT NULL THEN excluded.submitted_job_id ELSE submitted_job_id END,
                    filepath = CASE WHEN excluded.filepath IS NOT NULL THEN excluded.filepath ELSE filepath END;
            """

            current_details = get_article_details(pmc_id)
            val_job_id = (
                job_id
                if job_id is not None
                else (
                    current_details.get("submitted_job_id") if current_details else None
                )
            )
            val_filepath = (
                filepath
                if filepath is not None
                else (current_details.get("filepath") if current_details else None)
            )

            cursor.execute(
                sql,
                (
                    pmc_id,
                    status,
                    current_timestamp,
                    val_job_id,
                    val_filepath,
                    current_timestamp,
                ),
            )
            conn.commit()
        logger.debug(
            f"Status for PMC ID {pmc_id} set to {status}. Job ID: {val_job_id if val_job_id else 'N/A'}. Filepath: {val_filepath if val_filepath else 'N/A'}"
        )
    except sqlite3.Error as e:
        logger.error(
            f"Error setting status for PMC ID {pmc_id} to {status}: {e}", exc_info=True
        )


# --- NCBI E-utils Helper Functions ---
def _make_ncbi_request(base_url: str, params: dict, timeout: int = 30) -> str | None:
    """Makes a request to NCBI E-utilities with rate limiting."""
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    params["email"] = NCBI_EMAIL
    params["tool"] = NCBI_TOOL_NAME
    try:
        logger.debug(
            f"Making NCBI request to {base_url} with params: {params.get('id', params.get('term'))}"
        )
        response = requests.get(base_url, params=params, timeout=timeout)
        response.raise_for_status()
        time.sleep(0.35 if not NCBI_API_KEY else 0.11)
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during NCBI API request to {base_url}: {e}")
        return None


def fetch_pmc_ids_from_pubmed(
    search_term: str = NCBI_SEARCH_TERM, max_results: int = NCBI_MAX_RESULTS
) -> List[str]:
    """Fetches a list of PMC IDs from PubMed based on a search term."""
    logger.info(
        f"Searching PubMed for PMIDs related to: '{search_term}' (max_results: {max_results}) with date filter 2015..."
    )
    esearch_params = {
        "db": "pubmed",
        "term": search_term,
        "retmax": max_results,
        "sort": "pub_date",
        "usehistory": "y",
        "mindate": "2021/01/01",
        "maxdate": "2021/12/31",
        "datetype": "pdat",
    }
    esearch_response_xml = _make_ncbi_request(BASE_URL_ESEARCH, esearch_params)
    pmids: List[str] = []
    if esearch_response_xml:
        try:
            esearch_root = ET.fromstring(esearch_response_xml)
            id_list_element = esearch_root.find("IdList")
            if id_list_element is not None:
                pmids = [
                    id_el.text for id_el in id_list_element.findall("Id") if id_el.text
                ]
            if pmids:
                logger.info(f"ESearch successful: Found {len(pmids)} PMIDs.")
            else:
                logger.warning("ESearch returned no PMIDs for the search term.")
        except ET.ParseError as e:
            logger.error(f"Error parsing ESearch XML response: {e}")
            logger.debug(f"ESearch response XML: {esearch_response_xml[:500]}")
    else:
        logger.error("ESearch request failed. Cannot proceed to EFetch.")
        return []

    if not pmids:
        return []

    fetched_pmc_ids = []

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            existing_pmc_ids_in_db = {
                row[0]
                for row in cursor.execute(
                    "SELECT pmc_id FROM processed_pmc_articles WHERE pmc_id IS NOT NULL"
                ).fetchall()
            }
    except sqlite3.Error as e:
        logger.error(
            f"Error accessing SQLite DB to get existing PMC IDs: {e}", exc_info=True
        )
        return []

    # Process PMIDs in batches for EFetch
    for i in range(0, len(pmids), EFETCH_BATCH_SIZE):
        batch_pmids = pmids[i : i + EFETCH_BATCH_SIZE]
        pmids_str = ",".join(batch_pmids)
        efetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmids_str}&retmode=xml&rettype=abstract&email={NCBI_EMAIL}&tool={NCBI_TOOL_NAME}"
        logger.info(
            f"Fetching details for batch of {len(batch_pmids)} PMIDs ({i // EFETCH_BATCH_SIZE + 1}/{(len(pmids) + EFETCH_BATCH_SIZE - 1) // EFETCH_BATCH_SIZE})..."
        )

        try:
            response = requests.get(efetch_url, timeout=NCBI_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during NCBI API request to {efetch_url}: {e}")
            logger.warning(f"Skipping batch due to EFetch error: {batch_pmids}")
            continue

        root = ET.fromstring(response.content)
        for article in root.findall(".//PubmedArticle"):
            pmid_element = article.find(".//PMID")
            pmid = pmid_element.text if pmid_element is not None else None

            pmc_id = None
            article_ids = article.find(".//ArticleIdList")
            if article_ids is not None:
                for aid in article_ids.findall(".//ArticleId"):
                    if aid.get("IdType") == "pmc":
                        pmc_id = aid.text
                        break

            if pmid and pmc_id:
                if (
                    pmc_id not in existing_pmc_ids_in_db
                    and pmc_id not in fetched_pmc_ids
                ):
                    fetched_pmc_ids.append(pmc_id)
                    logger.debug(f"Found new PMC ID: {pmc_id} (from PMID: {pmid})")
                else:
                    logger.debug(f"PMC ID {pmc_id} already processed or queued.")
            elif pmid:
                logger.debug(
                    f"PMID {pmid} does not have a corresponding PMC ID in this record."
                )

        if i + EFETCH_BATCH_SIZE < len(pmids):
            time.sleep(0.5)

    if not fetched_pmc_ids:
        logger.info(
            "No new PMC IDs found in the fetched PubMed records that are not already in the database."
        )
    return fetched_pmc_ids


# Selenium PDF Download Functions
def _setup_selenium_driver(download_dir: str) -> Optional[webdriver.Chrome]:
    """Initializes Selenium WebDriver for PDF downloading."""
    logger.info("Setting up Selenium WebDriver...")
    try:
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        chrome_options.page_load_strategy = "none"

        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "download.open_pdf_in_system_reader": False,
            "profile.default_content_settings.popups": 0,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        os.environ["WDM_LOG_LEVEL"] = "0"
        os.environ["WDM_SSL_VERIFY"] = "0"

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("WebDriver setup successful.")
        return driver
    except Exception as e:
        logger.error(f"WebDriver setup failed: {e}", exc_info=True)
        return None


def _download_pdf_with_selenium(
    driver: webdriver.Chrome, pmc_id: str, target_dir: str, temp_download_dir: str
) -> Optional[str]:
    """Attempts to download PDF for a given PMC ID using Selenium."""
    article_url = ARTICLE_URL_TEMPLATE.format(pmc_id)
    expected_final_filename = f"{pmc_id}.pdf"
    final_filepath = os.path.join(target_dir, expected_final_filename)

    if os.path.exists(final_filepath):
        logger.info(f"Skipping {pmc_id}: File already exists at {final_filepath}")
        return final_filepath

    if os.path.exists(temp_download_dir):
        shutil.rmtree(temp_download_dir)
    os.makedirs(temp_download_dir, exist_ok=True)

    downloaded_filename_from_selenium = None
    pdf_absolute_url = None
    action_taken = "None"
    # Initialize variables for PDF download process

    driver.set_page_load_timeout(30)

    try:
        try:
            logger.debug(
                f"Attempting to find direct PDF link for {pmc_id} via requests to {article_url}"
            )
            headers_req = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(
                article_url, headers=headers_req, timeout=30, verify=True
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            pdf_link_tag = (
                soup.find("a", attrs={"data-ga-label": "pdf_download_desktop"})
                or soup.find("a", class_=["format-pdf", "pdf-link"])
                or soup.find(
                    "a",
                    href=lambda href: href is not None
                    and href.lower().endswith(".pdf")
                    and "articles" in href.lower(),
                )
            )

            if pdf_link_tag and "href" in pdf_link_tag: # type: ignore
                pdf_relative_url = pdf_link_tag["href"] # type: ignore
                if not pdf_relative_url.startswith("http"): # type: ignore
                    pdf_absolute_url = urljoin(response.url, pdf_relative_url) # type: ignore
                else:
                    pdf_absolute_url = pdf_relative_url
                logger.info(
                    f"Found potential direct PDF URL for {pmc_id}: {pdf_absolute_url}"
                )
        except requests.exceptions.RequestException as req_err:
            logger.warning(
                f"Requests failed to get article page {article_url} or find direct link: {req_err}. Will rely on Selenium navigation."
            )

        if pdf_absolute_url:
            logger.info(
                f"Navigating directly to PDF URL with Selenium: {pdf_absolute_url}"
            )
            driver.set_page_load_timeout(90)
            driver.get(pdf_absolute_url)
            action_taken = f"Navigated directly to PDF URL: {pdf_absolute_url}"
            time.sleep(10)
        else:
            logger.info(
                f"Navigating to article page with Selenium to find & click PDF link: {article_url}"
            )
            driver.set_page_load_timeout(30)
            driver.get(article_url)
            time.sleep(3)
            action_taken = f"Navigated to article page: {article_url}"
            pdf_link_element = None
            try:
                pdf_link_element = driver.find_element(
                    "css selector", "a[data-ga-label='pdf_download_desktop']"
                )
                logger.info("Found PDF link by data-ga-label. Clicking...")
            except NoSuchElementException:
                try:
                    pdf_link_element = driver.find_element(
                        "css selector", "a.format-pdf, a.pdf-link"
                    )
                    logger.info("Found PDF link by class name. Clicking...")
                except NoSuchElementException:
                    try:
                        pdf_link_element = driver.find_element(
                            "xpath",
                            "(//a[contains(translate(@href, 'PDF', 'pdf'), '.pdf') and contains(@href, 'articles') and (contains(@class, 'pdf') or contains(@data-ga-action, 'pdf'))])[1]",
                        )
                        logger.info(
                            "Found generic PDF link by more specific href/class/action. Clicking..."
                        )
                    except NoSuchElementException:
                        try:
                            pdf_link_element = driver.find_element(
                                "xpath",
                                "(//a[contains(translate(@href, 'PDF', 'pdf'), '.pdf') and contains(@href, 'articles')])[1]",
                            )
                            logger.info(
                                "Found broadest generic PDF link by href. Clicking..."
                            )
                        except NoSuchElementException as find_err_final:
                            err_msg = (
                                f"Could not find clickable PDF link on {article_url}."
                            )
                            logger.error(
                                f"FAILED (Link Find Selenium): {err_msg} Error: {find_err_final.msg}"
                            )
                            # PDF link not found with Selenium
                            try:
                                page_text_lower = driver.find_element(
                                    "tag name", "body"
                                ).text.lower()
                                embargo_keywords = [
                                    "will be available in pmc on",
                                    "delayed release",
                                    "embargo",
                                    "article is not yet available",
                                ]
                                if any(
                                    keyword in page_text_lower
                                    for keyword in embargo_keywords
                                ):
                                    embargo_msg = f"Article {pmc_id} appears to be under embargo or not yet available on PMC."
                                    logger.info(
                                        f"INFO - {embargo_msg} No PDF link found."
                                    )
                                    # Article is embargoed/unavailable
                                    pass
                                else:
                                    logger.warning(
                                        f"WARNING - No PDF link found on {article_url} and no clear embargo message detected."
                                    )
                            except Exception as page_check_err:
                                logger.warning(
                                    f"WARNING - Could not check page content for embargo message: {page_check_err}"
                                )
                            add_or_update_article_status(
                                pmc_id,
                                ArticleStatus.DOWNLOAD_FAILED,
                                filepath=None,
                                job_id=None,
                            )
                            return None
            pdf_link_element.click()
            action_taken += " -> Clicked PDF link"
            time.sleep(5)

        driver.set_page_load_timeout(30)

        logger.debug(
            f"Waiting for download of {pmc_id} to complete in {temp_download_dir}..."
        )
        download_wait_timeout = 120
        start_wait_time = time.time()
        download_complete = False

        while time.time() - start_wait_time < download_wait_timeout:
            try:
                files_in_temp_dir = [
                    f
                    for f in os.listdir(temp_download_dir)
                    if os.path.isfile(os.path.join(temp_download_dir, f))
                ]
                pdf_files = [f for f in files_in_temp_dir if f.lower().endswith(".pdf")]

                if pdf_files:
                    potential_pdf_path = os.path.join(temp_download_dir, pdf_files[0])
                    crdownload_files = [
                        f
                        for f in files_in_temp_dir
                        if f.lower().endswith(".crdownload")
                    ]
                    if not crdownload_files:
                        current_size = os.path.getsize(potential_pdf_path)
                        if current_size > 0:
                            downloaded_filename_from_selenium = pdf_files[0]
                            logger.info(
                                f"Download appears complete for {pmc_id}. Found PDF: {downloaded_filename_from_selenium} (Size: {current_size} bytes)"
                            )
                            download_complete = True
                            break
                else:
                    crdownload_files = [
                        f
                        for f in files_in_temp_dir
                        if f.lower().endswith(".crdownload")
                    ]
                    if crdownload_files:
                        logger.debug(
                            f"Download in progress for {pmc_id}: Found .crdownload files: {crdownload_files}. Waiting..."
                        )
                    else:
                        logger.debug(
                            f"No PDF and no .crdownload files found yet for {pmc_id}. Contents: {files_in_temp_dir}. Waiting..."
                        )
            except FileNotFoundError:
                logger.debug(
                    f"Temp download directory {temp_download_dir} not found. Waiting..."
                )
            except Exception as e_wait_loop:
                logger.warning(
                    f"Error in download wait loop for {pmc_id}: {e_wait_loop}"
                )
            time.sleep(2)

        if not download_complete or not downloaded_filename_from_selenium:
            err_msg = f"Download for {pmc_id} did not result in a PDF file in {temp_download_dir} after {download_wait_timeout}s. Action: {action_taken}"
            logger.error(f"FAILED (Timeout/Not Found): {err_msg}")
            if os.path.exists(temp_download_dir):
                logger.info(
                    f"Contents of {temp_download_dir}: {os.listdir(temp_download_dir)}"
                )
            add_or_update_article_status(
                pmc_id, ArticleStatus.DOWNLOAD_FAILED, filepath=None, job_id=None
            )
            return None

        temp_filepath = os.path.join(
            temp_download_dir, downloaded_filename_from_selenium
        )
        time.sleep(1)

        if not os.path.exists(temp_filepath) or os.path.getsize(temp_filepath) == 0:
            err_msg = f"PDF file {downloaded_filename_from_selenium} missing or empty post-wait."
            logger.error(f"FAILED (File Missing or Empty): {err_msg}")
            add_or_update_article_status(
                pmc_id, ArticleStatus.DOWNLOAD_FAILED, filepath=None, job_id=None
            )
            return None

        os.makedirs(target_dir, exist_ok=True)
        shutil.move(temp_filepath, final_filepath)
        logger.info(f"Successfully downloaded and moved {pmc_id} to {final_filepath}")
        add_or_update_article_status(
            pmc_id, ArticleStatus.DOWNLOADED, filepath=final_filepath, job_id=None
        )
        return final_filepath

    except TimeoutException as te:
        err_msg = f"Selenium timed out loading URL for {pmc_id}. Last action: {action_taken}. URL: {driver.current_url if driver else 'N/A'}"
        logger.error(f"FAILED (Page Load Timeout): {err_msg}. Error: {te.msg}")
        add_or_update_article_status(
            pmc_id, ArticleStatus.DOWNLOAD_FAILED, filepath=None, job_id=None
        )
        return None
    except WebDriverException as wde:
        err_msg = f"WebDriver Error for {pmc_id}: {wde.msg}"
        logger.error(f"FAILED (WebDriver Error): {err_msg}", exc_info=True)
        add_or_update_article_status(
            pmc_id, ArticleStatus.DOWNLOAD_FAILED, filepath=None, job_id=None
        )
        return None
    except Exception as e_main_dl:
        err_msg = f"Unexpected Error during PDF download for {pmc_id}: {str(e_main_dl)}"
        logger.error(f"FAILED (Unexpected Error): {err_msg}", exc_info=True)
        add_or_update_article_status(
            pmc_id, ArticleStatus.DOWNLOAD_FAILED, filepath=None, job_id=None
        )
        return None


# API Submission Function
def _submit_pdf_to_api(pmc_id: str, pdf_filepath: str) -> Optional[str]:
    """Submits the downloaded PDF to the FastAPI /analyze endpoint."""
    if not os.path.exists(pdf_filepath):
        logger.error(
            f"API Submission Error: PDF file not found at {pdf_filepath} for PMC ID {pmc_id}"
        )
        return None

    analyze_url = f"{settings.AUTOMATED_FETCHER_API_URL}/analyze"
    logger.info(f"Submitting {pmc_id} (file: {pdf_filepath}) to API: {analyze_url}")

    try:
        with open(pdf_filepath, "rb") as f:
            files = {"file": (os.path.basename(pdf_filepath), f, "application/pdf")}
            data = {
                "identifier": pmc_id,
                "source": JobSourceEnum.AUTOMATED.value,
                "external_id": pmc_id,
            }
            response = requests.post(analyze_url, files=files, data=data, timeout=30)
            response.raise_for_status()

            response_data = response.json()
            job_id = response_data.get("job_id")
            if job_id:
                logger.info(f"Successfully submitted {pmc_id} to API. Job ID: {job_id}")
                return job_id
            else:
                logger.error(
                    f"API submission for {pmc_id} succeeded but no job_id in response: {response_data}"
                )
                return None
    except requests.exceptions.HTTPError as http_err:
        logger.error(
            f"API Submission HTTP Error for {pmc_id}: {http_err} - Response: {http_err.response.text if http_err.response else 'No response body'}"
        )
        return None
    except requests.exceptions.RequestException as req_err:
        logger.error(f"API Submission Request Error for {pmc_id}: {req_err}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error during API submission for {pmc_id}: {e}", exc_info=True
        )
        return None


def main():
    logger.info("==== Starting Automated RCT Processor Script ====")
    api_url_setting = settings.AUTOMATED_FETCHER_API_URL
    logger.info(
        f"Configured FastAPI application URL for submissions: {api_url_setting}"
    )

    try:
        init_state_db()
        os.makedirs(DOWNLOAD_FOLDER_BASE, exist_ok=True)

        # 1. Fetch new PMC IDs
        logger.info("--- Stage 1: Fetching New PMC IDs ---")
        newly_fetched_pmc_ids = fetch_pmc_ids_from_pubmed(max_results=NCBI_MAX_RESULTS)
        if newly_fetched_pmc_ids:
            logger.info(
                f"Fetched {len(newly_fetched_pmc_ids)} PMC IDs. Checking against local DB."
            )
            for pmc_id in newly_fetched_pmc_ids:
                details = get_article_details(pmc_id)
                if not details:
                    logger.info(
                        f"New PMC ID {pmc_id} found. Adding to DB as PENDING_DOWNLOAD."
                    )
                    add_or_update_article_status(pmc_id, ArticleStatus.PENDING_DOWNLOAD)
                # else: logger.debug(f"PMC ID {pmc_id} already in DB with status: {details['status']}.")
        else:
            logger.info("No new PMC IDs fetched from PubMed in this run.")

        # 2. Download Pending PDFs
        logger.info("--- Stage 2: Downloading Pending PDFs ---")
        driver = None
        articles_to_download_query = "SELECT pmc_id FROM processed_pmc_articles WHERE status = ? OR status = ? ORDER BY created_at ASC LIMIT ?"

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                articles_to_download_query,
                (
                    ArticleStatus.PENDING_DOWNLOAD,
                    ArticleStatus.DOWNLOAD_FAILED,
                    DOWNLOAD_LIMIT_PER_RUN,
                ),
            )
            articles_needing_download = [row[0] for row in cursor.fetchall()]

        if not articles_needing_download:
            logger.info("No articles currently marked for PDF download.")
        else:
            logger.info(
                f"Attempting to download PDFs for {len(articles_needing_download)} articles: {articles_needing_download}"
            )
            driver = _setup_selenium_driver(SELENIUM_TEMP_DOWNLOAD_DIR)
            if driver:
                for pmc_id in articles_needing_download:
                    logger.info(f"Processing PDF download for PMC ID: {pmc_id}")
                    downloaded_pdf_path = _download_pdf_with_selenium(
                        driver, pmc_id, DOWNLOAD_FOLDER_BASE, SELENIUM_TEMP_DOWNLOAD_DIR
                    )
                    if downloaded_pdf_path:
                        logger.info(f"Successfully processed download for {pmc_id}.")
                    else:
                        logger.error(
                            f"Failed to download PDF for {pmc_id}. Status updated by download function."
                        )
                    time.sleep(1)
            else:
                logger.error(
                    "Selenium WebDriver could not be initialized. Skipping PDF downloads for this run."
                )
        if driver:
            logger.info("Closing Selenium WebDriver after download stage...")
            driver.quit()
            logger.info("WebDriver closed.")
            try:
                if os.path.exists(SELENIUM_TEMP_DOWNLOAD_DIR) and not os.listdir(
                    SELENIUM_TEMP_DOWNLOAD_DIR
                ):
                    shutil.rmtree(SELENIUM_TEMP_DOWNLOAD_DIR)
            except Exception:
                pass

        # 3. Submit Downloaded PDFs to API
        # COMMENTED OUT: API submission stage - only downloading PDFs for now
        # logger.info("--- Stage 3: Submitting Downloaded PDFs to API ---")
        # articles_to_submit_query = "SELECT pmc_id, filepath FROM processed_pmc_articles WHERE status = ? ORDER BY last_attempted ASC LIMIT ?"

        # with sqlite3.connect(DB_PATH) as conn:
        #     conn.row_factory = sqlite3.Row
        #     cursor = conn.cursor()
        #     cursor.execute(articles_to_submit_query, (ArticleStatus.DOWNLOADED, SUBMISSION_LIMIT_PER_RUN))
        #     articles_needing_submission = [dict(row) for row in cursor.fetchall()]

        # if not articles_needing_submission:
        #     logger.info("No downloaded PDFs currently pending API submission.")
        # else:
        #     logger.info(f"Attempting to submit {len(articles_needing_submission)} PDFs to API.")
        #     for article_data in articles_needing_submission:
        #         pmc_id = article_data['pmc_id']
        #         pdf_filepath = article_data['filepath']
        #         if not pdf_filepath or not os.path.exists(pdf_filepath):
        #             logger.error(f"Cannot submit PMC ID {pmc_id}: Filepath '{pdf_filepath}' is invalid or file does not exist. Setting status to DOWNLOAD_FAILED.")
        #             add_or_update_article_status(pmc_id, ArticleStatus.DOWNLOAD_FAILED, filepath=None)
        #             continue

        #         logger.info(f"Processing API submission for PMC ID: {pmc_id}, File: {pdf_filepath}")
        #         job_id = _submit_pdf_to_api(pmc_id, pdf_filepath)
        #         if job_id:
        #             add_or_update_article_status(pmc_id, ArticleStatus.SUBMITTED_TO_API, job_id=job_id)
        #             logger.info(f"Successfully submitted PMC ID {pmc_id}. API Job ID: {job_id}")
        #         else:
        #             add_or_update_article_status(pmc_id, ArticleStatus.SUBMISSION_FAILED)
        #             logger.error(f"Failed to submit PDF for PMC ID {pmc_id} to API.")
        #         time.sleep(1) # Pause between API submissions

        logger.info("API submission stage skipped - only downloading PDFs in this run.")

    except Exception as e:
        logger.critical(
            f"Critical error in main execution of Automated RCT Processor: {e}",
            exc_info=True,
        )
    finally:
        logger.info("==== Automated RCT Processor Script Finished ====")


if __name__ == "__main__":
    main()
