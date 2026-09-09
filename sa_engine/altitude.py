from .models import (
    Aircraft,
    Comparability,
    VerticalLimit,
    VerticalReference,
    VerticalUnit,
)


# Are the aircraft altitude and this vertical limit compatible enough to compare?
def can_compare(
    aircraft: Aircraft,
    limit: VerticalLimit,
) -> Comparability:
    """Decide whether aircraft barometric altitude can be compared with a vertical limit."""
    if (
        aircraft.baro_altitude_ft is None
    ):  # Same as, but preferred to: if aircraft.baro_altitude_ft == None:
        return Comparability.UNKNOWN
    elif limit.reference == VerticalReference.GND:
        return Comparability.COMPARABLE
    elif limit.reference == VerticalReference.AGL:
        return Comparability.UNKNOWN

    elif (
        limit.unit == VerticalUnit.FL
        or limit.reference == VerticalReference.STANDARD_PRESSURE
    ):
        return Comparability.COMPARABLE

    elif limit.reference == VerticalReference.MSL:
        return Comparability.APPROXIMATE
    return Comparability.UNKNOWN
