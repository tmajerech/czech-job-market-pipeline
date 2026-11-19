import duckdb
import pytest

from pipeline.base_table import BaseTable


class DuplicateGrainTable(BaseTable):
    name = "test_duplicate_grain"
    grain_columns = ("portal_id",)

    @classmethod
    def create_sql(cls) -> str:
        return ""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass


def test_validate_grain_rejects_duplicate_key(connection) -> None:
    connection.execute("""
        CREATE TEMP TABLE test_duplicate_grain AS
        SELECT * FROM (VALUES (42), (42)) AS rows(portal_id)
    """)

    with pytest.raises(ValueError, match="Found duplicate rows"):
        DuplicateGrainTable.validate_grain(connection)


def test_validate_grain_rejects_null_key(connection) -> None:
    connection.execute("""
        CREATE TEMP TABLE test_duplicate_grain AS
        SELECT * FROM (VALUES (NULL::INTEGER)) AS rows(portal_id)
    """)

    with pytest.raises(ValueError, match="Found rows with NULL values"):
        DuplicateGrainTable.validate_grain(connection)


def test_validate_grain_accepts_unique_keys(connection) -> None:
    connection.execute("""
        CREATE TEMP TABLE test_duplicate_grain AS
        SELECT * FROM (VALUES (42), (43)) AS rows(portal_id)
    """)

    DuplicateGrainTable.validate_grain(connection)


class MissingGrainTable(DuplicateGrainTable):
    grain_columns = ()


def test_validate_grain_requires_declared_columns(connection) -> None:
    with pytest.raises(ValueError, match="Grain columns must be defined"):
        MissingGrainTable.validate_grain(connection)
