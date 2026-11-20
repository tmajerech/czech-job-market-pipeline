import copy
import gzip
import json
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
VACANCY_SAMPLE = PROJECT_ROOT / "data/samples/vacancy_snapshot_row.json"

CODELISTS = {
    "cz-isco.json.gz": [
        {
            "id": "CzIsco/52231",
            "kod": "52231",
            "nazev": {"cs": "Test occupation"},
        }
    ],
    "kraje.json.gz": [
        {
            "id": "Kraj/35",
            "kod": "CZ010",
            "kodNuts3": "CZ010",
            "nazev": {"cs": "Test region"},
        }
    ],
    "okresy.json.gz": [
        {
            "id": "Okres/3302",
            "kod": "3302",
            "kodLau": "CZ0100",
            "kraj": "Kraj/35",
            "nazev": {"cs": "Test district"},
        }
    ],
    "obce.json.gz": [
        {
            "id": "Obec/545848",
            "kod": "545848",
            "okres": "Okres/3302",
            "nazev": {"cs": "Test municipality"},
        }
    ],
    "typy-mzdy.json.gz": [
        {
            "id": "TypMzdy/mesic",
            "kod": "mesic",
            "nazev": {"cs": "Měsíční mzda"},
        }
    ],
    "smennosti.json.gz": [
        {
            "id": "Smennost/jednoSm",
            "kod": "jednoSm",
            "nazev": {"cs": "Jednosměnný provoz"},
        }
    ],
    "zverejnovat-vpm.json.gz": [
        {
            "id": "ZverejnovatVpm/ano",
            "kod": "ano",
            "nazev": {"cs": "Ano"},
        }
    ],
    "typy-mista-vykonu-prace.json.gz": [
        {
            "id": "TypMistaVykonuPrace/adrprov",
            "kod": "adrprov",
            "nazev": {"cs": "Adresa provozovny"},
        }
    ],
    "kontaktni-pracoviste.json.gz": [
        {
            "id": "KontaktniPracoviste/CKA",
            "kod": "CKA",
            "nazev": {"cs": "Test contact office"},
        }
    ],
}


def write_snapshot(
    bronze_root: Path,
    snapshot_date: date,
    portal_ids: tuple[int, ...],
) -> None:
    partition = f"snapshot_date={snapshot_date.isoformat()}"
    vacancy_path = bronze_root / "volna-mista" / partition / "volna-mista.json.gz"
    vacancy_path.parent.mkdir(parents=True, exist_ok=True)

    sample = json.loads(VACANCY_SAMPLE.read_text(encoding="utf-8"))
    vacancies = []
    for portal_id in portal_ids:
        vacancy = copy.deepcopy(sample)
        vacancy["id"] = f"VolneMisto/{portal_id}"
        vacancy["portalId"] = portal_id
        vacancy["datumVlozeni"] = f"{snapshot_date.isoformat()}T00:00:00.000Z"
        vacancy["datumZmeny"] = f"{snapshot_date.isoformat()}T08:00:00.000Z"
        vacancy["zamestnavatel"] = {
            "ico": "12345678",
            "nazev": "Test employer",
        }
        vacancy["mistoVykonuPrace"]["obec"] = {"id": "Obec/545848"}
        vacancy["mistoVykonuPrace"]["okresy"] = [{"id": "Okres/3302"}]
        vacancy["vyhodyVolnehoMista"] = []
        vacancy["pozadovanaDovednost"] = []
        vacancy["pozadovanaJazykovaZnalost"] = []
        vacancy["pozadovaneVzdelani"] = []
        vacancy["mistoVykonuPrace"]["pracoviste"][0]["nazev"] = (
            f"Test workplace {portal_id}"
        )
        vacancy["mistoVykonuPrace"]["pracoviste"][0]["adresa"][
            "nazevCastiObce"
        ] = None
        vacancy["prvniKontaktSeZamestnavatelem"]["komuSeHlasit"] = {
            "jmeno": None,
            "prijmeni": None,
            "titulPredJmenem": None,
            "titulZaJmenem": None,
            "poziceVeSpolecnosti": None,
            "email": None,
            "telefon": None,
        }
        vacancy["prvniKontaktSeZamestnavatelem"]["kdeSeHlasit"][
            "mistoKontaktu"
        ] = "Test employer"
        vacancies.append(vacancy)

    with gzip.open(vacancy_path, "wt", encoding="utf-8") as source_file:
        json.dump({"polozky": vacancies}, source_file, ensure_ascii=False)

    codelists_directory = bronze_root / "codelists" / partition
    codelists_directory.mkdir(parents=True, exist_ok=True)
    for filename, items in CODELISTS.items():
        codelist_path = codelists_directory / filename
        with gzip.open(codelist_path, "wt", encoding="utf-8") as source_file:
            json.dump({"polozky": items}, source_file, ensure_ascii=False)
