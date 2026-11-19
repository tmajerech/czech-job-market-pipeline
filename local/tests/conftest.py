import duckdb
import pytest


@pytest.fixture
def connection():
    connection = duckdb.connect(":memory:")
    yield connection
    connection.close()
