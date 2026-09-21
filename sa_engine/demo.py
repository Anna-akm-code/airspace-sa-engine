"""Deterministic invented scenario. Only this module invokes demo detection."""

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from shapely.geometry import box

from .artifacts import collect_tracks
from .geometry import find_alerts
from .history import RunHistory
from .live_workflow import RunResult
from .models import (
    ActivationStatus,
    Aircraft,
    VerticalLimit,
    VerticalReference,
    VerticalUnit,
    Zone,
    ZoneType,
)
from .report import build_report

DEMO_TIME = 1700000000


def synthetic_result(history):
    """Uses isolated Stage 5 history. Coordinates designate no real facility."""
    if history.runs_path.exists() or history.positions_path.exists():
        raise ValueError('Synthetic demo requires empty isolated history paths')
    zone = Zone('DEMO-P01', 'Synthetic Critical Infrastructure Zone - INVENTED',
        ZoneType.PROHIBITED,
        VerticalLimit(1000, VerticalUnit.FT, VerticalReference.STANDARD_PRESSURE),
        VerticalLimit(6000, VerticalUnit.FT, VerticalReference.STANDARD_PRESSURE),
        box(25.0, 64.0, 25.04, 64.04), 'synthetic', ActivationStatus.UNKNOWN)
    aircraft = Aircraft('000001','DEMO01',64.02,25.02,3000,None,70,90,False,
                        DEMO_TIME,DEMO_TIME,0,3)
    # The source code and numeric source field are synthetic metadata, not reception claims.
    for index, lon in enumerate((24.98, 24.995, 25.01)):
        timestamp = DEMO_TIME - 30 + index*10
        history.record(dict(run_id=f'synthetic-track-{index}', run_timestamp=timestamp),
                       [replace(aircraft,lon=lon,time_position=timestamp,last_contact=timestamp)])
    normal = replace(aircraft,icao24='000002',callsign='DEMO02',lon=25.07)
    stale = replace(aircraft,icao24='000003',callsign='DEMO-STALE',time_position=DEMO_TIME-120)
    traffic = [aircraft,normal,stale]
    alerts = [alert for item in traffic for alert in find_alerts(item,[zone],now=DEMO_TIME)]
    metadata = dict(run_id='synthetic-stage7',run_timestamp=DEMO_TIME,country='FI',
        max_age_s=60,zone_source='synthetic', raw_zone_count=1,supported_zone_count=1,
        unsupported_zone_count=0,traffic_timestamp=DEMO_TIME,traffic_observation_count=3,
        positioned_count=3,missing_position_count=0,fresh_count=2,stale_count=1,
        missing_time_count=0,future_time_count=0,on_ground_count=0,alert_count=len(alerts))
    result = RunResult(metadata,[zone],traffic,alerts)
    history.record(metadata,traffic)
    return result


def demo_report():
    """Build demo through detector and history without touching live files."""
    with TemporaryDirectory() as temporary:
        history = RunHistory(Path(temporary)/'runs.jsonl',Path(temporary)/'positions.jsonl')
        result = synthetic_result(history)
        return build_report(result, tracks=collect_tracks(result,history), mode='synthetic')
