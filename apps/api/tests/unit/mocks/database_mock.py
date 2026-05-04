"""
Mock implementation for database operations.

Provides in-memory simulation of SQLAlchemy operations
without requiring a real database connection.
"""

import uuid
from collections import defaultdict
from typing import Any
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from .base import AsyncBaseMock


class DatabaseMock(AsyncBaseMock):
    """Mock for SQLAlchemy AsyncSession and database operations."""

    def __init__(self):
        super().__init__()
        self._tables: dict[str, dict[str, Any]] = defaultdict(dict)
        self._session_state = "open"
        self._transaction_active = False

    def reset(self):
        """Reset all mock state including database tables."""
        super().reset()
        self.reset_tables()
        self._session_state = "open"
        self._transaction_active = False

    def reset_tables(self):
        """Clear all mock table data."""
        self._tables.clear()

    def add_record(self, table_name: str, record_id: str, data: dict[str, Any]):
        """Add a record to a mock table."""
        self._tables[table_name][record_id] = data.copy()

    def get_record(self, table_name: str, record_id: str) -> dict[str, Any] | None:
        """Get a record from a mock table."""
        return self._tables[table_name].get(record_id)

    def list_records(self, table_name: str) -> list[dict[str, Any]]:
        """List all records in a mock table."""
        return list(self._tables[table_name].values())

    def create_mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)

        # Mock basic session operations
        session.add = Mock(side_effect=self._mock_add)
        session.get = AsyncMock(side_effect=self._mock_get)
        session.execute = AsyncMock(side_effect=self._mock_execute)
        session.commit = AsyncMock(side_effect=self._mock_commit)
        session.rollback = AsyncMock(side_effect=self._mock_rollback)
        session.close = AsyncMock(side_effect=self._mock_close)
        session.flush = AsyncMock(side_effect=self._mock_flush)
        session.refresh = AsyncMock(side_effect=self._mock_refresh)

        # Mock session state properties
        session.is_active = True
        session.dirty = set()
        session.new = set()
        session.deleted = set()

        return session

    def _mock_add(self, instance):
        """Mock session.add()."""
        self.record_call("add", instance=instance)

        # Extract table name and ID from instance
        table_name = instance.__class__.__name__.lower()
        record_id = getattr(instance, "id", str(uuid.uuid4()))

        # Convert instance to dict for storage
        data = {}
        for attr_name in dir(instance):
            if not attr_name.startswith("_") and not callable(
                getattr(instance, attr_name)
            ):
                data[attr_name] = getattr(instance, attr_name)

        self.add_record(table_name, str(record_id), data)

    async def _mock_get(self, model_class: type, primary_key: Any):
        """Mock session.get()."""
        self.record_call("get", model_class=model_class, primary_key=primary_key)

        table_name = model_class.__name__.lower()
        record = self.get_record(table_name, str(primary_key))

        if record:
            # Create a mock instance with the stored data
            instance = Mock()
            for key, value in record.items():
                setattr(instance, key, value)
            return instance

        return None

    async def _mock_execute(self, statement):
        """Mock session.execute()."""
        self.record_call("execute", statement=statement)

        # Create a mock result
        result = Mock()
        result.fetchall = Mock(return_value=[])
        result.fetchone = Mock(return_value=None)
        result.scalar = Mock(return_value=None)
        result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        return result

    async def _mock_commit(self):
        """Mock session.commit()."""
        self.record_call("commit")
        self._transaction_active = False

    async def _mock_rollback(self):
        """Mock session.rollback()."""
        self.record_call("rollback")
        self._transaction_active = False

    async def _mock_close(self):
        """Mock session.close()."""
        self.record_call("close")
        self._session_state = "closed"

    async def _mock_flush(self):
        """Mock session.flush()."""
        self.record_call("flush")

    async def _mock_refresh(self, instance):
        """Mock session.refresh()."""
        self.record_call("refresh", instance=instance)


class MockQueryResult:
    """Mock for SQLAlchemy query results."""

    def __init__(self, data: list[dict[str, Any]]):
        self.data = data
        self._index = 0

    def fetchall(self) -> list[dict[str, Any]]:
        """Return all results."""
        return self.data

    def fetchone(self) -> dict[str, Any] | None:
        """Return the next result."""
        if self._index < len(self.data):
            result = self.data[self._index]
            self._index += 1
            return result
        return None

    def scalar(self) -> Any:
        """Return the first column of the first row."""
        if self.data and len(self.data[0]) > 0:
            first_row = self.data[0]
            return list(first_row.values())[0]
        return None


def create_database_mock() -> DatabaseMock:
    """Factory function to create a configured database mock."""
    return DatabaseMock()


def create_mock_session_factory(db_mock: DatabaseMock):
    """Create a mock session factory that returns mock sessions."""

    def mock_factory():
        return db_mock.create_mock_session()

    return mock_factory
