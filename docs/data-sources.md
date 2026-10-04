# Official data sources

Discovery was performed on 3 October 2026 (Europe/Prague). Downloads came directly from `data.mpsv.cz`; no mirrors or synthetic data were used. Exact local hashes, sizes, retrieval times, and URLs are in [`data/raw/manifest.json`](../data/raw/manifest.json).

## Source classification

| Dataset | Role | Publisher / provider | Format and local size | Update / retained history |
|---|---|---|---|---|
| [Volná místa za celou ČR](https://data.mpsv.cz/web/data/volna-mista-za-celou-cr) | Current full snapshot | Published by MPSV; source system/provider is Úřad práce ČR AIS | JSON and JSON-LD, plain or gzip. Downloaded JSON gzip: 17,368,295 bytes; 185,573,692 bytes uncompressed | Replaced daily at a stable URL. The directory exposes the current file, not dated old snapshots. Metadata says coverage starts 2014-12; an active record actually has `datumVlozeni=2013-12-13` |
| [Přírůstky volných míst za celou ČR](https://data.mpsv.cz/web/data/prirustky-volnych-mist-za-celou-cr) | Increment/change feed | Published by MPSV; source system/provider is Úřad práce ČR AIS | Dated JSON and JSON-LD, plain or gzip. Nine downloaded gzip files range from 535,882 to 3,046,449 bytes (5,343,733–28,939,405 uncompressed) | Described as daily. The live directory retained 513 dated gzip JSON files from 2024-10-31 through 2026-10-02, but 189 of the 702 calendar dates had no file |
| [MPSV codelists](https://data.mpsv.cz/od/soubory/ciselniky/) | Reference data | MPSV | JSON/JSON-LD and gzip variants, with JSON Schemas. The 45 downloaded data/schema/metadata files total 431,465 bytes compressed/on disk | Current files at stable URLs; no versioned codelist archive was found |
| [Current unemployment statistics](https://data.mpsv.cz/portal/sestavy/statistiky/trh-prace/nezamestnanost/statistiky-nezamestnanosti) — `podil_nezamestnanych_osob_trvala_kontaktni_adresa` | Independent monthly fact domain | MPSV / Úřad práce ČR | Generated JSON or CSV API. Downloaded JSON: 147,039,286 bytes, 250,360 rows | Monthly, sixth working day. Current response includes 2025-01-31 through 2026-08-31; old months remain inside the cumulative response |
| [Uchazeči a volná místa](https://data.mpsv.cz/web/data/uchazeci-a-volna-mista) | Legacy independent monthly aggregate fact | MPSV / Úřad práce ČR | Dated JSON/JSON-LD, plain or gzip. Sample for 2024-12: 2,013 bytes compressed, 21,727 uncompressed, 92 rows | Complete monthly archive: 246 months from 2004-07 through 2024-12. Superseded by the new portal from January 2025 |

### Direct URLs used

- Full snapshot directory: <https://data.mpsv.cz/od/soubory/volna-mista/>
- Full snapshot schema: <https://data.mpsv.cz/od/soubory/volna-mista/volna-mista.schema.json>
- Increment directory: <https://data.mpsv.cz/od/soubory/volna-mista-prirustek/>
- Increment schema: <https://data.mpsv.cz/od/soubory/volna-mista-prirustek/volna-mista-prirustek.schema.json>
- Current unemployment JSON API: <https://data.mpsv.cz/portal/api/reports/by-table/evid_pno_adresa_agr_frz_odata/data/json?unbounded=true>
- Current unemployment schema API: <https://data.mpsv.cz/portal/api/reports/by-table/evid_pno_adresa_agr_frz_odata/schema/json?title=podil_nezamestnanych_osob_trvala_kontaktni_adresa_metadata>
- Legacy unemployment archive: <https://data.mpsv.cz/od/soubory/uchazeci-a-volna-mista/>

All inspected payloads decode as UTF-8 JSON. The downloaded source payloads were not edited.

## Vacancy snapshot

The snapshot is not an all-time vacancy table. The official page says it contains vacancies approved by Úřad práce and currently intended for publication, with positive offered-place count and non-expired publication. Some records intentionally suppress employer and workplace data (`ZverejnovatVpm/anosp`).

Identifiers documented or observed:

- `portalId`: documented as the unique portal vacancy identifier; non-null and unique in all 39,217 current rows.
- `id`: always `VolneMisto/<portalId>` in the sample, so it is a namespaced rendering of the same key rather than an independent identifier.
- `referencniCislo`: non-null and unique in the current snapshot, but three sampled IDs changed reference number across re-emitted increment payloads.
- employer `ico`: a useful employer identifier when present, but not a vacancy key and intentionally hidden for some records.

## Increment files

The official documentation says each dated file contains records inserted, changed, or cancelled on the date in its filename. Actual behaviour differs materially; see [`incremental-behaviour.md`](incremental-behaviour.md).

Important source-contract issues:

- Actual records use `typZmenyOpenData`, while the published schema defines `typyZmenOpenData` (extra `y`).
- The referenced `typy-zmen-opendata.json.gz` codelist currently contains an empty `polozky` array, although the data uses `novy`, `zmeneny`, and `zruseny`.
- Dated files remain accessible, but missing dates cannot be distinguished from “no changes” days using the directory alone.

## Codelists actually referenced

The full snapshot referenced the following ID namespaces. Every distinct observed reference resolved in the corresponding downloaded codelist; the change-type exception is noted below.

| Observed prefix | Codelist file | Rows | Used by |
|---|---:|---:|---|
| `CzIsco` | `cz-isco` | 1,995 | Main profession and prior/required occupations |
| `Obec` | `obce` | 6,258 | Direct municipality and workplace/contact addresses |
| `Okres` | `okresy` | 78 | District lists and addresses |
| `Kraj` | `kraje` | 14 | Addresses |
| `CastObce` | `casti-obci` | 15,106 | Addresses |
| `MestskyObvodMestskaCast` | `mestske-obvody-mestske-casti` | 142 | Addresses |
| `MestskyObvodVPraze` | `mestske-obvody-v-praze` | 10 | Prague addresses |
| `TypStavebnihoObjektu` | `typy-stavebniho-objektu` | 4 | Address number type |
| `TypMistaVykonuPrace` | `typy-mista-vykonu-prace` | 6 | Workplace-location mode |
| `KontaktniPracoviste` | `kontaktni-pracoviste` | 269 | Úřad práce contact office |
| `VzdelaniDetailniKategorie` | `vzdelani-detailni-kategorie` | 16 | Minimum education |
| `VzdelaniKkov` | `vzdelani-kkov` | 1,630 | Repeated requested education |
| `Smennost` | `smennosti` | 10 | Shift pattern |
| `TypMzdy` | `typy-mzdy` | 2 | Hourly vs monthly salary |
| `PracovnepravniVztah` | `pracovnepravni-vztahy` | 5 | Repeated employment relationships |
| `VhodnostProTypZamestnance` | `vhodnosti-pro-typ-zamestnance` | 7 | Repeated suitability categories |
| `VyhodyVolnehoMista` | `vyhody-volneho-mista` | 10 | Repeated benefits |
| `Dovednost` | `dovednosti` | 103 | Repeated skill requirements |
| `Jazyk` | `jazyky` | 22 | Repeated language requirements |
| `UrovenZnalostiJazyka` | `urovne-znalosti-jazyka` | 3 | Language level |
| `ZverejnovatVpm` | `zverejnovat-vpm` | 4 | Publication/privacy mode |
| `TypyZmenOpenData` | `typy-zmen-opendata` | 0 | Increment event type; publisher codelist is empty |

The CZ-ISCO codelist has 1-, 2-, 3-, 4-, and 5-digit codes (10, 44, 131, 435, and 1,375 rows respectively). It has no explicit parent field; hierarchy is inferable from code prefixes.

## Unemployment sources

The selected current fact is at municipality × month-end × sex grain. Its natural key is `(rozhodne_datum, uchazec_pohlavi, obec_kod)`. It includes both permanent-address and contact-address counts and rates. `obec_kod` matches the numeric part of vacancy `Obec/<code>` identifiers.

The legacy `uchazeci-a-volna-mista` dataset is much coarser: one monthly row per country, region, or district, with territory names but no stable geographic codes. It is valuable for a long time series, but name matching alone is not a verified deterministic join.

Other portal candidates inspected but not downloaded in full:

- `evid_evidence_stat_1_agr_frz_odata`: 1,962,272 rows at the time of the probe; rich job-seeker demographics.
- `evid_nabidky_poptavky_stat_agr_frz_odata`: 810,421 rows; offer/demand measures by CZ-ISCO and geography.

They remain good future additions, but were unnecessary to answer the first-phase questions.

## Reuse conditions

The downloaded vacancy DCAT metadata states that the distributions contain no copyright works, are not protected by the database-maker special right, and **contain personal data**. The increment metadata makes the same personal-data declaration. Contact names, emails, and phone numbers are present in real rows, so raw vacancy payloads should not be committed to the public portfolio repository even though they are officially published.

CZ-ISCO metadata declares no personal data and similarly states no copyright/special database protection. The new portal’s generated unemployment API response did not include a per-download machine-readable licence object in the inspected response; confirm the portal’s [terms of use](https://data.mpsv.cz/portal/podminky-uziti) before redistributing those payloads. Publishing code, manifests, measurements, and source links is safer than republishing the raw data.
