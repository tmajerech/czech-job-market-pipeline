from datetime import datetime
from pathlib import Path
from shutil import copyfileobj
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from config import Config


SOURCE_URL = "https://data.mpsv.cz/od/soubory/volna-mista/volna-mista.json.gz"
SOURCE_TIMEZONE = ZoneInfo("Europe/Prague")
CHUNK_SIZE = 1024 * 1024


def download_bronze() -> Path:
    snapshot_date = datetime.now(SOURCE_TIMEZONE).date().isoformat()
    destination = (
        Path(__file__).parent
        / Config.RAW_PATH
        / f"snapshot_date={snapshot_date}"
        / "volna-mista.json.gz"
    )

    if destination.is_file() and destination.stat().st_size > 0:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_destination = destination.with_suffix(f"{destination.suffix}.part")

    try:
        with urlopen(Request(SOURCE_URL), timeout=60) as response:
            with temporary_destination.open("wb") as output:
                copyfileobj(response, output, length=CHUNK_SIZE)
        temporary_destination.replace(destination)
    except BaseException:
        temporary_destination.unlink(missing_ok=True)
        raise

    return destination


if __name__ == "__main__":
    print(download_bronze())
