from pipeline.gold.tables.bridge_vacancy_region import BridgeVacancyRegionTable
from pipeline.gold.tables.dim_contact_office import DimContactOfficeTable
from pipeline.gold.tables.dim_employer import DimEmployerTable
from pipeline.gold.tables.dim_municipality import DimMunicipalityTable
from pipeline.gold.tables.dim_occupation import DimOccupationTable
from pipeline.gold.tables.dim_publish_type import DimPublishTypeTable
from pipeline.gold.tables.dim_region import DimRegionTable
from pipeline.gold.tables.dim_salary_type import DimSalaryTypeTable
from pipeline.gold.tables.dim_shift_pattern import DimShiftPatternTable
from pipeline.gold.tables.dim_work_location_type import DimWorkLocationTypeTable
from pipeline.gold.tables.fact_vacancy_snapshot import FactVacancySnapshotTable

__all__ = [
    "BridgeVacancyRegionTable",
    "DimContactOfficeTable",
    "DimEmployerTable",
    "DimMunicipalityTable",
    "DimOccupationTable",
    "DimPublishTypeTable",
    "DimRegionTable",
    "DimSalaryTypeTable",
    "DimShiftPatternTable",
    "DimWorkLocationTypeTable",
    "FactVacancySnapshotTable",
]
