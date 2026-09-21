# Architecture decisions

ADR means Architecture Decision Record. Existing identifiers are preserved;
gaps in numbering do not imply missing implementation requirements.

## ADR-001 - OpenAIP as an integration source

**Decision:** Use OpenAIP's structured API behind a provider-specific client and
adapter for this portfolio integration. It does not replace authoritative AIP
information. The manual Finnish comparison is independent of offline testing.

**Consequence:** Domain objects and deterministic detection do not depend on
OpenAIP fields. Provider data terms remain separate from the source-code license;
see [data sources](../DATA_SOURCES.md).

## ADR-002 — Alerts, not infringements

**Decision:**  
The system output is called an `AirspaceAlert`, not an infringement.

**Why:**  
The system detects potentially relevant aircraft/airspace situations, but it does not have enough legal or operational context to determine that a regulation was actually violated.

**Consequence:**  
Alerts carry an `alert_type`, `verification_status`, `data_quality`, and `reason` to preserve uncertainty.




## ADR-003 — Danger areas are not prohibited areas

**Decision:**  
`DANGER`, `RESTRICTED`, and `PROHIBITED` are separate `ZoneType` values and produce different alert types.

**Why:**  
A danger area does not automatically mean entry is prohibited. These airspace types have different meanings, so the system must not collapse them into one generic "no-go" category.

**Consequence:**  
The system uses:
- `PROHIBITED_AREA_ENTRY`
- `RESTRICTED_AREA_ENTRY`
- `DANGER_AREA_EXPOSURE`


## ADR-007 — Use `covers()` for horizontal containment

**Decision:**  
Use Shapely `covers()` rather than `contains()` when checking whether an aircraft position lies within an airspace polygon.

**Why:**  
`contains()` excludes points exactly on the polygon boundary. For situational awareness, treating an aircraft exactly on a published boundary as outside could hide a relevant situation.

**Consequence:**  
Aircraft exactly on the zone boundary are treated as horizontally contained and continue through the alert logic. This behavior is protected by an automated test.
## ADR-008 — Preserve polygonal geometry in the domain

**Decision:** Zone stores Shapely Polygon or MultiPolygon, including interior
holes. Legacy coordinate lists normalize to Polygon at construction. The field
name `polygon` remains for compatibility.

**Consequence:** Detection calls `covers()` directly (ADR-007), preserving all
parts and boundaries. This adds a geometry-library dependency to the model,
not an OpenAIP representation. Coordinates are longitude/latitude; metric
calculations will require a suitable CRS/geodesic method.

## ADR-009 — Explicit unlimited ceilings and distinct altitude references

**Decision:** Unlimited upper limits have unlimited=True and no numeric value,
unit or reference. The OpenAIP sentinel is decoded only in the adapter. Unlimited
lower limits are rejected. Unit conversion does not equate altitude references.

**Consequence:** Detection skips the upper comparison for unlimited ceilings.
Missing or incomparable altitude still preserves uncertainty. Existing GND
comparability is deferred for a separate domain decision.

## ADR-010 — Separate ingestion, orchestration and deterministic detection

**Decision:** HTTP returns raw dictionaries; the adapter maps external field
names/numeric enums into domain models; detection consumes domain objects only.
The workflow composes those layers without duplicating their logic. OpenAIP is
an integration source, not a replacement for authoritative aviation information.

**Consequence:** Transport/HTTP exceptions, malformed-response errors and
adapter/domain errors remain distinguishable. Invalid supported-contract data
fails at ingestion boundaries. Selected batches fail on the first bad or
unsupported record, report its identity/index, and produce no partial alerts.
Explicit ID selection limits the demo scope; records are not silently skipped.
A replacement source can supply a different adapter without rewriting detection.

## ADR-011 — Separate live verification from deterministic tests

**Decision:** Automated tests use synthetic fixtures and injected HTTP sessions.
Live scripts load credentials only when executed and require manual invocation.
Authoritative comparisons use the separate Finnish sanity-check template.

**Consequence:** Tests prove software composition and behavior, not currency,
authority, activation or legality of real-world data. Synthetic demo positions,
altitudes and timestamps are explicit; no confirmed result is manufactured.
Manual verification remains pending until actual sources and results are recorded.

## ADR-012 - Thin live workflow, raw cache and observation history

**Decision:** Stage 5 composes the existing clients/adapters/detector. Its adapter
selects supported P/R/D types and counts unsupported integer codes; malformed
supported records still abort. Domain detection and older demo policies do not change.

**Consequence:** Raw country-tagged JSON cache has an explicit TTL and atomic
replacement. Corrupt cache fails visibly. Current traffic is never reused from
cache. Freshness visibility mirrors the detector's position-time threshold,
including the existing future-timestamp behavior, without creating stale alerts.

**Decision:** Application logging and append-only JSONL history are separate.
Position samples carry run IDs; a run marker follows position writes. Recent
track context is a chronological view of observations, not inferred movement.

**Consequence:** Single-writer JSONL stays simple but is not transactional across
files. Failures can leave orphan/partial observations; malformed reads fail
explicitly. No database, projection, map or expanded activation semantics are added.
See stage5.md for policies and pending manual smoke-test instructions.

## ADR-013 - Finland-focused projected boundary distance

**Decision:** Source geometry remains EPSG:4326 longitude/latitude degrees for
containment. Degree distances are not metres. Stage 6 uses pyproj to transform
both the polygonal geometry and aircraft Point to EPSG:3067 (ETRS-TM35FIN;
the installed PROJ database labels it EUREF-FIN / TM35FIN(E,N)). One reusable
Transformer uses always_xy=True to retain x=longitude, y=latitude input order.

**Consequence:** Distance is the shortest nonnegative planar distance in metres
to projected_geometry.boundary. Polygon.distance(point) is zero inside; exterior
alone omits holes and does not represent MultiPolygon boundaries. All rings and
components contribute. Invalid geometry/projection fails rather than being repaired.

Distance is added once per actual alert after the existing detector decisions;
UNKNOWN vertical alerts still have known horizontal distances. No outside-near
warnings or signed distances are added. CLI displays kilometres; the model uses metres.

Projection transforms vertices and joins them by straight segments, so nonlinear
edge curvature is approximated. Exact source-boundary points retain zero distance
using a topological boundary predicate, not a degree-distance calculation or a
broad snapping tolerance. No densification or global/geodesic accuracy claim is
made. This CRS choice is specific to Finland, not a universal distance solution.

APIs were verified with installed pyproj 3.8.0 and Shapely 2.1.2 using a Finland
point and round-tripped metric fixtures. A 2 km square constructed in EPSG:3067
has a centre 1000 m from its boundary; the test back-transforms inputs to EPSG:4326
and allows 0.01 m numerical tolerance (not a real-world accuracy guarantee).
API references: https://pyproj4.github.io/pyproj/stable/api/transformer.html and
https://shapely.readthedocs.io/en/2.1.2/manual.html#shapely.ops.transform.

## ADR-014 - Presentation consumes explicit saved results

**Decision:** Versioned report dictionaries explicitly serialize allowed fields,
enums, vertical limits and GeoJSON. Folium and Streamlit consume that same shape;
neither determines whether an alert exists. A per-run artifact bundle supplements,
not replaces, JSONL history. Latest-live UI reads artifacts, never invokes HTTP.

**Consequence:** Display order is explicit: GeoJSON uses lon/lat, Folium locations
use lat/lon. Full polygonal geometry preserves holes and components. Metric CRS
and detection semantics remain in the core. Text status accompanies colour.
The Streamlit wrapper may be removed while clients, adapters, detection, history,
CLI reports and standalone Folium HTML remain usable.

**Decision:** A deterministic invented scenario uses domain objects and the real
detector. Its tracks use isolated Stage 5 history; every output says SYNTHETIC.

**Consequence:** Demonstrations do not manufacture claims about live traffic or
sensitive real sites. Zero live alerts remains a normal valid output. Browser
assets/tiles may need internet even though artifact generation is offline.
