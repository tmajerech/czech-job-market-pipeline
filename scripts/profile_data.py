#!/usr/bin/env python3
"""Profile the downloaded MPSV samples without loading the large JSON files at once."""

from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterator, TextIO

try:
    import jsonschema
except ImportError:  # pragma: no cover - the script remains useful without it
    jsonschema = None


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ANALYSIS = ROOT / "analysis"
FULL = RAW / "vacancies" / "full" / "volna-mista-retrieved-2026-10-03.json.gz"
INCREMENTS = sorted((RAW / "vacancies" / "increments").glob("*.json.gz"))
VACANCY_SCHEMA = RAW / "vacancies" / "schema" / "volna-mista.schema.json"
INCREMENT_SCHEMA = RAW / "vacancies" / "schema" / "volna-mista-prirustek.schema.json"
PNO = RAW / "unemployment" / "podil-nezamestnanych-osob-adresa-retrieved-2026-10-03.json"
PNO_SCHEMA = RAW / "unemployment" / "podil-nezamestnanych-osob-adresa.schema.json"
OLD_UNEMPLOYMENT = RAW / "unemployment" / "uchazeci-a-volna-mista-12-2024.json.gz"

INCREMENT_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

CODELIST_BY_PREFIX = {
    "CastObce": "casti-obci",
    "CzIsco": "cz-isco",
    "Dovednost": "dovednosti",
    "Jazyk": "jazyky",
    "KontaktniPracoviste": "kontaktni-pracoviste",
    "Kraj": "kraje",
    "MestskyObvodMestskaCast": "mestske-obvody-mestske-casti",
    "MestskyObvodVPraze": "mestske-obvody-v-praze",
    "Obec": "obce",
    "Okres": "okresy",
    "PracovnepravniVztah": "pracovnepravni-vztahy",
    "Smennost": "smennosti",
    "TypMistaVykonuPrace": "typy-mista-vykonu-prace",
    "TypMzdy": "typy-mzdy",
    "TypStavebnihoObjektu": "typy-stavebniho-objektu",
    "TypyZmenOpenData": "typy-zmen-opendata",
    "UrovenZnalostiJazyka": "urovne-znalosti-jazyka",
    "VhodnostProTypZamestnance": "vhodnosti-pro-typ-zamestnance",
    "VyhodyVolnehoMista": "vyhody-volneho-mista",
    "VzdelaniDetailniKategorie": "vzdelani-detailni-kategorie",
    "VzdelaniKkov": "vzdelani-kkov",
    "ZverejnovatVpm": "zverejnovat-vpm",
}


def open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("rt", encoding="utf-8")


def iter_json_array(path: Path, array_key: str | None = None) -> Iterator[Any]:
    """Stream values from either a top-level array or an array under a known key."""
    decoder = json.JSONDecoder()
    with open_text(path) as handle:
        buffer = ""
        eof = False

        if array_key is None:
            marker = "["
        else:
            marker = f'"{array_key}"'

        while marker not in buffer:
            chunk = handle.read(65536)
            if not chunk:
                raise ValueError(f"Could not find {marker!r} in {path}")
            buffer += chunk

        if array_key is None:
            pos = buffer.index("[") + 1
        else:
            key_pos = buffer.index(marker) + len(marker)
            while "[" not in buffer[key_pos:]:
                chunk = handle.read(65536)
                if not chunk:
                    raise ValueError(f"Could not find array for {array_key!r} in {path}")
                buffer += chunk
            pos = buffer.index("[", key_pos) + 1

        while True:
            while True:
                while pos < len(buffer) and buffer[pos] in " \t\r\n,":
                    pos += 1
                if pos < len(buffer) or eof:
                    break
                buffer = ""
                pos = 0
                chunk = handle.read(65536)
                if chunk:
                    buffer += chunk
                else:
                    eof = True

            if pos < len(buffer) and buffer[pos] == "]":
                return
            if eof and pos >= len(buffer):
                raise ValueError(f"Unexpected EOF while reading {path}")

            while True:
                try:
                    value, end = decoder.raw_decode(buffer, pos)
                    yield value
                    pos = end
                    break
                except json.JSONDecodeError:
                    if eof:
                        raise
                    if pos:
                        buffer = buffer[pos:]
                        pos = 0
                    chunk = handle.read(65536)
                    if chunk:
                        buffer += chunk
                    else:
                        eof = True

            if pos > 1_000_000:
                buffer = buffer[pos:]
                pos = 0


def json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def uncompressed_size(path: Path) -> int:
    if path.suffix != ".gz":
        return path.stat().st_size
    total = 0
    with gzip.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            total += len(chunk)
    return total


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def numeric_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "p01": percentile(values, 0.01),
        "p25": percentile(values, 0.25),
        "median": percentile(values, 0.5),
        "p75": percentile(values, 0.75),
        "p99": percentile(values, 0.99),
        "max": max(values),
    }


def collect_ids(value: Any, output: collections.Counter[str]) -> None:
    if isinstance(value, dict):
        identifier = value.get("id")
        if isinstance(identifier, str) and "/" in identifier:
            output[identifier] += 1
        for child in value.values():
            collect_ids(child, output)
    elif isinstance(value, list):
        for child in value:
            collect_ids(child, output)


def load_codelists() -> tuple[dict[str, set[str]], dict[str, Any]]:
    ids_by_prefix: dict[str, set[str]] = {}
    profiles: dict[str, Any] = {}
    for prefix, filename in CODELIST_BY_PREFIX.items():
        path = RAW / "codelists" / f"{filename}.json.gz"
        rows = list(iter_json_array(path, "polozky"))
        identifiers = [row.get("id") for row in rows]
        ids_by_prefix[prefix] = {item for item in identifiers if isinstance(item, str)}
        codes = [row.get("kod") for row in rows if row.get("kod") is not None]
        profiles[filename] = {
            "row_count": len(rows),
            "id_nulls": sum(item is None for item in identifiers),
            "id_distinct": len(set(identifiers)),
            "id_duplicates": len(identifiers) - len(set(identifiers)),
            "code_distinct": len(set(map(str, codes))),
        }
    return ids_by_prefix, profiles


def top_level_stats(
    rows: Iterator[dict[str, Any]], expected_fields: list[str] | None = None
) -> tuple[int, dict[str, Any], list[dict[str, Any]]]:
    count = 0
    presence: collections.Counter[str] = collections.Counter()
    nulls: collections.Counter[str] = collections.Counter()
    types: dict[str, set[str]] = collections.defaultdict(set)
    retained: list[dict[str, Any]] = []
    for row in rows:
        count += 1
        retained.append(row)
        for field, value in row.items():
            presence[field] += 1
            if value is None:
                nulls[field] += 1
            types[field].add(json_type(value))
    fields = sorted(set(expected_fields or []) | set(presence))
    result = {}
    for field in fields:
        missing = count - presence[field]
        result[field] = {
            "present": presence[field],
            "missing": missing,
            "null": nulls[field],
            "missing_or_null": missing + nulls[field],
            "null_pct": round((missing + nulls[field]) * 100 / count, 4) if count else None,
            "observed_types": sorted(types[field]),
        }
    return count, result, retained


def validate_rows(
    rows: list[dict[str, Any]], schema: dict[str, Any]
) -> dict[str, Any]:
    if jsonschema is None:
        return {"available": False, "reason": "jsonschema is not installed"}
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
    except Exception as exc:
        return {"available": True, "schema_valid": False, "error": str(exc)}

    invalid_rows = 0
    error_count = 0
    examples: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        errors = list(validator.iter_errors(row))
        if errors:
            invalid_rows += 1
            error_count += len(errors)
            for error in errors[: max(0, 10 - len(examples))]:
                examples.append(
                    {
                        "row_index": index,
                        "path": ".".join(map(str, error.absolute_path)),
                        "message": error.message,
                    }
                )
    return {
        "available": True,
        "schema_valid": True,
        "rows_checked": len(rows),
        "invalid_rows": invalid_rows,
        "error_count": error_count,
        "examples": examples,
    }


def profile_full_vacancies(
    codelist_ids: dict[str, set[str]], codelist_profiles: dict[str, Any]
) -> tuple[dict[str, Any], dict[int, dict[str, Any]], set[str]]:
    schema = json.loads(VACANCY_SCHEMA.read_text(encoding="utf-8"))
    item_schema = schema["properties"]["polozky"]["items"]
    schema_fields = list(item_schema["properties"])
    row_count, fields, rows = top_level_stats(iter_json_array(FULL, "polozky"), schema_fields)

    identifiers: dict[str, collections.Counter[Any]] = {
        field: collections.Counter(row.get(field) for row in rows)
        for field in ("portalId", "id", "referencniCislo")
    }
    record_hashes = collections.Counter(canonical_hash(row) for row in rows)
    id_refs: collections.Counter[str] = collections.Counter()
    for row in rows:
        collect_ids(row, id_refs)

    prefix_counts: collections.Counter[str] = collections.Counter()
    unresolved_by_prefix: dict[str, list[str]] = {}
    observed_by_prefix: dict[str, set[str]] = collections.defaultdict(set)
    for identifier, count in id_refs.items():
        prefix = identifier.split("/", 1)[0]
        prefix_counts[prefix] += count
        observed_by_prefix[prefix].add(identifier)
    for prefix, observed in observed_by_prefix.items():
        if prefix in codelist_ids:
            unresolved_by_prefix[prefix] = sorted(observed - codelist_ids[prefix])

    array_fields = [
        "pracovnePravniVztahy",
        "vhodnostiPracovnihoMista",
        "vyhodyVolnehoMista",
        "pozadovanaDovednost",
        "pozadovanaJazykovaZnalost",
        "pozadovanePovolani",
        "pozadovaneVzdelani",
    ]
    arrays = {}
    for field in array_fields:
        lengths = [len(row[field]) for row in rows if isinstance(row.get(field), list)]
        arrays[field] = {
            "null": sum(row.get(field) is None for row in rows),
            "empty": sum(isinstance(row.get(field), list) and not row[field] for row in rows),
            "nonempty": sum(isinstance(row.get(field), list) and bool(row[field]) for row in rows),
            "total_elements": sum(lengths),
            "max_elements_per_record": max(lengths, default=0),
        }

    salary_by_type: dict[str, dict[str, list[float]]] = collections.defaultdict(
        lambda: {"from": [], "to": []}
    )
    salary_invalid_examples: list[dict[str, Any]] = []
    salary_counts = collections.Counter()
    for row in rows:
        lower = row.get("mesicniMzdaOd")
        upper = row.get("mesicniMzdaDo")
        salary_type = (row.get("typMzdy") or {}).get("id", "null")
        if lower is None:
            salary_counts["from_null"] += 1
        else:
            salary_by_type[salary_type]["from"].append(float(lower))
            if lower <= 0:
                salary_counts["from_nonpositive"] += 1
        if upper is None:
            salary_counts["to_null"] += 1
        else:
            salary_by_type[salary_type]["to"].append(float(upper))
            if upper <= 0:
                salary_counts["to_nonpositive"] += 1
        if lower is None and upper is None:
            salary_counts["both_null"] += 1
        if lower is not None and upper is not None and lower > upper:
            salary_counts["from_gt_to"] += 1
            if len(salary_invalid_examples) < 10:
                salary_invalid_examples.append(
                    {"portalId": row.get("portalId"), "from": lower, "to": upper, "type": salary_type}
                )

    locations = collections.Counter()
    municipality_ids: set[str] = set()
    district_ids: set[str] = set()
    region_ids: set[str] = set()
    address_codes: set[int] = set()
    for row in rows:
        place = row.get("mistoVykonuPrace")
        if not isinstance(place, dict):
            locations["place_null"] += 1
            continue
        locations["place_present"] += 1
        workplaces = place.get("pracoviste")
        if isinstance(workplaces, list):
            locations["workplace_elements"] += len(workplaces)
            locations["records_with_workplaces"] += 1 if workplaces else 0
            for workplace in workplaces:
                address = workplace.get("adresa") if isinstance(workplace, dict) else None
                if not isinstance(address, dict):
                    locations["workplace_address_null"] += 1
                    continue
                locations["workplace_addresses"] += 1
                for key, target in (("obec", municipality_ids), ("okres", district_ids), ("kraj", region_ids)):
                    identifier = (address.get(key) or {}).get("id")
                    if identifier:
                        target.add(identifier)
                if address.get("kodAdresnihoMista") is not None:
                    address_codes.add(address["kodAdresnihoMista"])
        municipality = (place.get("obec") or {}).get("id")
        if municipality:
            municipality_ids.add(municipality)
            locations["records_with_direct_municipality"] += 1
        districts = place.get("okresy")
        if isinstance(districts, list):
            for district in districts:
                identifier = district.get("id") if isinstance(district, dict) else None
                if identifier:
                    district_ids.add(identifier)
            if districts:
                locations["records_with_district_list"] += 1
        if place.get("adresaText"):
            locations["records_with_free_text_address"] += 1

    employer_icos = [
        row["zamestnavatel"].get("ico")
        for row in rows
        if isinstance(row.get("zamestnavatel"), dict)
    ]
    malformed_icos = sorted(
        {
            ico
            for ico in employer_icos
            if ico is not None and (not isinstance(ico, str) or re.fullmatch(r"\d{8}", ico) is None)
        }
    )
    czisco_ids = [(row.get("profeseCzIsco") or {}).get("id") for row in rows]
    czisco_codes = [identifier.split("/", 1)[1] for identifier in czisco_ids if identifier]

    date_fields = ["datumVlozeni", "datumZmeny", "terminZahajeniPracovnihoPomeru", "terminUkonceniPracovnihoPomeru", "expirace"]
    date_ranges = {}
    for field in date_fields:
        values = [row.get(field) for row in rows if row.get(field)]
        date_ranges[field] = {"non_null": len(values), "min_lexical": min(values, default=None), "max_lexical": max(values, default=None)}

    snapshot_by_portal = {row["portalId"]: row for row in rows if row.get("portalId") is not None}
    result = {
        "file": str(FULL.relative_to(ROOT)),
        "row_count": row_count,
        "schema_fields": schema_fields,
        "observed_fields": sorted({key for row in rows for key in row}),
        "field_profile": fields,
        "identifiers": {
            field: {
                "null": counter.get(None, 0),
                "distinct_non_null": len(counter) - (1 if None in counter else 0),
                "duplicate_rows": sum(count - 1 for value, count in counter.items() if value is not None and count > 1),
                "duplicate_values_sample": [
                    {"value": value, "count": count}
                    for value, count in counter.most_common()
                    if value is not None and count > 1
                ][:10],
            }
            for field, counter in identifiers.items()
        },
        "exact_duplicate_rows": sum(count - 1 for count in record_hashes.values() if count > 1),
        "schema_validation": validate_rows(rows, item_schema),
        "reference_prefix_occurrences": dict(sorted(prefix_counts.items())),
        "codelist_join_coverage": {
            prefix: {
                "observed_distinct": len(observed_by_prefix[prefix]),
                "unresolved_distinct": len(unresolved),
                "unresolved_sample": unresolved[:10],
            }
            for prefix, unresolved in sorted(unresolved_by_prefix.items())
        },
        "codelists": codelist_profiles,
        "arrays": arrays,
        "salary": {
            "counts": dict(salary_counts),
            "invalid_range_examples": salary_invalid_examples,
            "by_type": {
                salary_type: {
                    "from": numeric_summary(values["from"]),
                    "to": numeric_summary(values["to"]),
                }
                for salary_type, values in sorted(salary_by_type.items())
            },
        },
        "geography": {
            **dict(locations),
            "distinct_municipality_ids": len(municipality_ids),
            "distinct_district_ids": len(district_ids),
            "distinct_region_ids": len(region_ids),
            "distinct_address_place_codes": len(address_codes),
        },
        "profession": {
            "null_czisco_id": sum(identifier is None for identifier in czisco_ids),
            "distinct_czisco_id": len(set(czisco_ids) - {None}),
            "code_length_counts": dict(sorted(collections.Counter(map(len, czisco_codes)).items())),
            "unresolved_czisco_ids": sorted(set(czisco_ids) - {None} - codelist_ids["CzIsco"])[:20],
        },
        "employer": {
            "employer_null": sum(row.get("zamestnavatel") is None for row in rows),
            "ico_null": sum(ico is None for ico in employer_icos),
            "distinct_ico": len(set(employer_icos) - {None}),
            "malformed_ico_distinct": len(malformed_icos),
            "malformed_ico_sample": malformed_icos[:20],
        },
        "date_ranges": date_ranges,
        "basic_anomalies": {
            "pocet_mist_nonpositive": sum((row.get("pocetMist") or 0) <= 0 for row in rows),
            "hours_nonpositive": sum(row.get("pocetHodinTydne") is not None and row["pocetHodinTydne"] <= 0 for row in rows),
            "hours_gt_168": sum(row.get("pocetHodinTydne") is not None and row["pocetHodinTydne"] > 168 for row in rows),
            "id_portal_mismatch": sum(row.get("id") != f"VolneMisto/{row.get('portalId')}" for row in rows),
        },
    }
    return result, snapshot_by_portal, municipality_ids


def stripped_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {"id", "typZmenyOpenData"}}


def top_level_diff(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    keys = set(before) | set(after)
    return sorted(key for key in keys if before.get(key) != after.get(key) and key not in {"id", "typZmenyOpenData"})


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    row = event["row"]
    return {
        "file_date": event["file_date"],
        "change_type": event["change_type"],
        "datumVlozeni": row.get("datumVlozeni"),
        "datumZmeny": row.get("datumZmeny"),
        "profession": (row.get("pozadovanaProfese") or {}).get("cs"),
        "salary_from": row.get("mesicniMzdaOd"),
        "salary_to": row.get("mesicniMzdaDo"),
        "places": row.get("pocetMist"),
    }


def profile_increments(
    snapshot_by_portal: dict[int, dict[str, Any]], codelist_ids: dict[str, set[str]]
) -> dict[str, Any]:
    schema = json.loads(INCREMENT_SCHEMA.read_text(encoding="utf-8"))
    item_schema = schema["properties"]["polozky"]["items"]
    schema_fields = set(item_schema["properties"])
    histories: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    file_profiles: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    refs: collections.Counter[str] = collections.Counter()

    previous_ids: set[int] | None = None
    for path in INCREMENTS:
        file_date = INCREMENT_DATE_RE.search(path.name).group(1)
        rows = list(iter_json_array(path, "polozky"))
        all_rows.extend(rows)
        ids = [row.get("portalId") for row in rows]
        types = collections.Counter((row.get("typZmenyOpenData") or {}).get("id") for row in rows)
        completeness: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
        for row in rows:
            collect_ids(row, refs)
            change_type = (row.get("typZmenyOpenData") or {}).get("id")
            for field in schema_fields:
                if field not in row:
                    completeness[change_type][f"missing::{field}"] += 1
                elif row[field] is None:
                    completeness[change_type][f"null::{field}"] += 1
            if row.get("portalId") is not None:
                histories[row["portalId"]].append(
                    {"file_date": file_date, "change_type": change_type, "row": row}
                )

        raw_hash = sha256_file(path)
        with gzip.open(path, "rb") as handle:
            content_hash = hashlib.sha256(handle.read()).hexdigest()
        id_set = {identifier for identifier in ids if identifier is not None}
        file_profiles.append(
            {
                "file": str(path.relative_to(ROOT)),
                "date": file_date,
                "rows": len(rows),
                "change_types": dict(sorted(types.items(), key=lambda pair: str(pair[0]))),
                "portal_id_nulls": ids.count(None),
                "portal_id_distinct": len(id_set),
                "portal_id_duplicate_rows": len(ids) - ids.count(None) - len(id_set),
                "exact_duplicate_rows": len(rows) - len({canonical_hash(row) for row in rows}),
                "compressed_sha256": raw_hash,
                "uncompressed_sha256": content_hash,
                "overlap_with_previous_file": len(id_set & previous_ids) if previous_ids is not None else None,
                "completeness_by_type": {key: dict(value) for key, value in completeness.items()},
            }
        )
        previous_ids = id_set

    transition_counts: collections.Counter[str] = collections.Counter()
    repeated_ids = 0
    consecutive_diffs: list[dict[str, Any]] = []
    for portal_id, events in histories.items():
        events.sort(key=lambda event: event["file_date"])
        if len(events) > 1:
            repeated_ids += 1
        for before, after in zip(events, events[1:]):
            transition_counts[f"{before['change_type']} -> {after['change_type']}"] += 1
            differences = top_level_diff(before["row"], after["row"])
            consecutive_diffs.append(
                {
                    "portalId": portal_id,
                    "from_date": before["file_date"],
                    "to_date": after["file_date"],
                    "from_type": before["change_type"],
                    "to_type": after["change_type"],
                    "changed_top_level_fields": differences,
                    "payload_identical_excluding_increment_metadata": stripped_payload(before["row"]) == stripped_payload(after["row"]),
                }
            )

    examples = []
    desired = [
        ("TypyZmenOpenData/novy", "TypyZmenOpenData/zmeneny"),
        ("TypyZmenOpenData/zmeneny", "TypyZmenOpenData/zruseny"),
        ("TypyZmenOpenData/novy", "TypyZmenOpenData/zruseny"),
    ]
    for from_type, to_type in desired:
        for portal_id in sorted(histories):
            events = histories[portal_id]
            pairs = list(zip(events, events[1:]))
            match = next(
                (
                    (before, after)
                    for before, after in pairs
                    if before["change_type"] == from_type and after["change_type"] == to_type
                ),
                None,
            )
            if match:
                before, after = match
                examples.append(
                    {
                        "portalId": portal_id,
                        "events": [compact_event(event) for event in events],
                        "transition_changed_top_level_fields": top_level_diff(before["row"], after["row"]),
                    }
                )
                break

    if len(examples) < 4:
        candidates = [
            (portal_id, events)
            for portal_id, events in histories.items()
            if len(events) >= 3
        ]
        if candidates:
            portal_id, events = sorted(candidates, key=lambda item: (-len(item[1]), item[0]))[0]
            examples.append({"portalId": portal_id, "events": [compact_event(event) for event in events]})

    last_event_by_id = {portal_id: events[-1] for portal_id, events in histories.items()}
    snapshot_presence: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for portal_id, event in last_event_by_id.items():
        change_type = event["change_type"]
        snapshot_presence[change_type]["present"] += portal_id in snapshot_by_portal
        snapshot_presence[change_type]["absent"] += portal_id not in snapshot_by_portal

    changed_key_counts: collections.Counter[str] = collections.Counter()
    identical_repeats = 0
    for item in consecutive_diffs:
        if item["payload_identical_excluding_increment_metadata"]:
            identical_repeats += 1
        for key in item["changed_top_level_fields"]:
            changed_key_counts[key] += 1

    unresolved_change_types = sorted(
        {
            identifier
            for identifier in refs
            if identifier.startswith("TypyZmenOpenData/")
        }
        - codelist_ids["TypyZmenOpenData"]
    )

    return {
        "files": file_profiles,
        "file_count": len(file_profiles),
        "total_rows": len(all_rows),
        "distinct_portal_ids": len(histories),
        "portal_ids_appearing_in_multiple_files": repeated_ids,
        "schema_validation": validate_rows(all_rows, item_schema),
        "change_type_codelist_unresolved": unresolved_change_types,
        "transition_counts": dict(sorted(transition_counts.items())),
        "consecutive_event_pairs": len(consecutive_diffs),
        "identical_consecutive_payloads_excluding_increment_metadata": identical_repeats,
        "changed_top_level_field_counts": dict(changed_key_counts.most_common()),
        "last_event_snapshot_presence": {
            key: dict(value) for key, value in sorted(snapshot_presence.items())
        },
        "lifecycle_examples": examples,
    }


def profile_pno(vacancy_municipality_ids: set[str]) -> dict[str, Any]:
    schema = json.loads(PNO_SCHEMA.read_text(encoding="utf-8"))
    schema_fields = list(schema["properties"])
    row_count, fields, rows = top_level_stats(iter_json_array(PNO), schema_fields)
    keys = collections.Counter()
    hashes = collections.Counter()
    rows_by_date = collections.Counter()
    municipalities: set[str] = set()
    districts: set[str] = set()
    regions: set[str] = set()
    pno_formula_mismatches = 0
    pno_contact_formula_mismatches = 0
    negative_measures = 0
    for row in rows:
        key = (row.get("rozhodne_datum"), row.get("uchazec_pohlavi"), row.get("obec_kod"))
        keys[key] += 1
        hashes[canonical_hash(row)] += 1
        rows_by_date[row.get("rozhodne_datum")] += 1
        if row.get("obec_kod") is not None:
            municipalities.add(str(row["obec_kod"]))
        if row.get("okres_kod") is not None:
            districts.add(str(row["okres_kod"]))
        if row.get("kraj_kod") is not None:
            regions.add(str(row["kraj_kod"]))
        population = row.get("pocet_obyvatel_vek_15_64")
        if population:
            expected = row.get("pocet_uchazeci_dosazitelni_trvala") / population
            pno_formula_mismatches += abs(expected - row.get("pno", expected)) > 1e-12
            expected_contact = row.get("pocet_uchazeci_dosazitelni_kontaktni") / population
            pno_contact_formula_mismatches += abs(expected_contact - row.get("pno_kontaktni", expected_contact)) > 1e-12
        for field in (
            "pocet_obyvatel_vek_15_64",
            "pocet_uchazeci_dosazitelni_trvala",
            "pocet_uchazeci_v_evidenci_trvala",
            "pocet_uchazeci_dosazitelni_kontaktni",
            "pocet_uchazeci_v_evidenci_kontaktni",
            "pno",
            "pno_kontaktni",
        ):
            value = row.get(field)
            negative_measures += value is not None and value < 0

    vacancy_codes = {identifier.split("/", 1)[1] for identifier in vacancy_municipality_ids}
    missing_in_pno = sorted(vacancy_codes - municipalities)
    return {
        "file": str(PNO.relative_to(ROOT)),
        "row_count": row_count,
        "field_profile": fields,
        "schema_check": validate_rows(rows[:1], schema),
        "exact_duplicate_rows": sum(count - 1 for count in hashes.values() if count > 1),
        "candidate_key": {
            "fields": ["rozhodne_datum", "uchazec_pohlavi", "obec_kod"],
            "null_component_rows": sum(any(value is None for value in key) for key in keys),
            "duplicate_rows": sum(count - 1 for count in keys.values() if count > 1),
        },
        "dates": {
            "min": min(rows_by_date),
            "max": max(rows_by_date),
            "distinct": len(rows_by_date),
            "rows_by_date": dict(sorted(rows_by_date.items())),
        },
        "gender_values": dict(sorted(collections.Counter(row.get("uchazec_pohlavi") for row in rows).items(), key=lambda pair: str(pair[0]))),
        "distinct_municipality_codes": len(municipalities),
        "distinct_district_codes": len(districts),
        "distinct_region_codes": len(regions),
        "pno_formula_mismatches": pno_formula_mismatches,
        "pno_contact_formula_mismatches": pno_contact_formula_mismatches,
        "negative_measure_values": negative_measures,
        "vacancy_municipality_join": {
            "vacancy_distinct_codes": len(vacancy_codes),
            "matched": len(vacancy_codes & municipalities),
            "unmatched": len(missing_in_pno),
            "unmatched_sample": missing_in_pno[:20],
        },
    }


def profile_old_unemployment() -> dict[str, Any]:
    rows = list(iter_json_array(OLD_UNEMPLOYMENT, "polozky"))
    keys = collections.Counter((row.get("obdobi"), row.get("typUzemnihoCelku"), row.get("uzemniCelek")) for row in rows)
    return {
        "file": str(OLD_UNEMPLOYMENT.relative_to(ROOT)),
        "row_count": len(rows),
        "fields": sorted({key for row in rows for key in row}),
        "territory_type_counts": dict(sorted(collections.Counter(row.get("typUzemnihoCelku") for row in rows).items(), key=lambda pair: str(pair[0]))),
        "period_values": sorted({row.get("obdobi") for row in rows}),
        "candidate_key_duplicate_rows": sum(count - 1 for count in keys.values() if count > 1),
        "null_counts": {
            field: sum(row.get(field) is None for row in rows)
            for field in sorted({key for row in rows for key in row})
        },
    }


def source_url(relative: Path) -> str | None:
    text = relative.as_posix()
    base = "https://data.mpsv.cz"
    name = relative.name
    if text.startswith("data/raw/vacancies/full/"):
        return f"{base}/od/soubory/volna-mista/volna-mista.json.gz"
    if text.startswith("data/raw/vacancies/increments/"):
        return f"{base}/od/soubory/volna-mista-prirustek/{name}"
    if text.startswith("data/raw/vacancies/schema/"):
        directory = "volna-mista-prirustek" if "prirustek" in name else "volna-mista"
        return f"{base}/od/soubory/{directory}/{name}"
    if text.startswith("data/raw/codelists/"):
        return f"{base}/od/soubory/ciselniky/{name}"
    if name.startswith("podil-nezamestnanych-osob-adresa-retrieved"):
        return f"{base}/portal/api/reports/by-table/evid_pno_adresa_agr_frz_odata/data/json?unbounded=true"
    if name == "podil-nezamestnanych-osob-adresa.schema.json":
        return f"{base}/portal/api/reports/by-table/evid_pno_adresa_agr_frz_odata/schema/json?title=podil_nezamestnanych_osob_trvala_kontaktni_adresa_metadata"
    if name.startswith("uchazeci-a-volna-mista"):
        return f"{base}/od/soubory/uchazeci-a-volna-mista/{name}"
    return None


def build_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(RAW.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        relative = path.relative_to(ROOT)
        stat = path.stat()
        files.append(
            {
                "path": str(relative),
                "source_url": source_url(relative),
                "retrieved_at_utc_from_file_mtime": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc).isoformat(),
                "compressed_or_file_bytes": stat.st_size,
                "uncompressed_bytes": uncompressed_size(path),
                "sha256": sha256_file(path),
                "encoding": "UTF-8" if path.suffix in {".json", ".jsonld"} or path.name.endswith(".json.gz") else None,
                "compression": "gzip" if path.suffix == ".gz" else None,
            }
        )
    return {"generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "files": files}


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    codelist_ids, codelist_profiles = load_codelists()
    vacancy, snapshot_by_portal, vacancy_municipalities = profile_full_vacancies(codelist_ids, codelist_profiles)
    incremental = profile_increments(snapshot_by_portal, codelist_ids)
    unemployment = {
        "current_pno_by_address": profile_pno(vacancy_municipalities),
        "legacy_uchazeci_a_volna_mista": profile_old_unemployment(),
    }
    manifest = build_manifest()

    (ANALYSIS / "vacancy-profile.json").write_text(
        json.dumps(vacancy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ANALYSIS / "incremental-profile.json").write_text(
        json.dumps(incremental, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ANALYSIS / "unemployment-profile.json").write_text(
        json.dumps(unemployment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (RAW / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "vacancies": vacancy["row_count"],
                "increment_rows": incremental["total_rows"],
                "pno_rows": unemployment["current_pno_by_address"]["row_count"],
                "manifest_files": len(manifest["files"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
