from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

import duckdb


class BaseTable(ABC):
    name: str
    grain_columns: tuple[str, ...]
    publish: bool = True

    @classmethod
    @abstractmethod
    def create_sql(cls) -> str:
        raise NotImplementedError("Subclasses must implement create_sql()")

    @classmethod
    @abstractmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        """Run custom validation for the table"""
        pass

    @classmethod
    def create(cls, connection: duckdb.DuckDBPyConnection) -> None:
        connection.execute(cls.create_sql())

    @classmethod
    def validate(cls, connection: duckdb.DuckDBPyConnection) -> None:
        """Run all validations for the table"""
        cls.validate_grain(connection)
        cls.validate_custom(connection)

    @classmethod
    def validate_grain(cls, connection: duckdb.DuckDBPyConnection) -> None:
        """Validate that the table is unique across the grain"""
        if not cls.grain_columns:
            raise ValueError("Grain columns must be defined for the table")

        grain = ", ".join(cls.grain_columns)

        null_condition = " OR ".join(f"{col} IS NULL" for col in cls.grain_columns)

        null_rows = connection.execute(f"""
            SELECT {grain}
            FROM {cls.name}
            WHERE {null_condition}
            LIMIT 10
        """).fetchall()

        if null_rows:
            raise ValueError(f"Found rows with NULL values in grain columns: {null_rows}")

        duplicate_rows = connection.execute(f"""
        SELECT {grain}, COUNT(*)
        FROM {cls.name}
        GROUP BY {grain}
        HAVING COUNT(*) > 1
        LIMIT 10
        """).fetchall()

        if duplicate_rows:
            raise ValueError(f"Found duplicate rows for grain columns: {duplicate_rows}")

    @classmethod
    def export(cls, connection: duckdb.DuckDBPyConnection, output_root: Path, snapshot_date: date) -> Path | None:
        if not cls.publish:
            return None

        output_directory = output_root / cls.name / f"snapshot_date={snapshot_date.isoformat()}"
        output_directory.mkdir(parents=True, exist_ok=True)

        output_path = output_directory / "part-00000.parquet"
        temporary_path = output_directory / "part-00000.parquet.tmp"

        # Remove temporary file if it exists before creating a new one
        temporary_path.unlink(missing_ok=True)

        try:
            expected_row = connection.execute(f"SELECT COUNT(*) FROM {cls.name}").fetchone()
            if expected_row is None:
                raise RuntimeError(f"Could not read row count from {cls.name}")
            expected_row_count = expected_row[0]

            connection.execute(
                f"""
                COPY {cls.name}
                TO ?
                (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD
                )
                """,
                [str(temporary_path)],
            )

            exported_row = connection.execute(
                f"SELECT COUNT(*) FROM read_parquet(?)", [str(temporary_path)]
            ).fetchone()
            if exported_row is None:
                raise RuntimeError(f"Could not read row count from {temporary_path}")
            exported_row_count = exported_row[0]

            if exported_row_count != expected_row_count:
                raise ValueError(
                    f"{cls.name} export row count mismatch: "
                    f"expected {expected_row_count}, "
                    f"got {exported_row_count}"
                )

            temporary_path.replace(output_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        return output_path
