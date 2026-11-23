"""Generate the portfolio chart from published Gold vacancy events."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path
import re

import duckdb

from pipeline.snapshot_publish import snapshot_is_incomplete


PARTITION_PATTERN = re.compile(r"snapshot_date=(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class OccupationChange:
    occupation_code: str
    occupation_name: str
    new_count: int
    removed_count: int

    @property
    def activity(self) -> int:
        return self.new_count + self.removed_count


def _partition_file(gold_root: Path, table_name: str, snapshot_date: date) -> Path:
    return (
        gold_root
        / table_name
        / f"snapshot_date={snapshot_date.isoformat()}"
        / "part-00000.parquet"
    )


def latest_readable_event_snapshot(gold_root: Path) -> date:
    event_root = gold_root / "fact_vacancy_event"
    candidates: list[date] = []

    for parquet_path in event_root.glob("snapshot_date=*/part-*.parquet"):
        match = PARTITION_PATTERN.fullmatch(parquet_path.parent.name)
        if match:
            snapshot_date = date.fromisoformat(match.group(1))
            if not snapshot_is_incomplete(gold_root, snapshot_date):
                candidates.append(snapshot_date)

    if not candidates:
        raise FileNotFoundError(f"No readable Gold event snapshots found under {event_root}")

    return max(candidates)


def load_occupation_changes(
    gold_root: Path,
    top_n: int = 10,
) -> tuple[date, date, list[OccupationChange]]:
    """Load the most active occupations from the latest readable event interval."""
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    snapshot_date = latest_readable_event_snapshot(gold_root)
    event_path = _partition_file(gold_root, "fact_vacancy_event", snapshot_date)

    with duckdb.connect(":memory:") as connection:
        previous_dates = connection.execute(
            """
            SELECT DISTINCT previous_snapshot_date
            FROM read_parquet(?)
            """,
            [str(event_path)],
        ).fetchall()

        if len(previous_dates) != 1 or previous_dates[0][0] is None:
            raise ValueError(
                f"Expected one previous snapshot date in {event_path}, got {previous_dates}"
            )

        previous_snapshot_date = previous_dates[0][0]
        if snapshot_is_incomplete(gold_root, previous_snapshot_date):
            raise RuntimeError(
                f"Gold snapshot {previous_snapshot_date} has an incomplete publication marker"
            )

        current_fact_path = _partition_file(
            gold_root, "fact_vacancy_snapshot", snapshot_date
        )
        previous_fact_path = _partition_file(
            gold_root, "fact_vacancy_snapshot", previous_snapshot_date
        )
        current_occupation_path = _partition_file(
            gold_root, "dim_occupation", snapshot_date
        )
        previous_occupation_path = _partition_file(
            gold_root, "dim_occupation", previous_snapshot_date
        )

        required_paths = (
            current_fact_path,
            previous_fact_path,
            current_occupation_path,
            previous_occupation_path,
        )
        missing_paths = [str(path) for path in required_paths if not path.is_file()]
        if missing_paths:
            raise FileNotFoundError(f"Missing Gold inputs: {missing_paths}")

        rows = connection.execute(
            """
            WITH event_vacancies AS (
                SELECT
                    event.event_type,
                    vacancy.occupation_id
                FROM read_parquet(?) AS event
                INNER JOIN read_parquet(?) AS vacancy
                    ON vacancy.portal_id = event.portal_id
                    AND vacancy.snapshot_date = CASE
                        WHEN event.event_type = 'NEW' THEN event.snapshot_date
                        WHEN event.event_type = 'REMOVED'
                            THEN event.previous_snapshot_date
                    END
            ),
            occupation_counts AS (
                SELECT
                    occupation_id,
                    COUNT(*) FILTER (WHERE event_type = 'NEW') AS new_count,
                    COUNT(*) FILTER (WHERE event_type = 'REMOVED') AS removed_count
                FROM event_vacancies
                GROUP BY occupation_id
            ),
            current_occupations AS (
                SELECT occupation_id, occupation_code, occupation_name
                FROM read_parquet(?)
            ),
            previous_occupations AS (
                SELECT occupation_id, occupation_code, occupation_name
                FROM read_parquet(?)
            )
            SELECT
                COALESCE(
                    current.occupation_code,
                    previous.occupation_code,
                    counts.occupation_id
                ),
                COALESCE(current.occupation_name, previous.occupation_name),
                counts.new_count,
                counts.removed_count
            FROM occupation_counts AS counts
            LEFT JOIN current_occupations AS current
                USING (occupation_id)
            LEFT JOIN previous_occupations AS previous
                USING (occupation_id)
            WHERE COALESCE(current.occupation_name, previous.occupation_name) IS NOT NULL
            ORDER BY
                counts.new_count + counts.removed_count DESC,
                COALESCE(current.occupation_code, previous.occupation_code)
            LIMIT ?
            """,
            [
                str(event_path),
                [str(current_fact_path), str(previous_fact_path)],
                str(current_occupation_path),
                str(previous_occupation_path),
                top_n,
            ],
        ).fetchall()

    changes = [
        OccupationChange(
            occupation_code=occupation_code,
            occupation_name=" ".join(occupation_name.split()),
            new_count=new_count,
            removed_count=removed_count,
        )
        for occupation_code, occupation_name, new_count, removed_count in rows
    ]
    if not changes:
        raise ValueError(f"No occupation changes found in {event_path}")

    return snapshot_date, previous_snapshot_date, changes


def _truncate(text: str, limit: int = 50) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _format_date(value: date) -> str:
    return value.isoformat()


def render_svg(
    snapshot_date: date,
    previous_snapshot_date: date,
    changes: list[OccupationChange],
) -> str:
    """Render a dependency-free, README-friendly diverging bar chart."""
    width = 1200
    margin_left = 390
    plot_width = 730
    zero_x = margin_left + plot_width // 2
    half_width = plot_width // 2 - 35
    row_height = 48
    chart_top = 164
    height = chart_top + len(changes) * row_height + 82
    max_count = max(max(change.new_count, change.removed_count) for change in changes)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Vacancy listing turnover by occupation</title>',
        '<desc id="desc">New and removed vacancy listings between the two '
        "latest completed Gold snapshots.</desc>",
        '<rect width="1200" height="100%" rx="18" fill="#f8fafc"/>',
        '<text x="48" y="54" font-family="Arial" font-size="26" '
        'font-weight="700" fill="#0f172a">Vacancy listing turnover by occupation</text>',
        f'<text x="48" y="84" font-family="Arial" font-size="16" '
        f'fill="#475569">{escape(_format_date(previous_snapshot_date))} → '
        f'{escape(_format_date(snapshot_date))} · top {len(changes)} by NEW + REMOVED events</text>',
        '<rect x="48" y="112" width="14" height="14" rx="3" fill="#ef6a67"/>',
        '<text x="70" y="124" font-family="Arial" font-size="14" '
        'fill="#334155">REMOVED</text>',
        '<rect x="176" y="112" width="14" height="14" rx="3" fill="#16a67a"/>',
        '<text x="198" y="124" font-family="Arial" font-size="14" '
        'fill="#334155">NEW</text>',
        f'<line x1="{zero_x}" y1="142" x2="{zero_x}" y2="{height - 54}" '
        'stroke="#94a3b8" stroke-width="1"/>',
    ]

    for index, change in enumerate(changes):
        y = chart_top + index * row_height
        removed_width = round(change.removed_count / max_count * half_width)
        new_width = round(change.new_count / max_count * half_width)
        label = escape(_truncate(change.occupation_name))
        code = escape(change.occupation_code)

        parts.extend(
            [
                f'<text x="48" y="{y + 17}" font-family="Arial" '
                f'font-size="15" font-weight="600" fill="#0f172a">{label}</text>',
                f'<text x="48" y="{y + 35}" font-family="Menlo" '
                f'font-size="12" fill="#64748b">CZ-ISCO {code}</text>',
                f'<rect x="{zero_x - removed_width}" y="{y + 5}" '
                f'width="{removed_width}" height="26" rx="4" fill="#ef6a67"/>',
                f'<rect x="{zero_x}" y="{y + 5}" width="{new_width}" height="26" '
                'rx="4" fill="#16a67a"/>',
                f'<text x="{zero_x - removed_width - 9}" y="{y + 24}" '
                'text-anchor="end" font-family="Arial" font-size="13" '
                f'font-weight="700" fill="#9f3537">{change.removed_count}</text>',
                f'<text x="{zero_x + new_width + 9}" y="{y + 24}" '
                'font-family="Arial" font-size="13" font-weight="700" '
                f'fill="#08775a">{change.new_count}</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="48" y="{height - 26}" font-family="Arial" '
            'font-size="12" fill="#64748b">Source: Czech MPSV · aggregated from '
            'Gold Parquet tables with DuckDB</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def generate_chart(gold_root: Path, output_path: Path, top_n: int = 10) -> None:
    snapshot_date, previous_snapshot_date, changes = load_occupation_changes(
        gold_root, top_n
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_svg(snapshot_date, previous_snapshot_date, changes), encoding="utf-8"
    )

    print(
        f"Generated {output_path} from Gold interval "
        f"{previous_snapshot_date} -> {snapshot_date}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold-root",
        type=Path,
        default=Path("s3_doppelganger/gold/mpsv"),
        help="Gold root (default: s3_doppelganger/gold/mpsv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../docs/assets/vacancy-changes-by-occupation.svg"),
        help="SVG output path",
    )
    parser.add_argument("--top", type=int, default=10, help="Number of occupations")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    generate_chart(arguments.gold_root, arguments.output, arguments.top)
