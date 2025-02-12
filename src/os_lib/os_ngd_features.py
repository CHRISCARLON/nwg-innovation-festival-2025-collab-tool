from typing import List
from enum import Enum

class NGDFeaturesAPI(Enum):
    def __init__(self, *args):
        self._value_ = args

    def __iter__(self):
        return iter(self.value)

    def as_list(self) -> List[str]:
        return list(self.value)

    BLD = (
        "bld-fts-building-1",
        "bld-fts-buildingline-1",
        "bld-fts-buildingpart-1"
    )

    GNM = (
        "gnm-fts-namedarea-1",
        "gnm-fts-namedpoint-1"
    )

    LND = (
        "lnd-fts-land-1",
        "lnd-fts-landpoint-1",
        "lnd-fts-landform-1",
        "lnd-fts-landformline-1",
        "lnd-fts-landformpoint-1"
    )

    LUS = (
        "lus-fts-site-1",
        "lus-fts-siteaccesslocation-1",
        "lus-fts-siteroutingpoint-1"
    )

    STR = (
        "str-fts-compoundstructure-1",
        "str-fts-structure-1",
        "str-fts-structureline-1",
        "str-fts-structurepoint-1"
    )

    TRN = (
        "trn-fts-cartographicraildetail-1",
        "trn-fts-rail-1",
        "trn-fts-roadline-1",
        "trn-fts-roadtrackorpath-1"
    )

    NTWK = (
        "trn-ntwk-connectinglink-1",
        "trn-ntwk-connectingnode-1",
        "trn-ntwk-ferrylink-1",
        "trn-ntwk-ferrynode-1",
        "trn-ntwk-ferryterminal-1",
        "trn-ntwk-path-1",
        "trn-ntwk-pathlink-1",
        "trn-ntwk-pathnode-1",
        "trn-ntwk-railwaylink-1",
        "trn-ntwk-railwaylinkset-1",
        "trn-ntwk-railwaynode-1",
        "trn-ntwk-pavementlink-1",
        "trn-ntwk-road-1",
        "trn-ntwk-roadjunction-1",
        "trn-ntwk-roadlink-1",
        "trn-ntwk-roadnode-1",
        "trn-ntwk-street-1"
    )

    RAMI = (
        "trn-rami-averageandindicativespeed-1",
        "trn-rami-highwaydedication-1",
        "trn-rami-maintenancearea-1",
        "trn-rami-maintenanceline-1",
        "trn-rami-maintenancepoint-1",
        "trn-rami-reinstatementarea-1",
        "trn-rami-reinstatementline-1",
        "trn-rami-reinstatementpoint-1",
        "trn-rami-restriction-1",
        "trn-rami-routinghazard-1",
        "trn-rami-routingstructure-1",
        "trn-rami-specialdesignationarea-1",
        "trn-rami-specialdesignationline-1",
        "trn-rami-specialdesignationpoint-1"
    )

    WTR = (
        "wtr-fts-intertidalline-1",
        "wtr-fts-tidalboundary-1",
        "wtr-fts-water-1",
        "wtr-fts-waterpoint-1"
    )

    NTWK_WATER = (
        "trn-ntwk-waterlink-1",
        "trn-ntwk-waterlinkset-1",
        "trn-ntwk-waternode-1"
    )

    @classmethod
    def all_groups(cls) -> List[str]:
        return [member.name for member in cls]

    @classmethod
    def all_datasets(cls) -> List[str]:
        return [dataset for member in cls for dataset in member.value]
