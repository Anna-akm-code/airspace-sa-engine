# Stage 5: live detection and local history

## One manual smoke run

Set OPENAIP_API_KEY, OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in your local
`.env` or environment. Never include credentials in history or source control.
From the repository root run:

```powershell
python detect_only.py
```

The default writes only under gitignored `runs/`: `openaip_cache.json`,
`runs.jsonl`, and `positions.jsonl`. Example configurable paths/policy:

```powershell
python detect_only.py --cache runs/openaip_cache.json --cache-ttl 86400 --runs runs/runs.jsonl --positions runs/positions.jsonl --max-age 60 --log-level INFO
```

Use `--cache-ttl 0` to force a new OpenAIP fetch. OpenSky is fetched on every run.
Check source/counts, stale/missing-time observations, normal zero-alert output,
and JSONL lines. A second run within TTL should use cached airspace and fetch
new traffic; history grows rather than being overwritten. No synthetic aircraft
or alerts are inserted. Manual live validation for Stage 5 remains PENDING;
pytest uses fake HTTP and temporary directories. The authoritative comparison
in `openaip_manual_check.md` is still a separate process.

## Data flow and failure boundaries

`run_detection()` returns `RunResult(metadata, zones, aircraft, alerts)`:

1. OpenAIP raw disk cache or client fetch.
2. Adapter selects P/R/D; other integer classes are counted by code and warned.
3. Malformed type fields or malformed supported records fail before detection.
4. OpenSky client fetches a new raw envelope; adapter returns positioned Aircraft
   and an explicit count of rows without coordinates.
5. Workflow samples current time after fetch and computes freshness statistics.
6. Existing `find_alerts()` handles each aircraft unchanged.
7. Position observations append first, followed by the completed run metadata.

This policy belongs to the Stage 5 workflow. The older explicit-selection
OpenAIP demo still fails on unsupported selected records. External numeric type
knowledge remains in the adapter, not the workflow or domain detector.
HTTP, parsing, file and storage failures propagate; the workflow logs ERROR with
the exception class, without dumping response bodies, credentials or tokens.
It returns no success result on failure. A downloaded raw cache may remain even
if later parsing fails; inspect/correct/remove it explicitly before rerunning.

## Cache policy

Versioned JSON stores country, fetch-start Unix timestamp, and raw records.
The default 86400-second TTL is a development access policy, not an operational
aviation update guarantee. Age strictly below TTL is fresh; equality expires.
Missing, expired, or different-country cache refetches; there is no stale fallback.
Invalid JSON/envelope or a future fetch timestamp stops the run. Permission and
I/O errors also remain visible. Inspect/remove a corrupt file to refetch.

A temporary file in the same directory is flushed and replaced atomically, so
failed writes do not replace a valid old cache with a partial document. Raw data
is reparsed each run: no pickled domain objects, geometry or old parser decisions
are trusted. Concurrent writers are unsupported.

## Freshness counts

`time_position`, never `last_contact`, determines spatial age. Age > max_age_s
is stale; equality is fresh. Missing time is a separate category. Fresh/stale/
missing-time counts partition positioned aircraft, including those on ground;
on-ground count is an overlapping statistic among positioned observations.
Rows missing coordinates are separately counted but have no position history.

Stale, missing-time and ground observations are stored, but existing detection
excludes them. Staleness does not manufacture an AirspaceAlert. Future timestamps
retain the existing detector behavior (fresh) and receive a separate count and
warning; clock-skew semantics need a deliberate future decision. Traffic response
time and local run time are both exposed and not substituted for position time.

## Logging, history and track context

Python logging describes software activity: fetch/cache/counts/completion at
INFO, unsupported/freshness conditions at WARNING, stopping failures at ERROR.
Console logging is configured only by the CLI. JSONL is independent persistent
structured history, not captured log messages.

Run records contain UUID, timestamp, source/cache age, country/bbox, thresholds,
counts, unsupported class breakdown and traffic timestamp. Position records
contain run ID/time, all Aircraft fields (altitude names explicitly in feet), and
position age. Neither record stores HTTP clients, authentication data or raw tokens.

`RunHistory.last_positions(icao24, n=10)` filters positions, sorts by observation
(run) timestamp, and returns the latest N oldest-first, with stable file-order
ties. Missing file returns []; fewer than N returns all matches. Invalid JSON
or invalid basic position envelope raises HistoryError with line number, even
for another aircraft. Blank lines are errors. An incomplete final line blocks
append until repaired. Repeated/stale positions remain observations rather than
being deduplicated or interpolated into a trajectory. CLI track count includes
the current observation and is available per alerted ICAO24.

JSONL permits independent line parsing and simple append, but has no indexing,
rotation, locking or cross-file transactions. Track queries scan the file.
A crash/write failure can leave partial history or orphan position rows; run_id
allows checking whether a completed run marker exists. Appending validates the
line ending, not every previous historical record; strict reading detects bad
interior lines. Use one writer and repair malformed files explicitly.

No Stage 6 projected distances or Stage 7 maps/UI/reports are implemented.
Activation remains incomplete; results are modeled intersections according to
loaded data, not legal infringements. OpenSky is not comprehensive drone awareness.
