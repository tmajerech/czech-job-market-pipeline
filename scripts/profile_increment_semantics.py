#!/usr/bin/env python3
"""Focused checks for the semantics and ordering of vacancy increment files."""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
from pathlib import Path

from profile_data import (
    ANALYSIS,
    INCREMENTS,
    INCREMENT_DATE_RE,
    INCREMENT_SCHEMA,
    canonical_hash,
    iter_json_array,
    numeric_summary,
)


def main() -> None:
    schema = json.loads(INCREMENT_SCHEMA.read_text(encoding="utf-8"))
    item_schema = schema["properties"]["polozky"]["items"]
    schema_fields = set(item_schema["properties"])
    observed_fields: set[str] = set()
    files = []
    previous_multiset_hash = None
    previous_date = None
    total_lags: list[float] = []
    total_lag_buckets: collections.Counter[str] = collections.Counter()
    total_same_day_duplicate_groups = 0
    total_tombstone_like_rows = 0
    total_increment_id_mismatches = 0
    histories: dict[int, list[tuple[str, dict]]] = collections.defaultdict(list)

    for path in INCREMENTS:
        file_date_text = INCREMENT_DATE_RE.search(path.name).group(1)
        file_date = dt.date.fromisoformat(file_date_text)
        rows = list(iter_json_array(path, "polozky"))
        observed_fields.update(key for row in rows for key in row)
        by_portal: dict[int, list[dict]] = collections.defaultdict(list)
        lag_by_type: dict[str, list[float]] = collections.defaultdict(list)
        lag_buckets = collections.Counter()
        required_missing_rows = 0
        tombstone_like_rows = 0
        cancelled_payload = collections.Counter()
        id_mismatches = 0

        canonical_rows = sorted(canonical_hash(row) for row in rows)
        multiset_hash = hashlib.sha256("\n".join(canonical_rows).encode("ascii")).hexdigest()

        for row in rows:
            change_type = (row.get("typZmenyOpenData") or {}).get("id", "missing")
            portal_id = row.get("portalId")
            by_portal[portal_id].append(row)
            histories[portal_id].append((file_date_text, row))
            if row.get("id") != f"VolneMistoPrirustek/{portal_id}":
                id_mismatches += 1
            if any(field not in row for field in item_schema.get("required", [])):
                required_missing_rows += 1
            if len(row) <= 5:
                tombstone_like_rows += 1

            changed = row.get("datumZmeny")
            if changed:
                lag = (file_date - dt.date.fromisoformat(changed[:10])).days
                total_lags.append(float(lag))
                lag_by_type[change_type].append(float(lag))
                if lag < 0:
                    bucket = "future"
                elif lag == 0:
                    bucket = "same_day"
                elif lag == 1:
                    bucket = "one_day_old"
                elif lag <= 7:
                    bucket = "two_to_seven_days_old"
                elif lag <= 30:
                    bucket = "eight_to_thirty_days_old"
                else:
                    bucket = "over_thirty_days_old"
                lag_buckets[bucket] += 1
                total_lag_buckets[bucket] += 1

            if change_type == "TypyZmenOpenData/zruseny":
                cancelled_payload["rows"] += 1
                cancelled_payload["pocetMist_zero"] += row.get("pocetMist") == 0
                cancelled_payload["employer_present"] += row.get("zamestnavatel") is not None
                cancelled_payload["location_present"] += row.get("mistoVykonuPrace") is not None
                cancelled_payload["profession_present"] += row.get("profeseCzIsco") is not None
                cancelled_payload["salary_from_present"] += row.get("mesicniMzdaOd") is not None

        duplicate_groups = []
        for portal_id, events in sorted(by_portal.items()):
            if len(events) > 1:
                duplicate_groups.append(
                    {
                        "portalId": portal_id,
                        "event_count": len(events),
                        "change_types_in_file_order": [
                            (event.get("typZmenyOpenData") or {}).get("id") for event in events
                        ],
                        "datumZmeny_in_file_order": [event.get("datumZmeny") for event in events],
                        "payloads_identical_excluding_change_type": len(
                            {
                                canonical_hash(
                                    {
                                        key: value
                                        for key, value in event.items()
                                        if key != "typZmenyOpenData"
                                    }
                                )
                                for event in events
                            }
                        )
                        == 1,
                    }
                )

        total_same_day_duplicate_groups += len(duplicate_groups)
        total_tombstone_like_rows += tombstone_like_rows
        total_increment_id_mismatches += id_mismatches
        files.append(
            {
                "date": file_date_text,
                "rows": len(rows),
                "datum_zmeny_lag_days": numeric_summary([float(value) for values in lag_by_type.values() for value in values]),
                "datum_zmeny_lag_buckets": dict(lag_buckets),
                "lag_summary_by_change_type": {
                    key: numeric_summary(values) for key, values in sorted(lag_by_type.items())
                },
                "same_portal_id_groups": len(duplicate_groups),
                "same_portal_id_extra_rows": sum(item["event_count"] - 1 for item in duplicate_groups),
                "same_portal_id_examples": duplicate_groups[:5],
                "required_field_missing_rows": required_missing_rows,
                "tombstone_like_rows": tombstone_like_rows,
                "cancelled_payload": dict(cancelled_payload),
                "increment_id_mismatches": id_mismatches,
                "canonical_record_multiset_sha256": multiset_hash,
                "same_record_multiset_as_previous_file": multiset_hash == previous_multiset_hash,
                "previous_file_date": previous_date,
            }
        )
        previous_multiset_hash = multiset_hash
        previous_date = file_date_text

    identity_variation = {}
    for label, extractor in {
        "referencniCislo": lambda row: row.get("referencniCislo"),
        "datumVlozeni": lambda row: row.get("datumVlozeni"),
        "employer_ico": lambda row: (row.get("zamestnavatel") or {}).get("ico"),
        "profession_czisco": lambda row: (row.get("profeseCzIsco") or {}).get("id"),
    }.items():
        varying = []
        for portal_id, events in sorted(histories.items()):
            values = {extractor(row) for _, row in events}
            if len(values) > 1:
                varying.append(
                    {
                        "portalId": portal_id,
                        "values": sorted(values, key=lambda value: str(value)),
                        "events": [
                            {
                                "file_date": file_date,
                                "change_type": (row.get("typZmenyOpenData") or {}).get("id"),
                                "datumZmeny": row.get("datumZmeny"),
                                "value": extractor(row),
                            }
                            for file_date, row in events
                        ],
                    }
                )
        identity_variation[label] = {
            "portal_ids_with_multiple_values": len(varying),
            "examples": varying[:5],
        }

    output = {
        "schema_fields_not_observed": sorted(schema_fields - observed_fields),
        "observed_fields_not_in_schema": sorted(observed_fields - schema_fields),
        "schema_change_field": "typyZmenOpenData",
        "observed_change_field": "typZmenyOpenData",
        "overall_datum_zmeny_lag_days": numeric_summary(total_lags),
        "overall_datum_zmeny_lag_buckets": dict(total_lag_buckets),
        "same_portal_id_groups_across_files": total_same_day_duplicate_groups,
        "tombstone_like_rows": total_tombstone_like_rows,
        "increment_id_mismatches": total_increment_id_mismatches,
        "identity_field_variation_across_files": identity_variation,
        "files": files,
    }
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "increment-semantics.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: output[key] for key in list(output)[:7]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
