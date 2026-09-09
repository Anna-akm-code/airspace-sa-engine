from dataclasses import dataclass
from enum import Enum


class VerticalUnit(Enum):
    FT = "ft"
    M = "m"
    FL = "fl"


class VerticalReference(Enum):
    MSL = "msl"
    AGL = "agl"
    STANDARD_PRESSURE = "standard_pressure"
    GND = "gnd"


class ZoneType(Enum):  # what the airspace is
    PROHIBITED = "prohibited"
    RESTRICTED = "restricted"
    DANGER = "danger"


class ActivationStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class Comparability(Enum):  # whether two altitude references can sensibly be compared
    COMPARABLE = "comparable"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class AlertType(Enum):  # what happened
    PROHIBITED_AREA_ENTRY = "prohibited_area_entry"
    RESTRICTED_AREA_ENTRY = "restricted_area_entry"
    DANGER_AREA_EXPOSURE = "danger_area_exposure"


class VerificationStatus(Enum):  # how certain we are
    POTENTIAL = "potential"
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"


class DataQuality(Enum):  # how trustworthy/complete the input data is
    OK = "ok"
    STALE = "stale"
    NO_ALTITUDE = "no_altitude"
    VERTICAL_UNKNOWN = "vertical_unknown"


@dataclass
class Aircraft:
    icao24: str
    callsign: str | None
    lat: float | None
    lon: float | None
    baro_altitude_ft: float | None
    geo_altitude_ft: float | None
    velocity: float | None
    heading: float | None
    on_ground: bool
    time_position: int | None
    last_contact: int
    position_source: int
    category: int | None


@dataclass
class VerticalLimit:
    value: float
    unit: VerticalUnit
    reference: VerticalReference

    def to_feet(self):
        if self.unit == VerticalUnit.FT:
            return VerticalLimit(self.value, VerticalUnit.FT, self.reference)
        elif self.unit == VerticalUnit.M:
            return VerticalLimit(self.value * 3.28084, VerticalUnit.FT, self.reference)
        elif self.unit == VerticalUnit.FL:
            return VerticalLimit(self.value * 100, VerticalUnit.FT, self.reference)

@dataclass
class Zone:
    """Airspace zone polygon uses coordinate order (longitude, latitude).many geospatial libraries and formats use coordinates in lon, lat order:"""
    id: str
    name: str
    zone_type: ZoneType
    lower: VerticalLimit
    upper: VerticalLimit
    polygon: list[tuple[float, float]]
    source: str
    activation_status: ActivationStatus # some restricted/danger areas are not active all the time. They may only apply during certain hours, by NOTAM, or when activated for a specific operation.

@dataclass
class AirspaceAlert:
    aircraft: Aircraft
    zone: Zone
    alert_type: AlertType
    verification_status: VerificationStatus
    data_quality: DataQuality
    distance_to_boundary_m: float | None
    reason: str    