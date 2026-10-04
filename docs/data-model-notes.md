# Data model notes

These are modelling implications from observed data, not a final warehouse design.

## Observed entity map

```text
VACANCY_CURRENT (portalId)
├── employer {ico, name}                         0..1
├── requested profession text                   1
├── main profession -> CZ-ISCO                  1
├── minimum education -> detailed education     1
├── shift / salary type / publication mode      1 each
├── work location                               0..1 tagged union
│   ├── workplace[] -> structured address
│   ├── direct municipality
│   ├── district[]
│   └── free-text address
├── employment relationship[]                   1..4
├── employee suitability[]                      1..7
├── benefits[]                                  0..7
├── required skills[]                           0..9
├── required languages[] -> language + level    0..7
├── prior/required occupation[] -> CZ-ISCO      0..5
├── requested education[] -> KKOV               0..6
└── first-contact object                        1

VACANCY_INCREMENT_OBSERVATION (source object + row ordinal)
└── portalId -> VACANCY logical identity
    ├── new / changed / cancelled marker
    └── full vacancy-shaped payload

UNEMPLOYMENT_MUNICIPALITY_MONTH_SEX
└── (month-end, sex, municipality code)
    ├── permanent-address counts/rate
    └── contact-address counts/rate

LEGACY_UNEMPLOYMENT_GEO_MONTH
└── (month-end, territory type, territory name)
    └── job seekers, registered vacancies, unemployment share
```

## Grains and candidate keys

| Entity | Observed grain | Key assessment |
|---|---|---|
| Current vacancy | One currently published vacancy | `portalId` is non-null and unique across 39,217 rows. `id` is derived. Strong current key |
| Raw increment observation | One row at one ordinal in one downloaded source object | No safe natural event key. Same `portalId` and `datumZmeny` can occur more than once in a file with contradictory type ordering. Use `(source_object_id, row_ordinal)` |
| Logical vacancy across observations | One business vacancy identity | `portalId` is the best link. It survives cancellation/reactivation, but `datumVlozeni` can reset and selected attributes can change |
| Vacancy version (potential) | One distinct observed payload for a `portalId` | Candidate technical key `(portalId, canonical_payload_hash)` plus first/last observation timestamps. Do not claim exact business validity before collection began |
| Current municipality unemployment | One municipality × month-end × sex | `(rozhodne_datum, uchazec_pohlavi, obec_kod)` is non-null and unique across 250,360 rows |
| Legacy unemployment aggregate | One month-end × territory type × territory name | Unique in the 92-row sample, but name is not a durable geography key |
| Codelist member | One namespaced reference value | `id` is non-null and unique in every non-empty downloaded codelist |

## Relationship classification

| Relationship | Classification | Evidence / caveat |
|---|---|---|
| Current vacancy `portalId` ↔ increment `portalId` | **Verified deterministic join** | Same numeric identifier; increment `id` and snapshot `id` use different namespaces but are both derived from it |
| Vacancy reference object `.id` ↔ matching MPSV codelist `.id` | **Verified deterministic join** | Zero unresolved distinct IDs across all 21 non-empty directly referenced codelists |
| Increment change type ↔ change-type codelist | **Not currently joinable** | Actual field spelling differs from schema and the official codelist has zero rows |
| Vacancy municipality `Obec/<code>` ↔ current unemployment `obec_kod` | **Verified deterministic geography join** | All 2,587 distinct vacancy municipality codes occur in unemployment. Join after stripping the namespace or through the municipality dimension |
| Vacancy district/region IDs ↔ current unemployment codes | **Verified for coded values, with pseudo-member caveat** | Code systems match; unemployment adds `(neuvedeno)`. The district codelist has `9999`, which is not the same value |
| Vacancy rows ↔ unemployment rows | **Not a direct row-level join** | Facts have different grains. Aggregate vacancies to geography/time and aggregate or retain unemployment sex deliberately |
| Legacy unemployment territory name ↔ coded geography | **Likely join requiring validation** | No code is supplied. Requires an official time-aware name/code crosswalk; string equality is insufficient |
| Employer IČO ↔ external business register | **Likely join requiring validation** | Eight-digit IČO is clean when present, but ARES or another official register was not probed in this phase |
| `kodAdresnihoMista` ↔ RÚIAN address place | **Likely join requiring validation** | Field semantics and values indicate RÚIAN, but an official RÚIAN extract was not downloaded or coverage-tested |
| Vacancy `referencniCislo` across time | **Not a safe historical join key** | Unique in the current snapshot, but three IDs changed it across re-emitted events |
| Employer name, territory name, profession text | **Not safely joinable as keys** | Descriptive text; case/spelling/version changes are expected |

## Nested modelling implications

- Keep the raw JSON payload intact in bronze.
- In silver, scalar vacancy attributes can form a parent record keyed by snapshot/observation plus `portalId`.
- Repeated arrays are real many-valued relationships, not columns to concatenate. They are natural child/bridge tables for employment relationships, suitability, benefits, skills, languages, prior occupations, and KKOV education.
- `mistoVykonuPrace` is a union of four location representations. A workplace child may have a structured address; other vacancies apply to a municipality, multiple districts, or free text. Do not force all four into one mandatory address foreign key.
- Employer is deliberately absent for privacy-mode records. Use an “undisclosed” member only in analytical dimensions; retain source nulls in silver.
- Free-text fields (`upresnujiciInformace`, profession labels, contact details) are source attributes, not separate analytical entities in this non-NLP project.

## Historical / SCD implications

### Vacancy history

A Type-2-like vacancy version table is feasible **from project collection start** if versions are derived from canonical payload changes observed in full snapshots. Suggested semantics:

- `observed_from` / `observed_to`, not asserted business-valid timestamps.
- a payload hash to suppress unchanged re-emissions;
- explicit `is_present_in_snapshot` and observed event type;
- reactivation as another state transition, not creation of a new surrogate entity;
- raw source references retained for audit.

The increment archive alone cannot provide a complete Type 2 history back to October 2024 because there is no initial archived full snapshot, files are missing, and event ordering is ambiguous.

### Reference history

The codelist endpoints expose current files, not dated history. If historical dimension versions matter, archive each retrieval and create a new codelist member version only when its canonical content changes. Do not fabricate historical effective dates.

### Employer

IČO can identify disclosed employers, but only name and IČO are supplied. A small employer dimension is reasonable; SCD changes would reflect observed names, not a complete legal-register history.

## Potential analytical facts and marts

Supported by the data:

- current vacancy counts and offered-place counts by date captured, municipality/district/region, CZ-ISCO level, employer, salary type, employment relationship, suitability, and shift;
- observed vacancy openings/changes/cancellations, with explicit feed-quality flags;
- month-end unemployment counts and PNO by municipality and sex from January 2025;
- long-run monthly job-seeker/registered-vacancy trends at district/region/country level from July 2004 through December 2024;
- vacancy-to-job-seeker or vacancy-to-working-age-population ratios at a common geography/time grain, once vacancy snapshots have been captured at month-end.

Not supported defensibly yet:

- exact daily vacancy state before the project’s first stored full snapshot;
- person-level job-seeker analysis (the chosen unemployment data is aggregated);
- a direct vacancy-to-job-seeker match;
- automatic salary normalization beyond separating the declared hourly/monthly types and flagging anomalies.
