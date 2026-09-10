import pytest

from sa_engine import models


@pytest.fixture
def danger_zone():
    return models.Zone(
        id="danger-1",
        name="Synthetic Danger Area",
        zone_type=models.ZoneType.DANGER,
        lower=models.VerticalLimit(
            1000,
            models.VerticalUnit.FT,
            models.VerticalReference.STANDARD_PRESSURE,
        ),
        upper=models.VerticalLimit(
            6000,
            models.VerticalUnit.FT,
            models.VerticalReference.STANDARD_PRESSURE,
        ),
        polygon=[
            (24.90, 60.10),
            (25.00, 60.10),
            (25.00, 60.20),
            (24.90, 60.20),
        ],
        source="synthetic",
        activation_status=models.ActivationStatus.UNKNOWN,
    )

@pytest.fixture
def prohibited_zone():
    return models.Zone(
        id="prohibited-1",
        name="Synthetic Prohibited Area",
        zone_type=models.ZoneType.PROHIBITED,
        lower=models.VerticalLimit(
            1000,
            models.VerticalUnit.FT,
            models.VerticalReference.STANDARD_PRESSURE,
        ),
        upper=models.VerticalLimit(
            6000,
            models.VerticalUnit.FT,
            models.VerticalReference.STANDARD_PRESSURE,
        ),
        polygon=[
            (24.90, 60.10),
            (25.00, 60.10),
            (25.00, 60.20),
            (24.90, 60.20),
        ],
        source="synthetic",
        activation_status=models.ActivationStatus.UNKNOWN,
    )

@pytest.fixture
def restricted_zone():
    return models.Zone(
        id="restricted-1",
        name="Synthetic Restricted Area",
        zone_type=models.ZoneType.RESTRICTED,
        lower=models.VerticalLimit(
            1000,
            models.VerticalUnit.FT,
            models.VerticalReference.STANDARD_PRESSURE,
        ),
        upper=models.VerticalLimit(
            6000,
            models.VerticalUnit.FT,
            models.VerticalReference.STANDARD_PRESSURE,
        ),
        polygon=[
            (24.90, 60.10),
            (25.00, 60.10),
            (25.00, 60.20),
            (24.90, 60.20),
        ],
        source="synthetic",
        activation_status=models.ActivationStatus.UNKNOWN,
    )


@pytest.fixture
def agl_zone():
    return models.Zone(
        id="agl-1",
        name="Synthetic AGL Area",
        zone_type=models.ZoneType.DANGER,
        lower=models.VerticalLimit(
            0,
            models.VerticalUnit.FT,
            models.VerticalReference.GND,
        ),
        upper=models.VerticalLimit(
            6000,
            models.VerticalUnit.FT,
            models.VerticalReference.AGL,
        ),
        polygon=[
            (24.90, 60.10),
            (25.00, 60.10),
            (25.00, 60.20),
            (24.90, 60.20),
        ],
        source="synthetic",
        activation_status=models.ActivationStatus.UNKNOWN,
    )


@pytest.fixture
def msl_zone():
    return models.Zone(
        id="msl-1",
        name="Synthetic MSL Area",
        zone_type=models.ZoneType.DANGER,
        lower=models.VerticalLimit(
            1000,
            models.VerticalUnit.FT,
            models.VerticalReference.MSL,
        ),
        upper=models.VerticalLimit(
            6000,
            models.VerticalUnit.FT,
            models.VerticalReference.MSL,
        ),
        polygon=[
            (24.90, 60.10),
            (25.00, 60.10),
            (25.00, 60.20),
            (24.90, 60.20),
        ],
        source="synthetic",
        activation_status=models.ActivationStatus.UNKNOWN,
    )

@pytest.fixture
def aircraft_inside():
    return models.Aircraft(
        icao24="abc123",
        callsign="FIN123",
        lat=60.15,
        lon=24.95,
        baro_altitude_ft=3000,
        geo_altitude_ft=3100,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=1000,
        last_contact=1002,
        position_source=0,
        category=3,
    )

@pytest.fixture
def aircraft_outside():
    return models.Aircraft(
        icao24="outside1",
        callsign="OUT123",
        lat=60.30,
        lon=25.20,
        baro_altitude_ft=3000,
        geo_altitude_ft=3100,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=1000,
        last_contact=1002,
        position_source=0,
        category=3,
    )

@pytest.fixture
def aircraft_on_ground():
    return models.Aircraft(
        icao24="ground1",
        callsign="GND123",
        lat=60.15,
        lon=24.95,
        baro_altitude_ft=3000,
        geo_altitude_ft=3100,
        velocity=0,
        heading=270,
        on_ground=True,  # important difference
        time_position=1000,
        last_contact=1002,
        position_source=0,
        category=3,
    )


@pytest.fixture
def aircraft_stale():
    return models.Aircraft(
        icao24="stale1",
        callsign="OLD123",
        lat=60.15,
        lon=24.95,
        baro_altitude_ft=3000,
        geo_altitude_ft=3100,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=900,  # with now=1010 → 110 seconds old
        last_contact=902,
        position_source=0,
        category=3,
    )


@pytest.fixture
def aircraft_above():
    return models.Aircraft(
        icao24="above1",
        callsign="HIGH123",
        lat=60.15,
        lon=24.95,
        baro_altitude_ft=7000,  # zone upper limit is 6000
        geo_altitude_ft=7100,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=1000,
        last_contact=1002,
        position_source=0,
        category=3,
    )


@pytest.fixture
def aircraft_below():
    return models.Aircraft(
        icao24="below1",
        callsign="LOW123",
        lat=60.15,
        lon=24.95,
        baro_altitude_ft=500,  # zone lower limit is 1000
        geo_altitude_ft=600,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=1000,
        last_contact=1002,
        position_source=0,
        category=3,
    )


@pytest.fixture
def aircraft_on_boundary():
    return models.Aircraft(
        icao24="boundary1",
        callsign="EDGE123",
        lat=60.15,
        lon=24.90,  # exactly on left edge of polygon
        baro_altitude_ft=3000,
        geo_altitude_ft=3100,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=1000,
        last_contact=1002,
        position_source=0,
        category=3,
    )


@pytest.fixture
def aircraft_missing_altitude():
    return models.Aircraft(
        icao24="noalt1",
        callsign="NOALT",
        lat=60.15,
        lon=24.95,
        baro_altitude_ft=None,  # important difference
        geo_altitude_ft=3100,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=1000,
        last_contact=1002,
        position_source=0,
        category=3,
    )

@pytest.fixture
def aircraft_missing_time_position():
    return models.Aircraft(
        icao24="notime1",
        callsign="NOTIME",
        lat=60.15,
        lon=24.95,
        baro_altitude_ft=3000,
        geo_altitude_ft=3100,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=None,
        last_contact=1002,
        position_source=0,
        category=3,
    )


@pytest.fixture
def aircraft_missing_position():
    return models.Aircraft(
        icao24="nopos1",
        callsign="NOPOS",
        lat=None,
        lon=24.95,
        baro_altitude_ft=3000,
        geo_altitude_ft=3100,
        velocity=80,
        heading=270,
        on_ground=False,
        time_position=1000,
        last_contact=1002,
        position_source=0,
        category=3,
    )