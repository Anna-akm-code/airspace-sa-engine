from sa_engine import models
from sa_engine.altitude import can_compare

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


limit_fl = models.VerticalLimit(
    65,
    models.VerticalUnit.FL,
    models.VerticalReference.STANDARD_PRESSURE,
)

limit_msl = models.VerticalLimit(
    5000,
    models.VerticalUnit.FT,
    models.VerticalReference.MSL,
)

limit_agl = models.VerticalLimit(
    500,
    models.VerticalUnit.FT,
    models.VerticalReference.AGL,
)


print(can_compare(aircraft, limit_fl))
print(can_compare(aircraft, limit_msl))
print(can_compare(aircraft, limit_agl))
