import pytest

from sa_engine import models
from sa_engine.altitude import can_compare


def test_to_feet_from_ft():
    limit = models.VerticalLimit(
        value=1500,
        unit=models.VerticalUnit.FT,
        reference=models.VerticalReference.MSL,
    )

    converted = limit.to_feet()

    assert converted.value == 1500
    assert converted.unit is models.VerticalUnit.FT
    assert converted.reference is models.VerticalReference.MSL


def test_to_feet_from_metres():
    limit = models.VerticalLimit(
        value=500,
        unit=models.VerticalUnit.M,
        reference=models.VerticalReference.AGL,
    )

    converted = limit.to_feet()

    assert converted.value == pytest.approx(1640.42)
    assert converted.unit is models.VerticalUnit.FT
    assert converted.reference is models.VerticalReference.AGL


def test_to_feet_from_flight_level():
    limit = models.VerticalLimit(
        value=65,
        unit=models.VerticalUnit.FL,
        reference=models.VerticalReference.STANDARD_PRESSURE,
    )

    converted = limit.to_feet()

    assert converted.value == 6500
    assert converted.unit is models.VerticalUnit.FT
    assert converted.reference is models.VerticalReference.STANDARD_PRESSURE


def test_agl_limit_is_not_comparable(aircraft_inside):
    limit = models.VerticalLimit(
        value=1000,
        unit=models.VerticalUnit.FT,
        reference=models.VerticalReference.AGL,
    )

    result = can_compare(aircraft_inside, limit)

    assert result is models.Comparability.UNKNOWN


def test_missing_altitude_is_unknown(aircraft_missing_altitude):
    limit = models.VerticalLimit(
        value=5000,
        unit=models.VerticalUnit.FT,
        reference=models.VerticalReference.STANDARD_PRESSURE,
    )

    result = can_compare(aircraft_missing_altitude, limit)

    assert result is models.Comparability.UNKNOWN


def test_baro_vs_msl_is_approximate(aircraft_inside):
    limit = models.VerticalLimit(
        value=3000,
        unit=models.VerticalUnit.FT,
        reference=models.VerticalReference.MSL,
    )

    result = can_compare(aircraft_inside, limit)

    assert result is models.Comparability.APPROXIMATE


def test_baro_vs_fl_is_comparable(aircraft_inside):
    limit = models.VerticalLimit(
        value=60,
        unit=models.VerticalUnit.FL,
        reference=models.VerticalReference.STANDARD_PRESSURE,
    )

    result = can_compare(aircraft_inside, limit)

    assert result is models.Comparability.COMPARABLE

def test_ground_limit_is_comparable(aircraft_inside):
    limit = models.VerticalLimit(
        value=0,
        unit=models.VerticalUnit.FT,
        reference=models.VerticalReference.GND,
    )

    result = can_compare(aircraft_inside, limit)

    assert result is models.Comparability.COMPARABLE
