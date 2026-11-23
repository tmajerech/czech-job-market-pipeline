#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RETRIEVAL_DATE="2026-10-03"
BASE="https://data.mpsv.cz"

download() {
  local url="$1"
  local destination="$2"

  mkdir -p "$(dirname "$destination")"
  if [[ -s "$destination" ]]; then
    printf 'exists  %s\n' "${destination#"$ROOT_DIR"/}"
    return
  fi

  printf 'fetch   %s\n' "$url"
  curl --fail --location --retry 3 --connect-timeout 20 \
    --output "$destination.part" "$url"
  mv "$destination.part" "$destination"
}

download "$BASE/od/soubory/volna-mista/volna-mista.json.gz" \
  "$ROOT_DIR/analysis/raw/vacancies/full/volna-mista-retrieved-$RETRIEVAL_DATE.json.gz"
download "$BASE/od/soubory/volna-mista/volna-mista.schema.json" \
  "$ROOT_DIR/analysis/raw/vacancies/schema/volna-mista.schema.json"
download "$BASE/od/soubory/volna-mista/volna-mista-metadata.jsonld" \
  "$ROOT_DIR/analysis/raw/vacancies/schema/volna-mista-metadata.jsonld"
download "$BASE/od/soubory/volna-mista-prirustek/volna-mista-prirustek.schema.json" \
  "$ROOT_DIR/analysis/raw/vacancies/schema/volna-mista-prirustek.schema.json"
download "$BASE/od/soubory/volna-mista-prirustek/volna-mista-prirustek-metadata.jsonld" \
  "$ROOT_DIR/analysis/raw/vacancies/schema/volna-mista-prirustek-metadata.jsonld"

increment_dates=(
  2026-09-22 2026-09-23 2026-09-24 2026-09-25 2026-09-26
  2026-09-27 2026-09-30 2026-10-01 2026-10-02
)
for date in "${increment_dates[@]}"; do
  name="volna-mista-prirustek-$date.json.gz"
  download "$BASE/od/soubory/volna-mista-prirustek/$name" \
    "$ROOT_DIR/analysis/raw/vacancies/increments/$name"
done

codelists=(
  casti-obci cz-isco dovednosti jazyky kontaktni-pracoviste kraje
  mestske-obvody-mestske-casti mestske-obvody-v-praze obce okresy
  pracovnepravni-vztahy smennosti typy-mista-vykonu-prace typy-mzdy
  typy-stavebniho-objektu typy-zmen-opendata urovne-znalosti-jazyka
  vhodnosti-pro-typ-zamestnance vyhody-volneho-mista
  vzdelani-detailni-kategorie vzdelani-kkov zverejnovat-vpm
)
for name in "${codelists[@]}"; do
  download "$BASE/od/soubory/ciselniky/$name.json.gz" \
    "$ROOT_DIR/analysis/raw/codelists/$name.json.gz"
  download "$BASE/od/soubory/ciselniky/$name.schema.json" \
    "$ROOT_DIR/analysis/raw/codelists/$name.schema.json"
done
download "$BASE/od/soubory/ciselniky/cz-isco-metadata.jsonld" \
  "$ROOT_DIR/analysis/raw/codelists/cz-isco-metadata.jsonld"

download "$BASE/portal/api/reports/by-table/evid_pno_adresa_agr_frz_odata/data/json?unbounded=true" \
  "$ROOT_DIR/analysis/raw/unemployment/podil-nezamestnanych-osob-adresa-retrieved-$RETRIEVAL_DATE.json"
download "$BASE/portal/api/reports/by-table/evid_pno_adresa_agr_frz_odata/schema/json?title=podil_nezamestnanych_osob_trvala_kontaktni_adresa_metadata" \
  "$ROOT_DIR/analysis/raw/unemployment/podil-nezamestnanych-osob-adresa.schema.json"
download "$BASE/od/soubory/uchazeci-a-volna-mista/uchazeci-a-volna-mista-12-2024.json.gz" \
  "$ROOT_DIR/analysis/raw/unemployment/uchazeci-a-volna-mista-12-2024.json.gz"
download "$BASE/od/soubory/uchazeci-a-volna-mista/uchazeci-a-volna-mista.schema.json" \
  "$ROOT_DIR/analysis/raw/unemployment/uchazeci-a-volna-mista.schema.json"

printf 'Done. Generate hashes and measurements with scripts/profile_data.py.\n'
