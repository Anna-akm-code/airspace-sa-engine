"""One live modeled-intersection run. Includes metric boundary distance; saved report/map artifacts; no polling."""

import argparse
import logging
import os

from dotenv import load_dotenv

from inspect_zones import format_limit
from sa_engine.artifacts import write_artifacts
from sa_engine.freshness import position_age
from sa_engine.history import RunHistory
from sa_engine.live_workflow import run_detection
from sa_engine.openaip_cache import OpenAIPCache
from sa_engine.openaip_client import OpenAIPClient
from sa_engine.opensky_auth import OpenSkyTokenManager
from sa_engine.opensky_client import OpenSkyClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', default='runs/openaip_cache.json')
    parser.add_argument('--cache-ttl', type=float, default=86400, help='Seconds; 0 forces refetch')
    parser.add_argument('--runs', default='runs/runs.jsonl')
    parser.add_argument('--positions', default='runs/positions.jsonl')
    parser.add_argument('--artifacts', default='runs', help='Root for per-run JSON/text/map bundles')
    parser.add_argument('--max-age', type=int, default=60)
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format='%(levelname)s %(name)s: %(message)s')
    load_dotenv()
    names = ('OPENAIP_API_KEY', 'OPENSKY_CLIENT_ID', 'OPENSKY_CLIENT_SECRET')
    credentials = [os.getenv(name) for name in names]
    if not all(credentials):
        parser.error('Set OPENAIP_API_KEY, OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in environment/.env')
    history = RunHistory(args.runs, args.positions)
    cache = OpenAIPCache(args.cache, ttl_s=args.cache_ttl)
    if cache.path.resolve() in (history.runs_path.resolve(), history.positions_path.resolve()):
        parser.error('Cache and history paths must be distinct')
    result = run_detection(
        OpenAIPClient(credentials[0]),
        OpenSkyClient(OpenSkyTokenManager(credentials[1], credentials[2])),
        cache, history, max_age_s=args.max_age,
    )
    artifact_folder = write_artifacts(result, history, args.artifacts)
    print(f'Run artifacts: {artifact_folder}')
    stats = result.metadata
    print(f"Zones: raw={stats['raw_zone_count']} P/R/D={stats['supported_zone_count']} "
          f"unsupported={stats['unsupported_zone_count']} source={stats['zone_source']}")
    print(f"Traffic: observations={stats['traffic_observation_count']} positioned={stats['positioned_count']} "
          f"fresh={stats['fresh_count']} stale={stats['stale_count']} "
          f"missing_time={stats['missing_time_count']} missing_position={stats['missing_position_count']} "
          f"on_ground={stats['on_ground_count']}")
    print(f"Detection: {len(result.alerts)} alert(s) according to loaded data.")
    print('Activation is incomplete; alerts are not legal infringements. OpenSky is not comprehensive drone awareness.')
    tracks = {}
    for alert in result.alerts:
        item, zone = alert.aircraft, alert.zone
        if item.icao24 not in tracks:
            tracks[item.icao24] = history.last_positions(item.icao24)
        distance = ('unknown' if alert.distance_to_boundary_m is None
                    else f'{alert.distance_to_boundary_m / 1000:.2f} km')
        print(f'{item.callsign or "-"}/{item.icao24} | {zone.name} | '
              f'{alert.alert_type.value} | {alert.verification_status.value} | '
              f'baro_ft={item.baro_altitude_ft} geo_ft={item.geo_altitude_ft} | '
              f'{format_limit(zone.lower)} -> {format_limit(zone.upper)} | '
              f'position_age_s={position_age(item, stats["run_timestamp"])} | '
              f'distance to boundary: {distance} | '
              f'position_source={item.position_source} | recent_track_count={len(tracks[item.icao24])}')


if __name__ == '__main__':
    main()
