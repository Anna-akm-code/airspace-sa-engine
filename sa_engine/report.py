"""Explicit presentation schema. No HTTP, containment, or alert decisions."""

import json
from pathlib import Path

from shapely.geometry import mapping

from .freshness import position_age, position_freshness

LIMITATIONS = (
    'Modeled intersections, not legal infringement determinations. '
    'Activation status is incomplete. OpenAIP is not the sole authoritative operational source. '
    'OpenSky is cooperative traffic, not comprehensive drone/Remote ID coverage.'
)
META_FIELDS = (
    'run_id', 'run_timestamp', 'country', 'bbox', 'max_age_s', 'zone_source',
    'zones_fetched_at', 'zone_cache_age_s', 'raw_zone_count', 'supported_zone_count',
    'unsupported_zone_count', 'traffic_timestamp', 'traffic_observation_count',
    'positioned_count', 'missing_position_count', 'fresh_count', 'stale_count',
    'missing_time_count', 'future_time_count', 'on_ground_count', 'alert_count',
)
TRACK_FIELDS = (
    'icao24', 'callsign', 'observed_at', 'time_position', 'lat', 'lon',
    'baro_altitude_ft', 'geo_altitude_ft', 'velocity', 'heading', 'on_ground',
    'position_source', 'category', 'position_age_s', 'run_id',
)


def limit_dict(limit):
    return dict(value=limit.value, unit=None if limit.unit is None else limit.unit.value,
                reference=None if limit.reference is None else limit.reference.value,
                unlimited=limit.unlimited)


def format_limit(limit):
    if limit['unlimited']:
        return 'UNLIMITED'
    return f"{limit['value']} {limit['unit']} {limit['reference']}"


def format_position_source(code):
    names = {0: 'ADS-B', 1: 'ASTERIX', 2: 'MLAT', 3: 'FLARM'}
    if code is None:
        return 'unavailable'
    return f"{names.get(code, 'Unknown')} ({code})"


def format_altitude_ft(value):
    return 'unavailable' if value is None else f'{value} ft'


def aircraft_dict(item, now, max_age_s=60):
    return dict(icao24=item.icao24, callsign=item.callsign, lat=item.lat, lon=item.lon,
        baro_altitude_ft=item.baro_altitude_ft, geo_altitude_ft=item.geo_altitude_ft,
        velocity=item.velocity, heading=item.heading, on_ground=item.on_ground,
        time_position=item.time_position, last_contact=item.last_contact,
        position_source=item.position_source, category=item.category,
        position_age_s=position_age(item, now),
        freshness=position_freshness(item, now, max_age_s))


def zone_dict(zone, *, geometry=False):
    result = dict(id=zone.id, name=zone.name, zone_type=zone.zone_type.value,
                  activation_status=zone.activation_status.value,
                  lower=limit_dict(zone.lower), upper=limit_dict(zone.upper), source=zone.source)
    if geometry:
        # Explicit Shapely -> GeoJSON conversion preserves all components/rings.
        result['geometry'] = mapping(zone.polygon)
    return result


def alert_dict(alert, now, tracks=None, max_age_s=60):
    return dict(aircraft=aircraft_dict(alert.aircraft, now, max_age_s),
        zone=zone_dict(alert.zone), alert_type=alert.alert_type.value,
        verification_status=alert.verification_status.value,
        data_quality=alert.data_quality.value, reason=alert.reason,
        distance_to_boundary_m=alert.distance_to_boundary_m,
        recent_positions=[{key: row.get(key) for key in TRACK_FIELDS} for row in (tracks or [])])


def build_report(result, *, tracks=None, mode='live'):
    if mode not in ('live', 'synthetic'):
        raise ValueError('Report mode must be live or synthetic')
    tracks = tracks or {}
    now = result.metadata['run_timestamp']
    max_age = result.metadata.get('max_age_s', 60)
    data = dict(schema_version=1, mode=mode,
        label='SYNTHETIC DEMO - invented scenario' if mode == 'synthetic' else 'LIVE-LATEST - saved snapshot',
        limitations=LIMITATIONS,
        run={key: result.metadata.get(key) for key in META_FIELDS},
        zones=[zone_dict(zone, geometry=True) for zone in result.zones],
        aircraft=[aircraft_dict(item, now, max_age) for item in result.aircraft],
        alerts=[alert_dict(alert, now, tracks.get(alert.aircraft.icao24), max_age)
                for alert in result.alerts],
        tracks={icao: [{key: row.get(key) for key in TRACK_FIELDS} for row in rows]
                for icao, rows in tracks.items()})
    # Produces only JSON primitives (GeoJSON coordinate tuples become lists).
    return json.loads(json.dumps(data, allow_nan=False))


def alert_text(alert):
    item, zone = alert['aircraft'], alert['zone']
    return (f"{item['callsign'] or '-'} / {item['icao24']} | {zone['name']} ({zone['id']})\n"
        f"{alert['alert_type']} | {alert['verification_status'].upper()} | data quality: {alert['data_quality']}\n"
        f"{alert['reason']}\n"
        f"Position: {item['lat']}, {item['lon']}; age: {item['position_age_s']} s; source: {format_position_source(item['position_source'])}\n"
        f"Altitude: baro={item['baro_altitude_ft']} ft; geometric altitude: {format_altitude_ft(item['geo_altitude_ft'])}\n"
        f"Zone: {zone['zone_type']} | {format_limit(zone['lower'])} -> {format_limit(zone['upper'])}; "
        f"activation: {zone['activation_status']}\n"
        f"Boundary distance: {alert['distance_to_boundary_m']} m; recent positions: {len(alert['recent_positions'])}")


def report_text(report):
    run = report['run']
    lines = [report['label'], f"Run {run['run_id']} | timestamp {run['run_timestamp']}",
        f"Zones raw/supported/unsupported: {run['raw_zone_count']}/{run['supported_zone_count']}/{run['unsupported_zone_count']}",
        f"Traffic observations/positioned/fresh/stale: {run['traffic_observation_count']}/{run['positioned_count']}/{run['fresh_count']}/{run['stale_count']}",
        f"Alerts: {len(report['alerts'])}", report['limitations']]
    lines.extend(alert_text(alert) for alert in report['alerts'])
    if not report['alerts']:
        lines.append('No alerts in this run; this is not a safety determination.')
    return '\n\n'.join(lines) + '\n'


def load_report(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or data.get('schema_version') != 1
            or data.get('mode') not in ('live', 'synthetic')
            or not isinstance(data.get('run'), dict)
            or type(data['run'].get('run_timestamp')) is not int
            or any(not isinstance(data.get(key), list) for key in ('zones', 'aircraft', 'alerts'))
            or not isinstance(data.get('tracks'), dict)):
        raise ValueError('Unsupported or malformed run report')
    return data


def latest_live_report(root='runs'):
    candidates = []
    for path in Path(root).glob('*/alerts.json'):
        report = load_report(path)
        if report['mode'] == 'live':
            candidates.append((report['run']['run_timestamp'], str(path), report))
    return max(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None
