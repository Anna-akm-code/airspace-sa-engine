# Development and manual workflows

Optional live access is subject to [provider terms](../DATA_SOURCES.md).
No live verification is claimed.

## Live development demo

Set OPENAIP_API_KEY in your environment or local gitignored `.env`. Do not commit
credentials. First inspect Finnish candidates:

```powershell
python inspect_zones.py
```

Copy an exact ID from that output. Choose an explicit synthetic position using
the geometry/chart; the bounding-box centre is not guaranteed to be inside.
Run the following with your chosen ID and coordinates:

```powershell
python demo_openaip.py --zone-id "COPIED_ID" --lon 24.25 --lat 60.25
```

The example coordinates are invented, not a verified location in your selected
zone. Repeat `--zone-id` for multiple zones. Add `--baro-altitude-ft 3000` only
when you want that explicit synthetic barometric assumption. No altitude is
inferred from a zone's published limits. With altitude omitted, horizontal
containment can yield an UNKNOWN alert; outside the footprint there is no alert.
The synthetic aircraft is airborne, uses fixed timestamp 1000 for both its
position and detection time, and has no real surveillance source. The demo
prints selected zones and alert type, verification, data quality and reason.
It does not force any result, and no alert does not establish safety.

## Batch failure policy

The Stage 3 demo orchestration function fetches all pages, then parses all selected records
before detection. A malformed or unsupported selected record aborts the batch
with a ValueError containing its zero-based original index, ID and name, with
the original exception chained. No partial alerts or successful subset is returned.
Without an explicit ID selection, all records are parsed: unsupported OpenAIP
airspace classes will fail. The demo requires explicit IDs so its scope is visible;
it does not claim to evaluate all Finnish airspaces. Missing requested IDs fail.

Timeout/connection/HTTP errors remain requests exceptions. Malformed JSON or
pagination raises OpenAIPResponseError. These differ from adapter/domain errors.
There are no automatic retries. Validation covers the supported ingestion
contract, not every possible aviation inconsistency or adversarial payload.

## Stage 4: OpenSky traffic ingestion

`OpenSkyTokenManager -> OpenSkyClient -> raw time/states envelope ->
parse_states() -> (Aircraft list, missing-position count)`. The Stage 4 modules
remain independent; Stage 5 composes them with detection.

The [official REST documentation](https://openskynetwork.github.io/opensky-api/rest.html)
was checked on 2026-09-21: OAuth2 client credentials, `/states/all`, WGS84 bbox,
and the extended 18-field layout match the implementation. Position sources
0/1/2/3 mean ADS-B/ASTERIX/MLAT/FLARM. Category 14 denotes UAV when supplied;
OpenSky is cooperative aviation surveillance, not comprehensive drone, Remote ID
or U-space coverage. Coverage, update freshness and access limits vary.

Token expiry uses required positive `expires_in`, a monotonic clock and a
configurable 30-second margin; credentials/tokens are never written to disk by
these modules. HTTP errors, including 401/429, propagate without retries. An
expired/rejected token requiring recovery is left to the caller; no background
refresh or thread-safe shared cache is provided. Injected sessions are caller-owned.

The client preserves the raw timestamp and accepts `states: null` or `[]` as
empty; a missing key fails. Null-empty acceptance is a compatibility policy,
not a claim that the documentation guarantees null. Adapter callsigns are
trimmed (blank becomes None); missing coordinates are counted and filtered.
Missing altitudes remain None. Both altitudes convert metres to feet separately;
barometric and geometric values are never substituted. Mapped fields are
validated, malformed rows abort the batch, and appended fields are ignored.
Nonnegative source/category codes are preserved rather than used for filtering.

For optional live inspection, set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET
in the environment or local gitignored `.env`, then run `python inspect_traffic.py`.
It uses FINLAND_BBOX=(59.0,19.0,70.5,32.0), an approximate rectangle including
neighbouring territory, not the Finnish border. It prints timestamp/count, one
raw row and its length, and the filtering count; it saves no traffic. Live
credentials and endpoint behavior have not been exercised by the offline tests.

## Stage 5: live workflow

Run `python detect_only.py` with local OPENAIP_API_KEY, OPENSKY_CLIENT_ID and
OPENSKY_CLIENT_SECRET. Raw airspace cache, completed-run JSONL and position JSONL
use gitignored `runs/` by default. Freshness and unsupported type counts remain
visible; existing deterministic alert rules are unchanged. Current traffic is
always fetched. See [Stage 5](stage5.md) for configuration, failure policies,
track lookup and manual smoke-test instructions. Live validation remains pending.
Stage 7 consumes these results for reports/maps/UI; see below.

## Stage 6: metric boundary distance

Alerts now include shortest horizontal boundary distance in metres, including
when vertical containment is UNKNOWN. `projection.py` transforms both geometry
and point from EPSG:4326 to EPSG:3067 using a reusable pyproj Transformer with
always_xy=True. It measures against the full boundary, including holes and all
MultiPolygon parts. CLI displays kilometres. No outside-proximity alerts are added.
Exact source-boundary incidence remains zero; vertex projection approximates
curved transformed edges. See ADR-013 for scope and numerical test assumptions.
Dependencies now include pyproj==3.8.0; install with `python -m pip install -r requirements.txt`.

## Stage 7: reports, map and visual inspection

Install the pinned dependencies with `python -m pip install -r requirements.txt`.
Generate an unmistakably synthetic example without API credentials:

```powershell
python demo_presentation.py
streamlit run app.py
```

The demo writes `runs/synthetic-stage7/alerts.json`, `alerts.txt`, and `map.html`.
Open map.html in a browser or select **Synthetic Demo** in the UI. The invented
DEMO-P01 zone does not identify a real facility; DEMO01 and all track positions
are synthetic. Fixed scenario time makes tests reproducible, not current traffic.
Demo tracks pass through isolated temporary Stage 5 history and never pollute
live runs/positions JSONL. Re-running the demo replaces the same demo bundle.

`python detect_only.py` now also exports `runs/<run-id>/alerts.json`, `alerts.txt`
and `map.html` after the live workflow succeeds. `--artifacts PATH` changes the
bundle root; existing `--runs`/`--positions` history paths remain independent.
Select **Latest saved live run** in Streamlit and set its artifact directory.
The UI selects the greatest saved run timestamp, excludes synthetic reports,
and does not fetch APIs. Historical JSONL alone lacks full zones/alerts, so old
runs must not be reconstructed by guessing or rerunning detection in the UI.
A saved snapshot's freshness is at its run timestamp, not the current wall clock.

Report schema v1 explicitly selects run metadata, aircraft fields, zone limits,
GeoJSON footprints, detector-produced alerts and track snapshots. Enum values
are strings, absent values are JSON null, distances are metres, aircraft altitude
fields are feet, and zone limits retain their own units/references/unlimited flag.
Reports preserve UNKNOWN/POTENTIAL/CONFIRMED and data quality; neither map nor UI
recomputes containment or vertical rules. No alert is a valid result, not a safety
claim. Popup text is escaped; only local application-generated report files are
supported (this is not an arbitrary untrusted report upload service).

Display geometry is EPSG:4326 lon/lat GeoJSON; Folium markers and track polylines
use lat/lon. Leaflet's default basemap rendering uses EPSG:3857. EPSG:3067 remains
internal to metric calculation, never passed as display coordinates. Full GeoJSON
preserves holes and MultiPolygon parts. FeatureGroup/LayerControl separates P/R/D,
normal traffic, alerted traffic and tracks; popups also state freshness and alert
status in text. Track lines connect recorded observations, not a verified route.

Folium 0.20.0 and Streamlit 1.64.0 are pinned. Built-in
`streamlit.components.v1.html` embeds the map; no bridge package is required.
Generation/tests need no internet, but rendered Folium maps normally download
JavaScript/CSS and OpenStreetMap tiles in the browser. Fully offline browser asset
bundling is not provided. Reports remain readable without those assets.

Limitations remain visible: incomplete activation, cooperative traffic rather
than comprehensive drone/Remote ID coverage, OpenAIP not the sole authority, and
modeled intersections rather than legal infringement findings. Loading malformed
bundles fails visibly; artifact export errors do not roll back already completed
Stage 5 JSONL history. Large datasets/history scans are not optimized in this UI.

