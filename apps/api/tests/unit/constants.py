"""
Test constants for unit tests.

Centralized constants to eliminate magic values and improve maintainability.
"""

# Clinical Trial Identifiers
TEST_NCT_ID = "NCT12345678"
TEST_NCT_ID_2 = "NCT98765432"
TEST_INVALID_NCT_ID = "NCT00000000"

# DOI Constants
TEST_DOI = "10.1234/test.2024.001"
TEST_DOI_2 = "10.5678/similar.2024.002"
TEST_RETRACTED_DOI = "10.1234/retracted.2023"

# Hash Values
TEST_HASH_MEAN_SD = "65.2_12.8"
TEST_HASH_MEAN_SD_2 = "63.9_14.1"
TEST_HASH_MEDIAN_IQR = "58.5_45.2_71.8"

# Numerical Test Values
TEST_MEAN = 65.2
TEST_SD = 12.8
TEST_N = 75
TEST_MEDIAN = 58.5
TEST_IQR_LOWER = 45.2
TEST_IQR_UPPER = 71.8

# Paper Metadata
TEST_PAPER_TITLE = "Test Clinical Trial for Unit Testing"
TEST_JOURNAL = "Journal of Unit Testing"
TEST_AUTHORS = ["Dr. Test A", "Dr. Mock B"]
TEST_PUBLICATION_YEAR = 2024

# File Paths
TEST_PDF_PATH = "test_paper.pdf"
TEST_NONEXISTENT_PDF = "nonexistent.pdf"

# Performance Limits (milliseconds)
UNIT_TEST_MAX_MS = (
    50  # Unit tests should complete in <50ms (realistic for complex tests)
)
UNIT_TEST_STRICT_MS = 10  # Strict unit tests should complete in <10ms (simple tests)
SETUP_MAX_MS = 5  # Setup should be <5ms
MOCK_CALL_MAX_MS = 2  # Mock calls should be <2ms
ASYNC_OPERATION_MAX_MS = 20  # Async operations should complete in <20ms

# Mock Response Codes
SUCCESS_STATUS = 200
NOT_FOUND_STATUS = 404
SERVER_ERROR_STATUS = 500
SERVICE_UNAVAILABLE_STATUS = 503

# Test Data Sizes
MIN_PDF_SIZE = 1024  # Minimum valid PDF size in bytes
LARGE_PDF_SIZE = 1024000  # Large PDF for testing

# Group Data Templates
TEST_GROUP_DATA_MEAN_SD = {"mean": str(TEST_MEAN), "sd": str(TEST_SD), "n": str(TEST_N)}

TEST_GROUP_DATA_MEDIAN_IQR = {
    "median": str(TEST_MEDIAN),
    "iqr_lower": str(TEST_IQR_LOWER),
    "iqr_upper": str(TEST_IQR_UPPER),
    "n": str(TEST_N),
}

# Mock File Content
VALID_PDF_HEADER = b"%PDF-1.4\n"
MOCK_PDF_CONTENT = VALID_PDF_HEADER + b"Mock PDF content " * 100

# API Endpoints
CLINICAL_TRIALS_API_BASE = "https://clinicaltrials.gov/api/v2/studies"
GROBID_HEADER_ENDPOINT = "processHeaderDocument"
GROBID_REFERENCES_ENDPOINT = "processReferences"

# Error Messages
INVALID_PDF_ERROR = "Invalid PDF format"
FILE_NOT_FOUND_ERROR = "File not found"
SERVICE_UNAVAILABLE_ERROR = "Service temporarily unavailable"
API_QUOTA_ERROR = "API quota exceeded"
NETWORK_TIMEOUT_ERROR = "Request timed out"
MALFORMED_RESPONSE_ERROR = "Invalid response format"
RATE_LIMIT_ERROR = "Rate limit exceeded"
CONNECTION_ERROR = "Connection refused"
