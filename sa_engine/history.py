"""Append-only JSONL history, distinct from application logs. Single writer only."""

import json
from dataclasses import asdict
from math import isfinite
from pathlib import Path

from .freshness import position_age


class HistoryError(ValueError):
    """Malformed history must be repaired explicitly; no silently skipped lines."""


def append_jsonl(path, records):
    # Pre-serialize all records so serialization failure does not append half a batch.
    lines = [json.dumps(record, allow_nan=False) + '\n' for record in records]
    if not lines:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        with path.open('rb') as stream:
            stream.seek(-1, 2)
            if stream.read(1) != b'\n':
                raise HistoryError('History has an incomplete final line; repair before appending')
    with path.open('a', encoding='utf-8') as stream:
        stream.writelines(lines)


class RunHistory:
    def __init__(self, runs_path='runs/runs.jsonl', positions_path='runs/positions.jsonl'):
        self.runs_path = Path(runs_path)
        self.positions_path = Path(positions_path)
        if self.runs_path.resolve() == self.positions_path.resolve():
            raise ValueError('Run and position history must use different paths')

    def record(self, metadata: dict, aircraft):
        observations = []
        for item in aircraft:
            observations.append(dict(asdict(item), run_id=metadata['run_id'],
                observed_at=metadata['run_timestamp'],
                position_age_s=position_age(item, metadata['run_timestamp'])))
        # Successful run marker goes last. Files are not a cross-file transaction.
        append_jsonl(self.positions_path, observations)
        append_jsonl(self.runs_path, [metadata])

    def last_positions(self, icao24: str, n: int = 10) -> list[dict]:
        """Latest N by observation/run time, oldest first; stable ties by file order.

        Missing file returns []. Repeated/stale samples are retained; this is
        observation context, not an interpolated or deduplicated flight track.
        All lines are validated, including other aircraft. O(file size) scan.
        """
        if type(n) is not int or n < 1:
            raise ValueError('n must be a positive integer')
        try:
            stream = self.positions_path.open(encoding='utf-8')
        except FileNotFoundError:
            return []
        matches = []
        with stream:
            for line_number, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                    if (not isinstance(row, dict) or not isinstance(row.get('icao24'), str)
                            or type(row.get('observed_at')) not in (int, float)
                            or not isfinite(row['observed_at'])
                            or any(type(row.get(key)) not in (int, float)
                                   or not isfinite(row[key]) for key in ('lat', 'lon'))
                            or not -90 <= row['lat'] <= 90 or not -180 <= row['lon'] <= 180):
                        raise ValueError('Invalid position envelope')
                except ValueError as exc:
                    raise HistoryError(f'Malformed position history line {line_number}') from exc
                if row['icao24'] == icao24:
                    matches.append(row)
        return sorted(matches, key=lambda row: row['observed_at'])[-n:]
