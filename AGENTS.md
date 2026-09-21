# Airspace SA Engine

## Purpose

This is a learning and portfolio project for a deterministic
airspace situational-awareness engine.

The developer is learning Python and the aviation/geospatial
domain while building it.

## Working style

- Do not make large implementation changes without explaining them first.
- Prefer small incremental changes.
- Do not silently change domain semantics.
- Point out affected code and tests before changing shared models.
- Run the full test suite after changes.
- Preserve existing architecture unless there is a clear reason to change it.
- When reviewing code, identify edge cases and assumptions explicitly.

## Important domain rules

- Danger area is not the same as prohibited area.
- An AirspaceAlert is not a claim of legal infringement.
- Altitude units may be converted, but altitude references must not
  silently be treated as equivalent.
- GND, MSL, AGL and STANDARD_PRESSURE have distinct semantics.
- Horizontal containment may still be known when vertical comparison
  is unknown.
- Polygon coordinates use (longitude, latitude).
- Detection logic must remain deterministic.
- An LLM must never decide whether an airspace alert exists.

## Current project status

Stages 0-8 / M2 implementation is complete. Publication gates remain manual;
see docs/publication_checklist.md. Do not start Stage 9 without a new task.

Stage 3 includes:
- OpenAIP adapter: types, vertical references, explicit unlimited ceilings,
  Polygon/MultiPolygon geometry and complete Zone conversion.
- Paginated HTTP client, separately tested with injected offline HTTP responses.
- Manual Finnish inspection and authoritative-comparison template.
- End-to-end orchestration and synthetic-aircraft demo, with offline integration tests.
- Architecture decisions and limitations in README.md and docs/decisions.md.

Stage 4 adds OpenSky OAuth2 token management, a raw traffic client, and an
18-field state-vector adapter targeting the unchanged Aircraft model. Tests
remain offline; optional inspect_traffic.py is separate from detection. Missing
positions are explicitly counted/filtered; null altitude preserves uncertainty.
Stage 5 composes OpenAIP/OpenSky with find_alerts, raw disk caching, freshness
counts, application logging, append-only run/position JSONL and recent positions.
See docs/stage5.md. Live smoke validation remains pending. Unsupported integer
airspace classes are counted; malformed supported records abort the live run.

Live authoritative comparison is still pending; passing tests do not verify live data.
Batch parsing fails on any unsupported/malformed selected record before detection.
Known deferred issues: activation handling, GND comparability, the polygon field
name. Do not expand these without a new explicit task.

Stage 6 populates alert boundary distances using EPSG:4326 -> EPSG:3067,
pyproj always_xy=True and full Polygon/MultiPolygon boundaries. Containment and
vertical semantics are unchanged; outside proximity warnings are not implemented.

Stage 7 adds explicit JSON/text reports, Folium map artifacts and a read-only
Streamlit UI. Presentation consumes saved results, never recomputes alerts.
Synthetic demo objects use the real detector and isolated Stage 5 track history.
Live CLI exports per-run bundles; UI loads the latest saved live bundle without
HTTP. Keep synthetic labels and verification/data-quality text visible.

Stage 8 adds minimal Ruff, coverage, offline GitHub Actions, source/data licensing
separation and publication documentation. Live validation and Git-history review
are not implied by passing CI. No remote publishing is automatic.

## Testing

Use:

python -m pytest
python -m ruff check .
python -m pytest --cov=sa_engine --cov-report=term-missing

Do not use bare `pytest` for this repository because the current setup
may fail to resolve the `sa_engine` package that way.