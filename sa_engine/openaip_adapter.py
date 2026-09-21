from math import isfinite

from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, Polygon, shape

from sa_engine.models import (
    ActivationStatus,
    VerticalLimit,
    VerticalReference,
    VerticalUnit,
    Zone,
    ZoneType,
)

OPENAIP_VERTICAL_UNIT_MAP = {
    1: VerticalUnit.FT,
    6: VerticalUnit.FL,
}

OPENAIP_VERTICAL_REFERENCE_MAP = {
    0: VerticalReference.GND,
    1: VerticalReference.MSL,
    2: VerticalReference.STANDARD_PRESSURE,
}

OPENAIP_ZONE_TYPE_MAP = {
    1: ZoneType.RESTRICTED,
    2: ZoneType.DANGER,
    3: ZoneType.PROHIBITED,
}


def parse_zone_type(raw_type: int) -> ZoneType:
    try:
        return OPENAIP_ZONE_TYPE_MAP[raw_type]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported OpenAIP airspace type: {raw_type}"
        ) from exc

def parse_vertical_limit(raw_limit: dict) -> VerticalLimit:
    value = raw_limit["value"]
    raw_unit = raw_limit["unit"]
    raw_reference = raw_limit["referenceDatum"]

    if value == 999 and raw_unit == 6 and raw_reference == 2:
        return VerticalLimit(
            value=None,
            unit=None,
            reference=None,
            unlimited=True,
        )

    try:
        unit = OPENAIP_VERTICAL_UNIT_MAP[raw_unit]
        reference = OPENAIP_VERTICAL_REFERENCE_MAP[raw_reference]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported OpenAIP vertical limit: {raw_limit}"
        ) from exc

    return VerticalLimit(
        value=value,
        unit=unit,
        reference=reference,
    )

def parse_geometry(raw_geometry: dict) -> Polygon | MultiPolygon:
    """Parse a valid, nonempty polygonal geometry in (longitude, latitude) order."""
    try:
        geometry = shape(raw_geometry)
    except (AttributeError, KeyError, TypeError, ValueError, GEOSException) as exc:
        raise ValueError(
            f"Invalid OpenAIP geometry: {raw_geometry}"
        ) from exc

    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise ValueError(
            f"Unsupported OpenAIP geometry type: {geometry.geom_type}"
        )

    if geometry.is_empty:
        raise ValueError("OpenAIP geometry must not be empty")

    if not geometry.is_valid:
        raise ValueError("OpenAIP geometry is invalid")

    return geometry


def parse_zone(raw_zone: dict) -> Zone:
    """Convert one OpenAIP item to a Zone, or raise ValueError.

    Extra metadata is ignored. Activation cannot be inferred from this record.
    The input is not modified; no HTTP or detection logic runs here.
    """
    if not isinstance(raw_zone, dict):
        raise ValueError("OpenAIP zone must be an object")

    required = ("_id", "name", "type", "lowerLimit", "upperLimit", "geometry")
    for field in required:
        if field not in raw_zone:
            raise ValueError(f"Missing OpenAIP zone field: {field}")
    for field in ("_id", "name"):
        if not isinstance(raw_zone[field], str) or not raw_zone[field].strip():
            raise ValueError(f"OpenAIP {field} must be a nonempty string")
    if type(raw_zone["type"]) is not int:
        raise ValueError("OpenAIP type must be an integer")

    # Validate JSON shapes here; enum mappings remain in the existing parsers.
    for field in ("lowerLimit", "upperLimit"):
        limit = raw_zone[field]
        if not isinstance(limit, dict):
            raise ValueError(f"OpenAIP {field} must be an object")
        for key in ("value", "unit", "referenceDatum"):
            if key not in limit:
                raise ValueError(f"Missing OpenAIP {field} field: {key}")
        value = limit["value"]
        if type(value) not in (int, float) or not isfinite(value):
            raise ValueError(f"OpenAIP {field} value must be a finite number")
        if any(type(limit[key]) is not int for key in ("unit", "referenceDatum")):
            raise ValueError(f"OpenAIP {field} unit and referenceDatum must be integers")

    return Zone(
        id=raw_zone["_id"],
        name=raw_zone["name"],
        zone_type=parse_zone_type(raw_zone["type"]),
        lower=parse_vertical_limit(raw_zone["lowerLimit"]),
        upper=parse_vertical_limit(raw_zone["upperLimit"]),
        polygon=parse_geometry(raw_zone["geometry"]),
        source="openaip",
        activation_status=ActivationStatus.UNKNOWN,
    )


def parse_supported_zones(records: list[dict]) -> tuple[list[Zone], dict[int, int]]:
    """Select supported P/R/D types; count other integer types, fail malformed data."""
    zones = []
    unsupported = {}
    for index, raw in enumerate(records):
        if not isinstance(raw, dict) or type(raw.get('type')) is not int:
            raise ValueError(f'OpenAIP record {index}: type must be an integer')
        raw_type = raw['type']
        if raw_type not in OPENAIP_ZONE_TYPE_MAP:
            unsupported[raw_type] = unsupported.get(raw_type, 0) + 1
            continue
        try:
            zones.append(parse_zone(raw))
        except ValueError as exc:
            raise ValueError(f'OpenAIP record {index}, id={raw.get("_id")!r}: {exc}') from exc
    return zones, unsupported
