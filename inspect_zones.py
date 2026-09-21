"""Manual Finnish OpenAIP inspection; never run by pytest or on import."""

import argparse
import os

from dotenv import load_dotenv

from sa_engine.openaip_adapter import parse_zone
from sa_engine.openaip_client import OpenAIPClient


def format_limit(limit):
    if limit.unlimited:
        return "UNLIMITED"
    return f"{limit.value} {limit.unit.value} {limit.reference.value}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', action='append', help='Exact name to inspect; repeat for multiple zones')
    parser.add_argument('--limit', type=int, default=3, help='Maximum records displayed (default: 3)')
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be positive')
    load_dotenv()
    api_key = os.getenv('OPENAIP_API_KEY')
    if not api_key:
        parser.error('Set OPENAIP_API_KEY in your environment or local .env')

    raw_items = OpenAIPClient(api_key).fetch_airspaces('FI')
    candidates = [item for item in raw_items
                  if isinstance(item.get('name'), str)
                  and item['name'].startswith(('EFP', 'EFR', 'EFD'))]
    if args.name:
        candidates = [item for item in candidates if item['name'] in args.name]
        missing = set(args.name) - {item['name'] for item in candidates}
        if missing:
            parser.error(f'Requested names not found among P/R/D candidates: {sorted(missing)}')
    else:
        # Prefer one candidate of each naming family, then fill remaining slots.
        first = [next((item for item in candidates if item['name'].startswith(prefix)), None)
                 for prefix in ('EFP', 'EFR', 'EFD')]
        first = [item for item in first if item is not None]
        candidates = first + [item for item in candidates if item not in first]

    print(f'Fetched {len(raw_items)} Finnish records; displaying up to {args.limit}.')
    print('OpenAIP is not authoritative. Manual comparison is still required.')
    for raw in candidates[:args.limit]:
        try:
            zone = parse_zone(raw)
        except ValueError as exc:
            raise ValueError(f"Adapter failed for {raw.get('_id')!r} / {raw.get('name')!r}: {exc}") from exc
        print(f'{zone.id} | {zone.name} | {zone.zone_type.value} | '
              f'{format_limit(zone.lower)} -> {format_limit(zone.upper)} | '
              f'{zone.polygon.geom_type} | bounds(lon, lat): {zone.polygon.bounds}')
    if not candidates:
        print('No matching Finnish P/R/D candidates found; this is not a successful verification.')


if __name__ == '__main__':
    main()
