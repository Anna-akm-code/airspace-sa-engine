from sa_engine import models
from sa_engine.geometry import find_alerts


def test_aircraft_inside_zone_creates_alert(danger_zone, aircraft_inside):
    alerts = find_alerts(
        aircraft_inside,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 1


def test_aircraft_outside_zone_creates_no_alert(danger_zone, aircraft_outside):
    alerts = find_alerts(
        aircraft_outside,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 0    

def test_aircraft_on_ground_creates_no_alert(danger_zone, aircraft_on_ground):
    alerts = find_alerts(
        aircraft_on_ground,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 0


def test_stale_position_is_not_alerted(danger_zone, aircraft_stale):
    alerts = find_alerts(
        aircraft_stale,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 0


def test_aircraft_above_vertical_band_creates_no_alert(
    danger_zone,
    aircraft_above,
):
    alerts = find_alerts(
        aircraft_above,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 0


def test_aircraft_below_vertical_band_creates_no_alert(
    danger_zone,
    aircraft_below,
):
    alerts = find_alerts(
        aircraft_below,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 0


def test_aircraft_exactly_on_zone_boundary_creates_alert(
    danger_zone,
    aircraft_on_boundary,
):
    alerts = find_alerts(
        aircraft_on_boundary,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 1


def test_danger_area_yields_exposure_not_entry(
    danger_zone,
    aircraft_inside,
):
    alerts = find_alerts(
        aircraft_inside,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 1
    assert alerts[0].alert_type is models.AlertType.DANGER_AREA_EXPOSURE
    assert alerts[0].alert_type is not models.AlertType.PROHIBITED_AREA_ENTRY


def test_missing_altitude_still_reports_horizontal_containment(
    danger_zone,
    aircraft_missing_altitude,
):
    alerts = find_alerts(
        aircraft_missing_altitude,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 1
    assert alerts[0].verification_status is models.VerificationStatus.UNKNOWN
    assert alerts[0].data_quality is models.DataQuality.NO_ALTITUDE    


def test_prohibited_zone_yields_prohibited_entry(
    prohibited_zone,
    aircraft_inside,
):
    alerts = find_alerts(
        aircraft_inside,
        [prohibited_zone],
        now=1010,
    )

    assert len(alerts) == 1
    assert alerts[0].alert_type is models.AlertType.PROHIBITED_AREA_ENTRY



def test_missing_time_position_creates_no_alert(
    danger_zone,
    aircraft_missing_time_position,
):
    alerts = find_alerts(
        aircraft_missing_time_position,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 0


def test_missing_position_creates_no_alert(
    danger_zone,
    aircraft_missing_position,
):
    alerts = find_alerts(
        aircraft_missing_position,
        [danger_zone],
        now=1010,
    )

    assert len(alerts) == 0


def test_restricted_zone_yields_restricted_entry(
    restricted_zone,
    aircraft_inside,
):
    alerts = find_alerts(
        aircraft_inside,
        [restricted_zone],
        now=1010,
    )

    assert len(alerts) == 1
    assert alerts[0].alert_type is models.AlertType.RESTRICTED_AREA_ENTRY


def test_agl_zone_reports_vertical_unknown(
    agl_zone,
    aircraft_inside,
):
    alerts = find_alerts(
        aircraft_inside,
        [agl_zone],
        now=1010,
    )

    assert len(alerts) == 1
    assert alerts[0].verification_status is models.VerificationStatus.UNKNOWN
    assert alerts[0].data_quality is models.DataQuality.VERTICAL_UNKNOWN


def test_msl_zone_creates_potential_alert(
    msl_zone,
    aircraft_inside,
):
    alerts = find_alerts(
        aircraft_inside,
        [msl_zone],
        now=1010,
    )

    assert len(alerts) == 1
    assert alerts[0].verification_status is models.VerificationStatus.POTENTIAL


def test_aircraft_inside_zone_with_unlimited_upper_boundary():
    aircraft = models.Aircraft(
        icao24="abc123",
        callsign="TEST",
        lat=60.5,
        lon=24.5,
        baro_altitude_ft=50000,
        geo_altitude_ft=None,
        velocity=None,
        heading=None,
        on_ground=False,
        time_position=1000,
        last_contact=1000,
        position_source=0,
        category=None,
    )

    zone = models.Zone(
        id="unlimited-zone",
        name="Unlimited Restricted Zone",
        zone_type=models.ZoneType.RESTRICTED,
        lower=models.VerticalLimit(
            value=0,
            unit=models.VerticalUnit.FT,
            reference=models.VerticalReference.GND,
        ),
        upper=models.VerticalLimit(
            value=None,
            unit=None,
            reference=None,
            unlimited=True,
        ),
        polygon=[
            (24.0, 60.0),
            (25.0, 60.0),
            (25.0, 61.0),
            (24.0, 61.0),
        ],
        source="test",
        activation_status=models.ActivationStatus.ACTIVE,
    )

    alerts = find_alerts(
        aircraft=aircraft,
        zones=[zone],
        now=1000,
    )

    assert len(alerts) == 1
    assert alerts[0].verification_status is models.VerificationStatus.CONFIRMED
    assert alerts[0].data_quality is models.DataQuality.OK    

def test_aircraft_below_lower_boundary_of_unlimited_zone_has_no_alert():
    aircraft = models.Aircraft(
        icao24="abc123",
        callsign="TEST",
        lat=60.5,
        lon=24.5,
        baro_altitude_ft=1000,
        geo_altitude_ft=None,
        velocity=None,
        heading=None,
        on_ground=False,
        time_position=1000,
        last_contact=1000,
        position_source=0,
        category=None,
    )

    zone = models.Zone(
        id="unlimited-zone",
        name="Unlimited Restricted Zone",
        zone_type=models.ZoneType.RESTRICTED,
        lower=models.VerticalLimit(
            value=2000,
            unit=models.VerticalUnit.FT,
            reference=models.VerticalReference.STANDARD_PRESSURE,
        ),
        upper=models.VerticalLimit(
            value=None,
            unit=None,
            reference=None,
            unlimited=True,
        ),
        polygon=[
            (24.0, 60.0),
            (25.0, 60.0),
            (25.0, 61.0),
            (24.0, 61.0),
        ],
        source="test",
        activation_status=models.ActivationStatus.ACTIVE,
    )

    alerts = find_alerts(
        aircraft=aircraft,
        zones=[zone],
        now=1000,
    )

    assert alerts == []