from datetime import date
from pathlib import Path

from pipeline.bronze.download import download_file


SOURCE_ROOT = "https://data.mpsv.cz/od/soubory/ciselniky"
CODELIST_NAMES = (
    "casti-obci",
    "cz-isco",
    "dovednosti",
    "jazyky",
    "kontaktni-pracoviste",
    "kraje",
    "mestske-obvody-mestske-casti",
    "mestske-obvody-v-praze",
    "obce",
    "okresy",
    "pracovnepravni-vztahy",
    "smennosti",
    "typy-mista-vykonu-prace",
    "typy-mzdy",
    "typy-stavebniho-objektu",
    "typy-zmen-opendata",
    "urovne-znalosti-jazyka",
    "vhodnosti-pro-typ-zamestnance",
    "vyhody-volneho-mista",
    "vzdelani-detailni-kategorie",
    "vzdelani-kkov",
    "zverejnovat-vpm",
)


def download_codelists(bronze_root: Path, snapshot_date: date) -> tuple[Path, ...]:
    destination_directory = bronze_root / "codelists" / f"snapshot_date={snapshot_date.isoformat()}"

    return tuple(
        download_file(
            f"{SOURCE_ROOT}/{name}.json.gz",
            destination_directory / f"{name}.json.gz",
        )
        for name in CODELIST_NAMES
    )
