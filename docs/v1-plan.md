# V1 plan: Czech Job Market Monitor

## Cíl V1

V1 bude malý, ale kompletní datový produkt. Každý den stáhne kompletní snapshot volných míst, porovná ho s předchozím dnem a ukáže:

- kolik pracovních míst je aktuálně otevřených,
- kolik jich přibylo a zmizelo,
- kde je největší poptávka,
- o jaké profese je zájem,
- jaké jsou nabízené mzdy,
- vztah mezi nabídkami a nezaměstnaností v regionech.

Nejde o real-time aplikaci. Je to denní analytická pipeline a portfolio ukázka AWS, datového modelování, kvality dat a Snowflake.

## Tok dat

```text
MPSV API
   ↓
S3 raw – původní JSON snapshoty
   ↓
Python transformace + kontroly kvality
   ↓
S3 processed – Parquet
   ↓
Snowflake – analytické tabulky
   ↓
Dashboard / veřejná prezentace
```

## Rozsah V1

### 1. Denní snapshot pracovních míst

Každý den uložíme celý soubor pod datum:

```text
s3://.../raw/vacancies/snapshot_date=2026-10-04/vacancies.json.gz
```

Full snapshot bude zdroj pravdy. Oficiální incrementy můžeme archivovat, ale nebudeme na nich stavět výsledný stav, protože obsahují duplicity a opožděné události.

### 2. Odvozené změny

Porovnáním dvou full snapshotů vytvoříme následující typy změn:

```text
NEW
REMOVED
CHANGED
UNCHANGED
```

Identifikátorem nabídky bude `portalId`. Tak získáme spolehlivou historii od okamžiku spuštění projektu.

### 3. Datové vrstvy

#### Raw

Původní soubory beze změny. Slouží pro audit a opakované zpracování.

#### Silver

Vyčištěné tabulky:

- `vacancy_snapshot`
- `vacancy_location`
- `vacancy_work_relationship`
- `vacancy_education`
- `vacancy_benefit`
- `vacancy_daily_change`
- `unemployment_monthly`
- `dim_location`
- `dim_occupation`

Vnořená pole z JSONu budou v samostatných tabulkách. Jedna nabídka totiž může mít více pracovních vztahů, benefitů nebo požadavků.

#### Gold

Tabulky přímo pro dashboard:

- `daily_market_overview`
- `daily_region_metrics`
- `daily_occupation_metrics`
- `monthly_region_labour_market`

Příklad struktury regionální denní metriky:

```text
snapshot_date
region
active_vacancies
new_vacancies
removed_vacancies
median_salary_from
employers_count
```

## Dashboard V1

### 1. Overview

- aktivní nabídky,
- nová a odstraněná místa,
- počet zaměstnavatelů,
- vývoj v čase.

### 2. Mapa a regiony

- nabídky podle kraje a okresu,
- nabídky na počet nezaměstnaných.

### 3. Profese

- nejžádanější CZ-ISCO profese,
- změna poptávky v čase,
- mzdy podle profese.

### 4. Data quality

- datum posledního načtení,
- počet vstupních řádků,
- duplicity,
- chybějící hodnoty,
- neplatné mzdy nebo data.

Ve veřejném výstupu nebudeme publikovat kontaktní osoby, telefony, e-maily ani celý původní JSON.

## Postup implementace

### Fáze 1 – lokální prototyp

V Jupyteru:

1. načíst celý full JSON,
2. vybrat sloupce potřebné pro V1,
3. rozbalit vnořené struktury,
4. vytvořit první čisté DataFrame,
5. uložit výsledek do Parquetu,
6. ověřit datové typy, klíče a duplicity.

Výstup:

```text
data/processed/vacancy_snapshot.parquet
```

### Fáze 2 – porovnání snapshotů

Až budeme mít dva snapshoty, vytvoříme funkci:

```python
compare_snapshots(previous_df, current_df)
```

Výsledkem bude tabulka denních změn:

```text
snapshot_date
portal_id
change_type
changed_columns
```

Tady vznikne hlavní technická hodnota projektu.

### Fáze 3 – opakovatelná Python pipeline

Notebook převedeme do samostatných kroků:

```text
download
validate
transform
compare
publish
```

Každý krok musí jít spustit z příkazové řádky a opakované spuštění nesmí vytvářet duplicity.

### Fáze 4 – AWS

Fungující lokální pipeline přeneseme do AWS:

- S3 pro raw a processed data,
- EventBridge pro denní spuštění,
- Step Functions pro řízení kroků,
- ECS Fargate nebo Lambda podle skutečné paměťové náročnosti,
- CloudWatch pro logy a alerty,
- Glue Catalog a Athena pro kontrolu Parquetů.

### Fáze 5 – Snowflake

Snowflake bude načítat připravené Parquety ze S3. V něm vytvoříme:

- staging tabulky,
- silver model,
- gold metriky,
- incremental load,
- testy unikátnosti a referenční integrity.

Snowflake nebude obsluhovat každý veřejný request. Bude analytickou a transformační vrstvou.

### Fáze 6 – prezentace

Nakonec připravíme:

- jednoduchý dashboard,
- architektonický diagram,
- README s rozhodnutími a omezeními,
- ukázky datové kvality,
- náklady na provoz,
- screenshoty a demo.

## Bezprostřední další krok

Vytvořit notebook:

```text
notebooks/01_build_vacancy_snapshot.ipynb
```

Notebook bude dělat pouze následující:

```text
full JSON
→ výběr relevantních polí
→ základní čištění
→ normalizace datových typů
→ kontrola klíče portalId
→ vacancy_snapshot.parquet
```

Nejdřív postavíme jednu kvalitní tabulku `vacancy_snapshot`. AWS, Snowflake a dashboard začneme řešit až poté, co bude přesně definované a ověřené její výsledné schéma.
