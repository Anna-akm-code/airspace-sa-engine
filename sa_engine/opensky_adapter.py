"""OpenSky extended positional state vectors -> existing Aircraft domain model."""

from math import isfinite

from .models import Aircraft

METRES_TO_FEET = 3.28084  # Same conversion factor as VerticalLimit.to_feet().


def _number(value, field):
    if value is None:
        return None
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError(f"OpenSky {field} must be finite numeric data or null")
    return value


def _integer(value, field, *, nullable=False):
    if nullable and value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError(f"OpenSky {field} must be a nonnegative integer")
    return value


def parse_state_vector(raw: list) -> Aircraft | None:
    """Parse 18 extended fields; ignore appended fields for forward compatibility.

    All mapped fields are validated before filtering missing coordinates. Null
    longitude OR latitude returns None; malformed rows raise ValueError. Blank
    callsigns become None. Missing altitude never causes filtering.
    """
    if not isinstance(raw, list) or len(raw) < 18:
        raise ValueError("OpenSky extended state vector requires at least 18 fields")
    icao24 = raw[0]
    if (not isinstance(icao24, str) or len(icao24) != 6
            or any(c not in "0123456789abcdefABCDEF" for c in icao24)):
        raise ValueError("OpenSky icao24 must be a six-character hexadecimal string")
    callsign = raw[1]
    if callsign is not None:
        if not isinstance(callsign, str):
            raise ValueError("OpenSky callsign must be a string or null")
        callsign = callsign.strip() or None
    time_position = _integer(raw[3], "time_position", nullable=True)
    last_contact = _integer(raw[4], "last_contact")
    lon = _number(raw[5], "longitude")
    lat = _number(raw[6], "latitude")
    if lon is not None and not -180 <= lon <= 180:
        raise ValueError("OpenSky longitude is outside WGS84 bounds")
    if lat is not None and not -90 <= lat <= 90:
        raise ValueError("OpenSky latitude is outside WGS84 bounds")
    baro = _number(raw[7], "baro_altitude")
    if type(raw[8]) is not bool:
        raise ValueError("OpenSky on_ground must be boolean")
    velocity = _number(raw[9], "velocity")
    heading = _number(raw[10], "true_track")
    geo = _number(raw[13], "geo_altitude")
    position_source = _integer(raw[16], "position_source")
    category = _integer(raw[17], "category", nullable=True)
    # Preserve source/category codes; interpreting them is not detection logic.
    baro_ft = None if baro is None else baro * METRES_TO_FEET
    geo_ft = None if geo is None else geo * METRES_TO_FEET
    for value in (baro_ft, geo_ft):
        if value is not None and not isfinite(value):
            raise ValueError("OpenSky converted altitude must be finite")
    if lon is None or lat is None:
        return None
    return Aircraft(
        icao24=icao24, callsign=callsign, lat=lat, lon=lon,
        baro_altitude_ft=baro_ft, geo_altitude_ft=geo_ft,
        velocity=velocity, heading=heading, on_ground=raw[8],
        time_position=time_position, last_contact=last_contact,
        position_source=position_source, category=category,
    )


def parse_states(states: list | None) -> tuple[list[Aircraft], int]:
    """Return (aircraft, missing-position count). Fail on malformed rows.

    The explicit count makes filtering visible to callers. No partial result is
    returned on failure. Null states is an empty response, not a malformed row.
    """
    if states is None:
        return [], 0
    if not isinstance(states, list):
        raise ValueError("OpenSky states must be an array or null")
    aircraft = []
    skipped = 0
    for index, raw in enumerate(states):
        try:
            item = parse_state_vector(raw)
        except ValueError as exc:
            raise ValueError(f"OpenSky state row {index}: {exc}") from exc
        if item is None:
            skipped += 1
        else:
            aircraft.append(item)
    return aircraft, skipped
