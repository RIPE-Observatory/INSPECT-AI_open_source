"""
Simplified base mock classes for unit testing.

Provides minimal, fast mock implementations focused on behavior verification
rather than realistic responses.
"""

import time
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, Mock

from tests.unit.constants import SUCCESS_STATUS


@dataclass
class MockResponse:
    """Minimal mock response object."""

    data: Any = None
    status_code: int = SUCCESS_STATUS
    error: str | None = None

    @property
    def ok(self) -> bool:
        """Check if response is successful."""
        return self.status_code < 400


class BaseMock:
    """
    Simplified base class for service mocks.

    Focuses on call tracking and simple response simulation
    without complex behavior patterns.
    """

    def __init__(self):
        self.call_count = 0
        self.call_history: list[dict[str, Any]] = []
        self._should_error = False
        self._error_message = ""
        self._error_type = "generic"
        self._simulate_timeout = False
        self._timeout_delay = 5.0

    def reset(self):
        """Reset all mock state."""
        self.call_count = 0
        self.call_history.clear()
        self._should_error = False
        self._error_message = ""
        self._error_type = "generic"
        self._simulate_timeout = False
        self._timeout_delay = 5.0

    def setup_error(self, error_message: str, error_type: str = "generic"):
        """Setup mock to raise error on next call."""
        self._should_error = True
        self._error_message = error_message
        self._error_type = error_type

    def setup_timeout_error(self, timeout_delay: float = 5.0):
        """Setup mock to simulate network timeout."""
        self._simulate_timeout = True
        self._timeout_delay = timeout_delay

    def setup_connection_error(self):
        """Setup mock to simulate connection failures."""
        self.setup_error("Connection refused", "connection")

    def setup_rate_limit_error(self):
        """Setup mock to simulate rate limiting."""
        self.setup_error("Rate limit exceeded", "rate_limit")

    def record_call(self, method_name: str, **kwargs):
        """Record a method call and handle configured errors."""
        self.call_count += 1
        self.call_history.append(
            {"method": method_name, "timestamp": time.time(), "args": kwargs}
        )

        # Check for simulated errors
        self._check_for_errors()

    def _check_for_errors(self):
        """Check and raise any configured errors."""
        import asyncio

        # Timeout takes precedence
        if self._simulate_timeout:
            self._simulate_timeout = False  # Reset after raising
            raise asyncio.TimeoutError(
                f"Request timed out after {self._timeout_delay}s"
            )

        # Then check for other errors
        if self._should_error:
            self._should_error = False  # Reset after raising
            error_msg = self._error_message
            error_type = self._error_type

            if error_type == "connection":
                raise ConnectionError(error_msg)
            elif error_type == "rate_limit":
                raise Exception(f"HTTP 429: {error_msg}")
            else:
                raise Exception(error_msg)

    def assert_called_once(self, method_name: str):
        """Assert method was called exactly once."""
        calls = [c for c in self.call_history if c["method"] == method_name]
        assert len(calls) == 1, f"Expected 1 call to {method_name}, got {len(calls)}"

    def assert_not_called(self, method_name: str):
        """Assert method was never called."""
        calls = [c for c in self.call_history if c["method"] == method_name]
        assert len(calls) == 0, f"Expected 0 calls to {method_name}, got {len(calls)}"


class AsyncBaseMock(BaseMock):
    """Base class for async service mocks."""

    def create_simple_response(
        self, data: Any = None, status_code: int = SUCCESS_STATUS
    ) -> MockResponse:
        """Create a simple mock response."""
        return MockResponse(data=data, status_code=status_code)


def create_mock_function(
    return_value: Any = None,
    side_effect: Exception | None = None,
    is_async: bool = False,
) -> Mock | AsyncMock:
    """
    Create simple mock functions.

    Args:
        return_value: Value to return when called
        side_effect: Exception to raise when called
        is_async: Whether to create an AsyncMock
    """
    mock_class = AsyncMock if is_async else Mock
    mock_func = mock_class()

    if return_value is not None:
        mock_func.return_value = return_value

    if side_effect is not None:
        mock_func.side_effect = side_effect

    return mock_func
