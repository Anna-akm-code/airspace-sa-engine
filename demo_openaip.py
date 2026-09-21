"""Live OpenAIP data with one explicitly synthetic aircraft; development only."""

import argparse
import os
from math import isfinite

from dotenv import load_dotenv

from inspect_zones import format_limit
from sa_engine.models import Aircraft
from sa_engine.openaip_client import OpenAIPClient
from sa_engine.openaip_workflow import check_openaip_airspaces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zone-id', action='append', required=True,
                        help='Exact OpenAIP ID from inspect_zones.py; repeat to select several')
    parser.add_argument('--lon', type=float, required=True)
    parser.add_argument('--lat', type=float, required=True)
    parser.add_argument('--baro-altitude-ft', type=float, default=None,
                        help='Synthetic barometric altitude; omitted means unknown')
    args = parser.parse_args()
    if not (-180 <= args.lon <= 180 and -90 <= args.lat <= 90):
        parser.error('Longitude/latitude must be finite and within geographic bounds')
    if args.baro_altitude_ft is not None and not isfinite(args.baro_altitude_ft):
        parser.error('Barometric altitude must be finite')
    load_dotenv()
    key = os.getenv('OPENAIP_API_KEY')
    if not key:
        parser.error('Set OPENAIP_API_KEY in your environment or local .env')

    # Fixed synthetic timestamps keep freshness deterministic. No surveillance.
    now = 1000
    aircraft = Aircraft(
        icao24='000000', callsign='SYNTHETIC', lat=args.lat, lon=args.lon,
        baro_altitude_ft=args.baro_altitude_ft, geo_altitude_ft=None,
        velocity=None, heading=None, on_ground=False, time_position=now,
        last_contact=now, position_source=0, category=None,
    )
    zones, alerts = check_openaip_airspaces(
        OpenAIPClient(key), aircraft, now=now, zone_ids=args.zone_id,
    )
    print(f'SYNTHETIC aircraft: lon={args.lon}, lat={args.lat}, '
          f'baro_altitude_ft={args.baro_altitude_ft}, airborne, time={now}.')
    print('OpenAIP data; activation unknown. This is not operational or legal verification.')
    for zone in zones:
        print(f'{zone.id} | {zone.name} | {zone.zone_type.value} | '
              f'{format_limit(zone.lower)} -> {format_limit(zone.upper)} | '
              f'{zone.polygon.geom_type} | bounds={zone.polygon.bounds}')
    print(f'{len(alerts)} alert(s). No alert does not establish safety.')
    for alert in alerts:
        print(f'{alert.zone.id} | {alert.alert_type.value} | '
              f'{alert.verification_status.value} | {alert.data_quality.value} | '
              f'distance_to_boundary_m={alert.distance_to_boundary_m} | {alert.reason}')


if __name__ == '__main__':
    main()
