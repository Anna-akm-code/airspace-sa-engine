"""Development orchestration; transport, parsing and detection stay separate."""

from .geometry import find_alerts
from .models import Aircraft, AirspaceAlert, Zone
from .openaip_adapter import parse_zone
from .openaip_client import OpenAIPClient


def check_openaip_airspaces(
    client: OpenAIPClient,
    aircraft: Aircraft,
    *,
    now: int,
    country: str = "FI",
    zone_ids: list[str] | None = None,
) -> tuple[list[Zone], list[AirspaceAlert]]:
    """Parse the whole selected batch before detection; never skip failures.

    None selects all fetched records, including unsupported types (which fail).
    Explicit IDs narrow the demo scope, not the underlying HTTP request.
    Network/response exceptions propagate; ingestion failures are ValueError.
    """
    raw_items = client.fetch_airspaces(country)
    if zone_ids is not None:
        if not zone_ids:
            raise ValueError("Select at least one zone ID")
        missing = set(zone_ids) - {item.get("_id") for item in raw_items
                                   if isinstance(item.get("_id"), str)}
        if missing:
            raise ValueError(f"Requested zone IDs not found: {sorted(missing)}")
        selected = [(index, raw) for index, raw in enumerate(raw_items)
                    if raw.get("_id") in zone_ids]
    else:
        selected = list(enumerate(raw_items))

    zones = []
    for index, raw in selected:
        try:
            zones.append(parse_zone(raw))
        except ValueError as exc:
            raise ValueError(
                f"OpenAIP record index {index}, id={raw.get('_id')!r}, "
                f"name={raw.get('name')!r}: {exc}"
            ) from exc
    return zones, find_alerts(aircraft, zones, now=now)
