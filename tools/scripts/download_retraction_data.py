import httpx
import os
import logging
from dotenv import load_dotenv

from app.core.config import get_settings # type: ignore

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SETTINGS = get_settings()

DEFAULT_CSV_PATH = "src/data/retraction_watch.csv"
CSV_PATH = getattr(SETTINGS, "RETRACTION_WATCH_CSV_PATH", DEFAULT_CSV_PATH)

RAW_CSV_URL = (
    "https://gitlab.com/crossref/retraction-watch-data/-/raw/main/retraction_watch.csv"
)


def download_retraction_watch_csv(file_path: str = CSV_PATH) -> bool:
    """
    Downloads the Retraction Watch CSV data to the specified local path.

    Args:
        file_path (str): The local path where the CSV file should be saved.

    Returns:
        bool: True if download was successful, False otherwise.
    """
    logger.info(f"Attempting to download Retraction Watch CSV from: {RAW_CSV_URL}")
    logger.info(f"Saving to local path: {file_path}")

    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            logger.info(f"Ensured directory exists: {dir_name}")

        with httpx.stream(
            "GET", RAW_CSV_URL, timeout=60.0, follow_redirects=True
        ) as response:
            response.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
            logger.info(
                f"Successfully downloaded and saved Retraction Watch CSV to: {file_path}"
            )
            return True
    except httpx.HTTPStatusError as e_http:
        logger.error(
            f"HTTP error occurred while downloading CSV: {e_http.response.status_code} - {e_http.response.text[:200]}"
        )
    except httpx.RequestError as e_req:
        logger.error(f"Request error occurred while downloading CSV: {e_req}")
    except IOError as e_io:
        logger.error(f"IOError occurred while saving CSV to {file_path}: {e_io}")
    except Exception as e_gen:
        logger.error(f"An unexpected error occurred: {e_gen}", exc_info=True)

    return False


if __name__ == "__main__":
    logger.info("Running Retraction Watch CSV download script...")
    success = download_retraction_watch_csv()
    if success:
        logger.info("Download script completed successfully.")
    else:
        logger.error("Download script failed.")
