
from sa_engine import models
from sa_engine.geometry import find_alerts

aircraft = models.Aircraft(
    icao24="abc123",
    callsign="FIN123",
    lat=60.17,
    lon=24.94,
    baro_altitude_ft=5000,
    geo_altitude_ft=5100,
    velocity=80,
    heading=270,
    on_ground=False,
    time_position=1757410200,
    last_contact=1757410203,
    position_source=0,
    category=3,
)

zone = models.Zone(
    id="demo-zone-1",
    name="Synthetic Danger Area",
    zone_type=models.ZoneType.DANGER,
    lower=models.VerticalLimit(
        1000,
        models.VerticalUnit.FT,
        models.VerticalReference.MSL,
    ),
    upper=models.VerticalLimit(
        65,
        models.VerticalUnit.FL,
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

find_alerts(
    aircraft,
    [zone],
    now=1757410210,
)