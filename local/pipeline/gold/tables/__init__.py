from pipeline.gold.tables.bridge_vacancy_region import BridgeVacancyRegionTable
from pipeline.gold.tables.dim_occupation import DimOccupationTable
from pipeline.gold.tables.dim_region import DimRegionTable
from pipeline.gold.tables.dim_salary_type import DimSalaryTypeTable
from pipeline.gold.tables.fact_vacancy_snapshot import FactVacancySnapshotTable

__all__ = [
    "BridgeVacancyRegionTable",
    "DimOccupationTable",
    "DimRegionTable",
    "DimSalaryTypeTable",
    "FactVacancySnapshotTable",
]
