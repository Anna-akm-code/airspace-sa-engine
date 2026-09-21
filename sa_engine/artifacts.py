"""Persist detailed per-run presentation artifacts beside longitudinal history."""

import json
import re
from pathlib import Path

from .map_view import render_map
from .report import build_report, report_text


def collect_tracks(result, history, n=10):
    return {icao: [row for row in history.last_positions(icao, n)
                   if row['observed_at'] <= result.metadata['run_timestamp']]
            for icao in sorted({item.icao24 for item in result.aircraft})}


def write_artifacts(result, history, root='runs', *, mode='live'):
    run_id = result.metadata['run_id']
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Run ID must be a safe directory name')
    report = build_report(result, tracks=collect_tracks(result, history), mode=mode)
    text = report_text(report)
    html = render_map(report).get_root().render()
    folder = Path(root) / run_id
    folder.mkdir(parents=True, exist_ok=True)
    # Write JSON last: it is the bundle discovery marker used by the UI.
    (folder/'alerts.txt').write_text(text, encoding='utf-8')
    (folder/'map.html').write_text(html, encoding='utf-8')
    temporary = folder/'alerts.json.tmp'
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(folder/'alerts.json')
    return folder
