from enum import Enum


class PromoterOrganisation(Enum):
    NORTHUMBRIAN_WATER = "Northumbrian Water"
    NORTHERN_GAS_NETWORKS = "Northern Gas Networks"
    NEWCASTLE_CITY_COUNCIL = "Newcastle City Council"
    DURHAM_COUNTY_COUNCIL = "Durham County Council"

    def __str__(self) -> str:
        return self.value


class SWACode(Enum):
    NORTHUMBRIAN_WATER = ("SWA001", "Northumbrian Water")
    NORTHERN_GAS_NETWORKS = ("SWA002", "Northern Gas Networks")
    NEWCASTLE_CITY_COUNCIL = ("SWA003", "Newcastle City Council")
    DURHAM_COUNTY_COUNCIL = ("SWA004", "Durham County Council")

    def __init__(self, code: str, name: str):
        self.code = code
        self.display_name = name

    @property
    def label(self) -> str:
        return f"{self.code} - {self.display_name}"


class LocationType(Enum):
    FOOTWAY = ("footway", "Footway", 3)
    CARRIAGEWAY = ("carriageway", "Carriageway", 10)
    VERGE = ("verge", "Verge", 6)
    MIX = ("mix", "Mix", 15)

    def __init__(self, code: str, display_name: str, score: int):
        self.code = code
        self.display_name = display_name
        self.score = score

    @property
    def label(self) -> str:
        return f"{self.display_name} (Score: {self.score})"


class SectorType(Enum):
    WATER = ("water", "Water", 10)
    TELCO = ("telco", "Telecommunications", 2)
    GAS = ("gas", "Gas", 8)
    ELECTRICITY = ("electricity", "Electricity", 5)
    HIGHWAY = ("highway", "Highway", 5)

    def __init__(self, code: str, display_name: str, score: int):
        self.code = code
        self.display_name = display_name
        self.score = score

    @property
    def label(self) -> str:
        return f"{self.display_name} (Dig depth: {self.score}m)"


class ActivityType(Enum):
    NEW_INSTALLATION = ("new_installation", "New Installation")
    FULL_REPLACEMENT = ("full_replacement", "Full Replacement")
    PARTIAL_REPLACEMENT = ("partial_replacement", "Partial Replacement")
    UPGRADE = ("upgrade", "Upgrade")
    REPAIR = ("repair", "Repair")
    REMOVAL = ("removal", "Removal")
    ABANDONMENT = ("abandonment", "Abandonment")
    RELOCATION = ("relocation", "Relocation")
    PROTECTION_WORKS = ("protection_works", "Protection Works")
    SURVEY_INVESTIGATION = ("survey_investigation", "Survey/Investigation")
    CYCLE_LANE_INSTALLATION = ("cycle_lane_installation", "Cycle Lane Installation")
    CYCLE_PATH_CONSTRUCTION = ("cycle_path_construction", "Cycle Path Construction")
    CYCLE_CROSSING_UPGRADE = ("cycle_crossing_upgrade", "Cycle Crossing Upgrade")
    OTHER = ("other", "Other")

    def __init__(self, code: str, display_name: str):
        self.code = code
        self.display_name = display_name


class ProgrammeType(Enum):
    CAPITAL_INVESTMENT = ("capital_investment", "Capital Investment")
    ROUTINE_MAINTENANCE = ("routine_maintenance", "Routine Maintenance")
    EMERGENCY_PREPAREDNESS = ("emergency_preparedness", "Emergency Preparedness")
    NETWORK_EXPANSION = ("network_expansion", "Network Expansion")
    ASSET_REPLACEMENT = ("asset_replacement", "Asset Replacement")
    REGULATORY_COMPLIANCE = ("regulatory_compliance", "Regulatory Compliance")
    CUSTOMER_CONNECTION = ("customer_connection", "Customer Connection")
    NETWORK_REINFORCEMENT = ("network_reinforcement", "Network Reinforcement")
    CYCLE_NETWORK_DEVELOPMENT = (
        "cycle_network_development",
        "Cycle Network Development",
    )
    ACTIVE_TRAVEL_SCHEME = ("active_travel_scheme", "Active Travel Scheme")
    OTHER = ("other", "Other")

    def __init__(self, code: str, display_name: str):
        self.code = code
        self.display_name = display_name


class TTRORequired(Enum):
    YES = ("yes", "Yes", 10)
    NO = ("no", "No", 5)

    def __init__(self, code: str, display_name: str, score: int):
        self.code = code
        self.display_name = display_name
        self.score = score

    @property
    def label(self) -> str:
        return f"{self.display_name} (Score: {self.score})"


class InstallationMethod(Enum):
    OPEN_CUT = ("open_cut", "Open Cut", 10)
    DIRECTIONAL_DRILLING = ("directional_drilling", "Directional Drilling", 5)
    MOLING = ("moling", "Moling", 4)
    TUNNELLING = ("tunnelling", "Tunnelling", 4)
    THRUST_BORING = ("thrust_boring", "Thrust Boring", 2)
    PIPE_JACKING = ("pipe_jacking", "Pipe Jacking", 2)
    SLIP_LINING = ("slip_lining", "Slip Lining", 2)
    PIPE_BURSTING = ("pipe_bursting", "Pipe Bursting", 5)
    TRENCHING = ("trenching", "Trenching", 6)
    OTHER = ("other", "Other", 5)

    def __init__(self, code: str, display_name: str, score: int):
        self.code = code
        self.display_name = display_name
        self.score = score

    @property
    def label(self) -> str:
        return f"{self.display_name} (Score: {self.score})"


# Helper functions for Streamlit integration
def get_enum_options(enum_class) -> list:
    """Get list of enum values for selectbox options"""
    return list(enum_class)


def get_enum_labels(enum_class) -> dict:
    """Get mapping of enum values to display labels"""
    return {item: item.display_name for item in enum_class}


def get_enum_with_labels(enum_class) -> dict:
    """Get mapping with special label handling (for SectorType)"""
    if hasattr(list(enum_class)[0], "label"):
        return {item: item.label for item in enum_class}
    return get_enum_labels(enum_class)
