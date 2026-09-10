from shapely.geometry import Point, Polygon

from .altitude import can_compare
from .models import (
    Aircraft,
    AirspaceAlert,
    AlertType,
    Comparability,
    DataQuality,
    VerificationStatus,
    Zone,
    ZoneType,
)


def find_alerts(
    aircraft: Aircraft,
    zones: list[Zone],
    now: int,
    max_age_s: int = 60,
) -> list[AirspaceAlert]:
    alerts = []

    # No-alert exclusion rules
    if aircraft.on_ground:
        return []

    if aircraft.time_position is None:
        return []

    if now - aircraft.time_position > max_age_s:
        return []

    if aircraft.lat is None or aircraft.lon is None:
        return []

    point = Point(aircraft.lon, aircraft.lat)

    for zone in zones:
        shapely_polygon = Polygon(zone.polygon)

        # 1. Horizontal containment
        if not shapely_polygon.covers(point):
            continue

        # 2. Choose alert type based on zone type
        if zone.zone_type is ZoneType.PROHIBITED:
            alert_type = AlertType.PROHIBITED_AREA_ENTRY
        elif zone.zone_type is ZoneType.RESTRICTED:
            alert_type = AlertType.RESTRICTED_AREA_ENTRY
        else:
            alert_type = AlertType.DANGER_AREA_EXPOSURE

        # 3. Check whether vertical limits can be compared
        lower_result = can_compare(aircraft, zone.lower)
        upper_result = can_compare(aircraft, zone.upper)

        # 4. UNKNOWN: report horizontal containment,
        # but do not pretend we know vertical containment
        if (
            lower_result is Comparability.UNKNOWN
            or upper_result is Comparability.UNKNOWN
        ):
            if aircraft.baro_altitude_ft is None:
                data_quality = DataQuality.NO_ALTITUDE
                reason = "Aircraft is horizontally inside the zone, but altitude is missing."
            else:
                data_quality = DataQuality.VERTICAL_UNKNOWN
                reason = (
                    "Aircraft is horizontally inside the zone, "
                    "but vertical references cannot be compared reliably."
                )

            alerts.append(
                AirspaceAlert(
                    aircraft=aircraft,
                    zone=zone,
                    alert_type=alert_type,
                    verification_status=VerificationStatus.UNKNOWN,
                    data_quality=data_quality,
                    distance_to_boundary_m=None,
                    reason=reason,
                )
            )

            continue

         # From here on, barometric altitude exists and comparison is possible
        lower_ft = zone.lower.to_feet().value
        upper_ft = zone.upper.to_feet().value
        aircraft_altitude = aircraft.baro_altitude_ft

         # 5. Vertical containment
        if not lower_ft <= aircraft_altitude <= upper_ft:
            continue
        # 6. Approximate comparison
        if (
            lower_result is Comparability.APPROXIMATE
            or upper_result is Comparability.APPROXIMATE
        ):
            alerts.append(
                AirspaceAlert(
                    aircraft=aircraft,
                    zone=zone,
                    alert_type=alert_type,
                    verification_status=VerificationStatus.POTENTIAL,
                    data_quality=DataQuality.OK,
                    distance_to_boundary_m=None,
                    reason="Vertical containment is based on an approximate altitude comparison.",
                )
            )

        # 7. Both comparisons must now be COMPARABLE
        else:
            alerts.append(
                AirspaceAlert(
                    aircraft=aircraft,
                    zone=zone,
                    alert_type=alert_type,
                    verification_status=VerificationStatus.CONFIRMED,
                    data_quality=DataQuality.OK,
                    distance_to_boundary_m=None,
                    reason="Aircraft is horizontally and vertically inside the zone.",
                )
            )

    return alerts