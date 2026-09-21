"""Raw OpenAIP disk cache. TTL is a data-access policy, not aviation validity."""

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from time import time

logger = logging.getLogger(__name__)


class CacheError(ValueError):
    """Malformed cache: inspect/remove explicitly rather than silently trusting it."""


@dataclass
class CachedAirspaces:
    records: list[dict]
    source: str
    fetched_at: float


class OpenAIPCache:
    def __init__(self, path, *, ttl_s=86400, clock=time):
        if type(ttl_s) not in (int, float) or not isfinite(ttl_s) or ttl_s < 0:
            raise ValueError('ttl_s must be finite and nonnegative')
        self.path = Path(path)
        self.ttl_s = ttl_s
        self.clock = clock

    def load(self, client, country='FI') -> CachedAirspaces:
        country = country.upper()
        now = self.clock()
        try:
            text = self.path.read_text(encoding='utf-8')
        except FileNotFoundError:
            text = None
        if text is not None:
            try:
                data = json.loads(text)
            except ValueError as exc:
                raise CacheError('Invalid OpenAIP cache JSON') from exc
            if (not isinstance(data, dict) or data.get('version') != 1
                    or not isinstance(data.get('country'), str)
                    or type(data.get('fetched_at')) not in (int, float)
                    or not isfinite(data['fetched_at']) or data['fetched_at'] < 0
                    or not isinstance(data.get('records'), list)
                    or any(not isinstance(row, dict) for row in data['records'])):
                raise CacheError('Invalid OpenAIP cache envelope')
            age = now - data['fetched_at']
            if age < 0:
                raise CacheError('OpenAIP cache fetch timestamp is in the future')
            if data['country'] == country and age < self.ttl_s:
                logger.info('Using cached OpenAIP records (age %.1fs)', age)
                return CachedAirspaces(data['records'], 'cache', data['fetched_at'])
        logger.info('Fetching OpenAIP records for %s', country)
        records = client.fetch_airspaces(country)
        data = dict(version=1, country=country, fetched_at=now, records=records)
        # Serialize before touching the old cache. Temp file is on the same volume.
        encoded = json.dumps(data, allow_nan=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=self.path.parent, prefix=self.path.name + '.', suffix='.tmp',
                    delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return CachedAirspaces(records, 'live', now)
