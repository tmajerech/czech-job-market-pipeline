# Data profile

Measurements below come from the files retrieved on 3 October 2026. The scripts streamed the large JSON arrays and performed exact counts; no pandas dataframe or synthetic sample was used. Machine-readable output is in [`analysis/vacancy-profile.json`](../analysis/vacancy-profile.json), [`analysis/unemployment-profile.json`](../analysis/unemployment-profile.json), and [`data/raw/manifest.json`](../data/raw/manifest.json).

## Full vacancy snapshot

### Size and identifiers

| Measurement | Result |
|---|---:|
| Rows | 39,217 |
| Compressed / uncompressed size | 17,368,295 / 185,573,692 bytes |
| `portalId` null / distinct / duplicate rows | 0 / 39,217 / 0 |
| `id` null / distinct / duplicate rows | 0 / 39,217 / 0 |
| `referencniCislo` null / distinct / duplicate rows | 0 / 39,217 / 0 |
| Exact duplicate records | 0 |
| `id != "VolneMisto/<portalId>"` | 0 |

`portalId` is therefore a sound current-snapshot key. `id` is derived from it. `referencniCislo` is also unique in this snapshot, but the increment probe found three IDs whose reference number changed across re-emitted records, so it is not preferred as the historical key.

### Observed top-level structure

Scalar/date/flag fields:

`portalId`, `id`, `referencniCislo`, `azylant`, `cizinecMimoEu`, `datumVlozeni`, `datumZmeny`, `mesicniMzdaOd`, `mesicniMzdaDo`, `modraKarta`, `pocetHodinTydne`, `pocetMist`, `statniSpravaSamosprava`, `terminZahajeniPracovnihoPomeru`, `terminUkonceniPracovnihoPomeru`, `souhlasAgenturyAgentura`, `souhlasAgenturyUzivatel`, `urlAdresa`, `zamestnaneckaKarta`, `expirace`.

Objects / codelist references:

`pozadovanaProfese`, `upresnujiciInformace`, `minPozadovaneVzdelani`, `smennost`, `typMzdy`, `zverejnovat`, `mistoVykonuPrace`, `zamestnavatel`, `profeseCzIsco`, `kontaktniPracoviste`, `prvniKontaktSeZamestnavatelem`.

Repeated arrays:

`pracovnePravniVztahy`, `vhodnostiPracovnihoMista`, `vyhodyVolnehoMista`, `pozadovanaDovednost`, `pozadovanaJazykovaZnalost`, `pozadovanePovolani`, `pozadovaneVzdelani`.

Observed JSON types matched the published types except where the records violated explicit nested nullability or maximum length constraints, described below. Numeric fields appear as both JSON integers and numbers where the schema permits `number`.

### Nulls and repeated structures

| Field | Null rows | Null rate | Non-empty array rows | Total child rows | Max children/vacancy |
|---|---:|---:|---:|---:|---:|
| `mesicniMzdaDo` | 23,114 | 58.94% | — | — | — |
| `pocetHodinTydne` | 17,102 | 43.61% | — | — | — |
| `upresnujiciInformace` | 4,620 | 11.78% | — | — | — |
| `expirace` | 36,902 | 94.10% | — | — | — |
| `urlAdresa` | 37,751 | 96.26% | — | — | — |
| `pracovnePravniVztahy` | 0 | 0% | 39,217 | 43,206 | 4 |
| `vhodnostiPracovnihoMista` | 0 | 0% | 39,217 | 49,449 | 7 |
| `vyhodyVolnehoMista` | 30,141 | 76.86% | 9,076 | 17,897 | 7 |
| `pozadovanaDovednost` | 34,218 | 87.25% | 4,999 | 7,933 | 9 |
| `pozadovanaJazykovaZnalost` | 37,360 | 95.26% | 1,857 | 2,576 | 7 |
| `pozadovanePovolani` | 38,411 | 97.94% | 806 | 848 | 5 |
| `pozadovaneVzdelani` | 38,836 | 99.03% | 381 | 463 | 6 |

No observed repeated field used an empty array: it was either `null` or non-empty. Preserve that distinction in raw/silver processing rather than silently coercing both to the same value.

### Schema validation

The published full-snapshot JSON Schema is itself valid Draft 2020-12. Exhaustive validation found 38 invalid rows (0.097%):

- 35 rows have `prvniKontaktSeZamestnavatelem.kdeSeHlasit = null`, while the schema permits only an object.
- 1 `kdeSeHlasit.telefon` value exceeds the declared 50-character maximum (observed maximum 110).
- 2 `komuSeHlasit.telefon` values exceed the 50-character maximum (observed maximum 52).

These should be quarantined or admitted under an explicit compatibility exception; silently dropping them would lose otherwise useful vacancies.

### Employer

- Six records have a null employer object, consistent with the documented privacy publication mode.
- Among non-null employer objects, 10 `ico` values are null.
- 17,961 distinct non-null IČOs were observed.
- Every non-null IČO matched eight decimal digits.

Employer is therefore a reusable dimension candidate keyed by IČO when present, but the null/privacy case must remain valid and employer name should not be treated as a key.

### Geography

- `mistoVykonuPrace` is present for 39,211 records and null for 6.
- 36,412 vacancies have one or more `pracoviste` entries (36,412 child rows in this snapshot).
- 33,886 workplace children contain a structured address; 2,526 have a null address.
- 6,864 vacancies use the direct municipality representation.
- 1,990 use a district list.
- 386 use a free-text address.
- Across all representations: 2,587 distinct municipalities, 78 districts, 14 regions, and 14,151 RÚIAN address-place codes were observed.

All observed `Obec`, `Okres`, `Kraj`, municipality-part, and Prague-division IDs resolved in the downloaded official codelists. The location is a tagged union, not a single address: a model must retain workplace addresses, direct-municipality scope, district scope, and free text separately.

### Profession and education

- `profeseCzIsco.id` is non-null in all 39,217 records.
- 1,301 distinct main CZ-ISCO IDs were used; all resolve in the 1,995-row codelist.
- Main-profession code granularity is mixed: 1 row uses a 1-digit code, 3 use 2 digits, 688 use 3, 6,050 use 4, and 32,475 use 5.
- A further 848 prior/required-occupation child rows use CZ-ISCO references.
- 463 requested-education child rows use 154 distinct KKOV references; all resolve.

Do not assume every vacancy is classified at the 5-digit leaf level. Analytical groupings should retain the supplied code and derive parent prefixes explicitly.

### Salary

`mesicniMzdaOd` and `typMzdy` are non-null in every row; `mesicniMzdaDo` is null in 23,114 rows. No record has `from > to`, and no non-positive salary value was observed.

| Type | Rows with `from` | `from` median | `from` p99 | `from` max | Rows with `to` | `to` median | `to` max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Hourly (`TypMzdy/hod`) | 2,322 | 155 | 23,888.7 | 139,380 | 681 | 185 | 50,000 |
| Monthly (`TypMzdy/mesic`) | 36,895 | 27,328 | 90,000 | 400,000 | 15,422 | 38,000 | 560,000 |

The hourly tail is plainly suspicious: 33 hourly lower bounds and 11 hourly upper bounds exceed 1,000. Examples include hourly records with lower bounds 23,470, 27,160, 28,000, and 55,000, which look monthly. Conversely, 287 monthly lower bounds are below 10,000 and may represent part-time work or unit errors. These are quality flags, not grounds for automatic unit conversion.

### Other anomalies

- One record has `pocetHodinTydne = 0`; none exceed 168.
- Offered-place count is positive in every current row, matching the snapshot documentation.
- One active record has future `datumVlozeni=2027-08-24` even though its `datumZmeny` is 2026-09-04.
- Two start dates are obvious year-entry errors: `2226-12-01` and `2206-09-14`.
- `datumVlozeni` ranges from 2013-12-13 to 2027-08-24; `datumZmeny` ranges from 2019-01-03 to 2026-10-02.

## Current municipality unemployment fact

| Measurement | Result |
|---|---:|
| File size / rows | 147,039,286 bytes / 250,360 |
| Dates | 20 month-ends, 2025-01-31 through 2026-08-31 |
| Rows per month | 12,518 |
| Municipality codes | 6,259, including `(neuvedeno)` |
| District / region codes | 78 / 15 |
| Sex values | `M` 125,180; `Ž` 125,180 |
| Exact duplicate rows | 0 |
| Duplicate `(date, sex, municipality)` keys | 0 |

The fact has no missing key components. Population is null in 40 rows, and both PNO measures are null in 200 rows (0.0799%). Those 200 are exactly the two sexes × 20 months for `(neuvedeno)` plus four military areas with zero population (`Libavá`, `Boletice`, `Hradiště`, `Březina`). No measure is negative. Every non-null `pno` and `pno_kontaktni` exactly matches the corresponding reachable-job-seeker count divided by population within floating-point tolerance.

The publisher labels its schema as Draft 2020-12 JSON Schema, but uses non-standard `date` and `decimal` values for `type`. A standards validator rejects the schema before validating a row. The data itself encodes dates as strings and decimals as JSON numbers, so an ingestion contract must normalize this publisher schema or maintain an internal schema.

All 2,587 municipality codes observed in vacancy locations exist in this unemployment dataset. The reverse is not expected because current vacancies cover only a subset of municipalities. The one unemployment pseudo-code `(neuvedeno)` is absent from the official municipality codelist.

## Legacy December 2024 unemployment aggregate

The sample has 92 rows: 1 Czech Republic total, 14 regions, and 77 districts, all for 31 December 2024. `(obdobi, typUzemnihoCelku, uzemniCelek)` is unique. `miraNezamestnanosti` is null in all 92 rows; `podilNezOsob`, `uchazeci`, and `volnaMista` are populated.

This is a valid long-series fact domain, but it carries territory names rather than codes. A deterministic historical geography bridge would need to be sourced and validated before joining it to coded vacancy geography.
