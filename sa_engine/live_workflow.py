"""Stage 5 orchestration. Source and storage I/O surround deterministic detection."""

import logging
from dataclasses import dataclass
from time import time
from uuid import uuid4

from .freshness import position_age, position_freshness
from .geometry import find_alerts
from .models import Aircraft, AirspaceAlert, Zone
from .openaip_adapter import parse_supported_zones
from .opensky_adapter import parse_states
from .opensky_client import FINLAND_BBOX

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    metadata: dict
    zones: list[Zone]
    aircraft: list[Aircraft]
    alerts: list[AirspaceAlert]


def run_detection(openaip, opensky, cache, history, *, country='FI',
                  bbox=FINLAND_BBOX, max_age_s=60, clock=time) -> RunResult:
    """One current-traffic run, with explicit source filtering and success history.

    Errors stop the run and propagate unchanged; error logs avoid payloads or
    credentials. Persistence failure can leave position rows without a run marker.
    """
    try:
        if type(max_age_s) is not int or max_age_s < 0:
            raise ValueError('max_age_s must be a nonnegative integer')
        if cache.path.resolve() in (history.runs_path.resolve(), history.positions_path.resolve()):
            raise ValueError('Cache and history paths must be distinct')
        cached = cache.load(openaip, country)
        zones, unsupported = parse_supported_zones(cached.records)
        if unsupported:
            logger.warning('Unsupported OpenAIP types excluded: %s', unsupported)
        logger.info('Zones: raw=%d supported=%d', len(cached.records), len(zones))
        logger.info('Fetching current OpenSky traffic')
        traffic = opensky.fetch_states(bbox)
        aircraft, missing_position = parse_states(traffic['states'])
        now = int(clock())  # Sample after fetch: network latency counts toward age.
        counts = dict(fresh=0, stale=0, missing_time=0)
        for item in aircraft:
            counts[position_freshness(item, now, max_age_s)] += 1
        future = sum(position_age(item, now) is not None and position_age(item, now) < 0
                     for item in aircraft)
        if counts['stale'] or counts['missing_time'] or missing_position or future:
            logger.warning('Traffic freshness: %s; missing_position=%d future_time=%d',
                           counts, missing_position, future)
        alerts = [alert for item in aircraft
                  for alert in find_alerts(item, zones, now=now, max_age_s=max_age_s)]
        metadata = dict(
            version=1, run_id=str(uuid4()), run_timestamp=now, country=country.upper(),
            bbox=list(bbox), max_age_s=max_age_s, zone_source=cached.source,
            zones_fetched_at=cached.fetched_at, zone_cache_age_s=now-cached.fetched_at,
            raw_zone_count=len(cached.records), supported_zone_count=len(zones),
            unsupported_zone_count=sum(unsupported.values()), unsupported_types=unsupported,
            traffic_timestamp=traffic['time'], traffic_observation_count=len(traffic['states'] or []),
            positioned_count=len(aircraft), missing_position_count=missing_position,
            fresh_count=counts['fresh'], stale_count=counts['stale'],
            missing_time_count=counts['missing_time'], future_time_count=future,
            on_ground_count=sum(item.on_ground for item in aircraft), alert_count=len(alerts),
        )
        history.record(metadata, aircraft)
        logger.info('Detection completed: positioned=%d fresh=%d stale=%d alerts=%d',
                    len(aircraft), counts['fresh'], counts['stale'], len(alerts))
        return RunResult(metadata, zones, aircraft, alerts)
    except Exception as exc:
        logger.error('Run stopped (%s)', type(exc).__name__)
        raise
