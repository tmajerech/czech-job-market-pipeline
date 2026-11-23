# Pipeline sources

Bronze downloads these MPSV inputs:

| Input | Endpoint | Use |
|---|---|---|
| Full vacancy snapshot | [volna-mista.json.gz](https://data.mpsv.cz/od/soubory/volna-mista/volna-mista.json.gz) | Current published vacancies |
| 22 codelists | [ciselniky/](https://data.mpsv.cz/od/soubory/ciselniky/) | Occupations, geography, and vacancy attributes |

The exact codelist filenames are maintained in
[the downloader](../local/pipeline/bronze/codelists.py).

Each run stores unchanged JSON.gz files under today's Prague date in
`local/s3_doppelganger/bronze/mpsv/`. Existing non-empty files are reused.
The endpoints provide current data; the downloader cannot recover past dates.

Silver uses nine codelists; Gold exposes their attributes through dimensions.
See the [data model](data-model.md). Increment feeds and unemployment datasets
are not processed.

Raw vacancies can contain personal contact details. Downloaded data is ignored
by Git. Excluding the structured contact table from Silver does not anonymize
free-text fields.
