import pyarrow as pa


VACANCY_SCHEMA = pa.schema(
    [
        pa.field("snapshot_date", pa.date32(), nullable=False),
        pa.field("portal_id", pa.int64(), nullable=False),
        pa.field("source_id", pa.string(), nullable=False),
        pa.field("reference_number", pa.string()),
        pa.field("title", pa.string()),
        pa.field("created_at", pa.timestamp("ms", tz="UTC")),
        pa.field("updated_at", pa.timestamp("ms", tz="UTC")),
        pa.field("positions_count", pa.int32()),
        pa.field("weekly_hours", pa.float64()),
        pa.field("salary_from", pa.float64()),
        pa.field("salary_to", pa.float64()),
        pa.field("employer_ico", pa.string()),
        pa.field("employer_name", pa.string()),
        pa.field("cz_isco_id", pa.string()),
    ]
)
