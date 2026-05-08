import pathlib
from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices
from typing import List, Optional

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Core services URLs
    DATABASE_URL: PostgresDsn
    REDIS_URL: RedisDsn
    PDF_STORAGE_PATH: str = "/app/pdf_storage"

    # LLM API keys
    GOOGLE_API_KEY: Optional[str] = Field(None, validation_alias="GOOGLE_API_KEY")

    BACKEND_CORS_ORIGINS: Optional[List[str]] = Field(
        None, description="Comma-separated string of allowed CORS origins"
    )

    # LLM specific settings
    GEMINI_MODEL_NAME: str = "gemini-2.0-flash-001"  # Default Gemini model (legacy, used as fallback)
    OPENROUTER_LLM_MODEL: str = Field(
        default="google/gemini-3-flash-preview:nitro",
        description="OpenRouter model for structured LLM extraction",
    )

    # For Retraction Watch service
    RETRACTION_WATCH_CSV_PATH: str = Field(
        default="/app/var/data/retraction_watch.csv",
        description="Path to retraction watch CSV file",
    )

    # Logging configuration
    LOG_LEVEL: str = "INFO"

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file=str(DOTENV_PATH), env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "inspect-ai"
    API_V1_STR: str = "/api/v1"

    # URL for the automated RCT fetcher script to call the API
    AUTOMATED_FETCHER_API_URL: str = "http://localhost:8000/api/v1"

    # GROBID Service Configuration
    GROBID_PORT: int = Field(
        default=8070,
        description="GROBID service port",
    )
    GROBID_SERVICE_URL: str = Field(
        default="http://grobid:8070",
        description="GROBID service base URL (direct connection)",
    )
    GROBID_TIMEOUT_SECONDS: int = Field(
        default=120,
        description="Timeout for GROBID requests",
    )
    GROBID_MAX_FILE_SIZE_MB: int = Field(
        default=50, description="Maximum PDF file size in MB for GROBID processing"
    )
    GROBID_MAX_CONNECTIONS: int = Field(
        default=5,
        description="Maximum HTTP connections to GROBID service (reduced for memory efficiency)",
    )
    GROBID_KEEPALIVE_CONNECTIONS: int = Field(
        default=2,
        description="HTTP keepalive connections to maintain for GROBID service",
    )
    GROBID_MAX_RETRIES: int = Field(
        default=3, description="Maximum retry attempts per GROBID request"
    )

    # GROBID Consolidation Strategy Configuration (matching API parameter names)
    GROBID_CONSOLIDATE_HEADER: int = Field(
        default=1, description="Header consolidation level: 0=none, 1=full, 2=DOI-only"
    )
    GROBID_CONSOLIDATE_CITATIONS: int = Field(
        default=0,  # Disabled to prevent GROBID hanging on Crossref API errors
        description="Citations consolidation level: 0=none, 1=full, 2=DOI-only",
    )

    # PubPeer Service Configuration
    PUBPEER_API_URL: str = Field(
        default="https://pubpeer.com/v3/publications",
        description="PubPeer API endpoint URL",
    )
    PUBPEER_DEV_KEY: str = Field(
        default="PythonTest",
        description="PubPeer API development key",
    )

    OPENROUTER_API_KEY: Optional[str] = Field(
        None, description="OpenRouter API key for LLM checks"
    )
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
    )

    LOGFIRE_TOKEN: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("LOGFIRE_TOKEN", "logfire_token")
    )

    # Paper/demo mode. When enabled, API routes use a deterministic local reviewer
    # instead of requiring Clerk JWT verification.
    DISABLE_AUTH: bool = Field(
        default=False,
        description="Disable Clerk auth and use a local demo reviewer",
    )
    DEMO_REVIEWER_ID: str = Field(
        default="inspect_demo_reviewer",
        description="Stable reviewer identifier used when DISABLE_AUTH=true",
    )

    # Clerk configuration for backend auth verification
    CLERK_JWKS_URL: Optional[str] = Field(
        default=None,
        description="JWKS endpoint used to verify Clerk session tokens",
    )
    CLERK_ISSUER: Optional[str] = Field(
        default=None,
        description="Expected issuer claim for Clerk-issued tokens",
    )
    CLERK_ALLOWED_AUDIENCES: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("CLERK_ALLOWED_AUDIENCES", "CLERK_AUDIENCE"),
        description="Comma-separated list of allowed audience claims for Clerk tokens",
    )
    CLERK_JWT_TEMPLATE_NAME: str = Field(
        default="backend",
        description="Name of the Clerk JWT template used for backend requests",
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | List[str] | None) -> Optional[List[str]]:
        if isinstance(value, str):
            if not value.strip():
                return None
            return [origin.strip() for origin in value.split(",")]
        elif isinstance(value, list):
            return value
        return None

    @field_validator("CLERK_ALLOWED_AUDIENCES", mode="before")
    @classmethod
    def parse_audience_list(cls, value: str | List[str] | None) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            if not value.strip():
                return None
            return [aud.strip() for aud in value.split(",") if aud.strip()]
        if isinstance(value, list):
            return value
        raise ValueError("CLERK_ALLOWED_AUDIENCES must be a comma-separated string or list")

    def get_grobid_service_url(self) -> str:
        """Get the dynamic GROBID service URL based on configured port."""
        return f"http://grobid:{self.GROBID_PORT}"


settings = Settings()  # pyright: ignore[reportCallIssue]  # type: ignore[call-arg] # type: ignore[reportOptionalMemberAccess]


def get_settings():
    return settings  # pyright: ignore[reportOptionalMemberAccess]


# Application Constants
# These are fixed values that don't change based on environment

# Job and Check Processing
# NOTE: Total checks is now dynamic based on check registry profile
# Use get_default_total_checks() instead of this constant for new code
DEFAULT_TOTAL_CHECKS = 11  # Legacy fallback - kept for backward compatibility

DEFAULT_CHECKS_COMPLETED = 0
DEFAULT_CURRENT_PHASE = "initializing"


def get_default_total_checks() -> int:
    """
    Get the default total number of checks based on active check registry profile.

    This replaces the static DEFAULT_TOTAL_CHECKS constant with a dynamic value
    that reflects the actual number of enabled checks in the current environment.

    Returns:
        Number of enabled checks in the current profile.
    """
    try:
        from core.config.check_registry import registry
        return registry.get_total_checks()
    except Exception:
        # Fallback to legacy constant if registry not available
        return DEFAULT_TOTAL_CHECKS

# String Length Limits
MAX_CHECK_NAME_LENGTH = 50
MAX_CHECK_STATUS_LENGTH = 20
MAX_EXTERNAL_ID_LENGTH = 255
MAX_FILE_PATH_LENGTH = 500
MAX_CURRENT_PHASE_LENGTH = 50

MAX_REVIEWER_NAME_LENGTH = 150
MAX_REVIEWER_USERNAME_LENGTH = 150
MAX_REVIEWER_AFFILIATION_LENGTH = 255
MAX_REVIEWER_ROLE_LENGTH = 150
MAX_REVIEWER_COUNTRY_LENGTH = 120
MAX_REVIEWER_ORCID_LENGTH = 19

# Database Field Defaults
DEFAULT_JOB_SOURCE = "USER"
DEFAULT_KG_VISIBILITY = "anonymous"
