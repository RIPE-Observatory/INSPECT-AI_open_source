import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

REG_CTG = "clinicaltrials.gov"
REG_ANZCTR = "anzctr"
REG_PACTR = "pactr"
REG_CTRI = "ctri"
REG_CHICTR = "chictr"
REG_ISRCTN = "isrctn"
REG_IRCT = "irct"
REG_JPRN = "jprn"
REG_DRKS = "drks"
REG_REBEC = "rebec"
REG_EUCTR = "euctr"
REG_KCT = "kct"
REG_TCTR = "tctr"

# Define known date formats for each registry type (from WHO or direct API)
REGISTRY_DATE_FORMATS: Dict[str, List[str]] = {
    REG_CTG: ["%d-%m-%Y"],
    REG_ANZCTR: ["%d/%m/%Y"],
    REG_PACTR: ["%d/%m/%Y"],
    REG_CTRI: ["%d-%m-%Y"],
    REG_CHICTR: ["%Y-%m-%d"],
    REG_ISRCTN: ["%d/%m/%Y"],
    REG_IRCT: ["%Y-%m-%d"],
    REG_JPRN: ["%Y/%m/%d"],
    REG_DRKS: ["%d/%m/%Y"],
    REG_REBEC: ["%d/%m/%Y"],
    REG_EUCTR: ["%d/%m/%Y"],
    REG_KCT: ["%Y-%m-%d"],
    REG_TCTR: ["%d/%m/%Y"],
    # Add other registries and their common WHO ICTRP portal formats here
}

LLM_DATE_FORMATS: List[str] = [
    "%d-%m-%Y",  # For DD-MM-YYYY from LLM
    "%m-%Y",  # For MM-YYYY from LLM
]


def parse_date_to_components(
    date_str: str,
    registry_name_hint: Optional[str] = None,
    *,
    job_id: Optional[str] = None,
) -> Optional[Dict[str, Optional[int]]]:
    """
    Parses a date string into year, month, and optionally day components.
    Uses registry_name_hint to try specific formats first, then common LLM formats.

    Args:
        date_str: The date string to parse.
        registry_name_hint: The specific registry name (e.g., 'ChiCTR', 'ClinicalTrials.gov') to guide format selection.

    Returns:
        A dictionary {"year": YYYY, "month": MM, "day": DD} where day can be None if only month/year was parsed.
        Returns None if parsing fails for all attempted formats.
    """
    if not date_str or not isinstance(date_str, str):
        return None

    formats_to_try: List[str] = []
    normalized_registry_hint = (
        registry_name_hint.lower().replace(".", "") if registry_name_hint else None
    )

    if normalized_registry_hint and normalized_registry_hint in REGISTRY_DATE_FORMATS:
        formats_to_try.extend(REGISTRY_DATE_FORMATS[normalized_registry_hint])

    # Add LLM formats as general fallbacks or if no registry hint
    formats_to_try.extend(LLM_DATE_FORMATS)

    # Add generic common formats as a last resort if specific hints don't match
    generic_formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%Y-%m",
    ]
    for gf in generic_formats:
        if gf not in formats_to_try:
            formats_to_try.append(gf)

    dt_object: Optional[datetime] = None
    parsed_format_type: Optional[str] = None  # To know if it was DD-MM-YYYY or MM-YYYY

    for fmt_code in formats_to_try:
        try:
            dt_object = datetime.strptime(date_str, fmt_code)
            if fmt_code == "%m-%Y" or fmt_code == "%Y-%m":
                parsed_format_type = "MM-YYYY"
            else:
                parsed_format_type = (
                    "DD-MM-YYYY"  # Assume full date if not MM-YYYY specific format
                )
            break  # Successfully parsed
        except ValueError:
            continue  # Try next format

    if dt_object:
        day_component = dt_object.day if parsed_format_type == "DD-MM-YYYY" else None
        return {"year": dt_object.year, "month": dt_object.month, "day": day_component}

    job_suffix = f" (job_id={job_id})" if job_id else ""
    logger.warning(
        f"Failed to parse date string '{date_str}' with hint '{registry_name_hint}' using available formats: {formats_to_try}{job_suffix}"
    )
    return None


def get_comparison_string(date_components: Dict[str, Optional[int]]) -> Optional[str]:
    """
    Converts parsed date components to a string for comparison (YYYY-MM-DD or YYYY-MM).
    """
    if (
        not date_components
        or not date_components.get("year")
        or not date_components.get("month")
    ):
        return None

    year = date_components["year"]
    month = date_components["month"]
    day = date_components.get("day")

    if day:
        return f"{year:04d}-{month:02d}-{day:02d}"
    else:
        return f"{year:04d}-{month:02d}"
