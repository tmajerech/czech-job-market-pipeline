from pathlib import Path
from shutil import copyfileobj
from urllib.request import Request, urlopen


CHUNK_SIZE = 1024 * 1024


def download_file(source_url: str, destination: Path) -> Path:
    if destination.is_file() and destination.stat().st_size > 0:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_destination = destination.with_suffix(f"{destination.suffix}.part")

    try:
        with urlopen(Request(source_url), timeout=60) as response:
            with temporary_destination.open("wb") as output:
                copyfileobj(response, output, length=CHUNK_SIZE)
        temporary_destination.replace(destination)
    except BaseException:
        temporary_destination.unlink(missing_ok=True)
        raise

    return destination
