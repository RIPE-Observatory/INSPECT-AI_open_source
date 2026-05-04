"""Configuration helpers for the core package."""

from .config import (
    Settings,
    settings,
    get_settings,
    DEFAULT_TOTAL_CHECKS,
    get_default_total_checks,  # NEW: Dynamic check count
    DEFAULT_CHECKS_COMPLETED,
    DEFAULT_CURRENT_PHASE,
    MAX_CHECK_NAME_LENGTH,
    MAX_CHECK_STATUS_LENGTH,
    MAX_EXTERNAL_ID_LENGTH,
    MAX_FILE_PATH_LENGTH,
    MAX_CURRENT_PHASE_LENGTH,
    DEFAULT_JOB_SOURCE,
    MAX_REVIEWER_NAME_LENGTH,
    MAX_REVIEWER_USERNAME_LENGTH,
    MAX_REVIEWER_AFFILIATION_LENGTH,
    MAX_REVIEWER_ROLE_LENGTH,
    MAX_REVIEWER_COUNTRY_LENGTH,
    MAX_REVIEWER_ORCID_LENGTH,
    DEFAULT_KG_VISIBILITY,
)
from .check_registry import registry, get_registry  # noqa: F401

__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "DEFAULT_TOTAL_CHECKS",
    "get_default_total_checks",  # NEW: Dynamic check count
    "DEFAULT_CHECKS_COMPLETED",
    "DEFAULT_CURRENT_PHASE",
    "MAX_CHECK_NAME_LENGTH",
    "MAX_CHECK_STATUS_LENGTH",
    "MAX_EXTERNAL_ID_LENGTH",
    "MAX_FILE_PATH_LENGTH",
    "MAX_CURRENT_PHASE_LENGTH",
    "DEFAULT_JOB_SOURCE",
    "MAX_REVIEWER_NAME_LENGTH",
    "MAX_REVIEWER_USERNAME_LENGTH",
    "MAX_REVIEWER_AFFILIATION_LENGTH",
    "MAX_REVIEWER_ROLE_LENGTH",
    "MAX_REVIEWER_COUNTRY_LENGTH",
    "MAX_REVIEWER_ORCID_LENGTH",
    "DEFAULT_KG_VISIBILITY",
    "registry",
    "get_registry",
]
