# Offline OpenAIP fixtures

These are synthetic records, not downloaded airspaces or navigation data.
The name/type/limit/geometry structure follows inspect_zones.py and the existing
adapter tests. `_id` is assumed to be a nonempty string identifier.
Coordinates, IDs and names are invented. Polygon holes and a disjoint
MultiPolygon deliberately exercise preservation of geometry through detection.
The array contains individual records, not the API pagination envelope.
Only fields consumed by the adapter plus an ignored country field are included.
Activation is unknown; names and zone types do not establish current activation.

OpenSky fixture: `opensky_states_synthetic.json` contains six invented 18-field
rows, not captured traffic: normal, null altitude, on-ground, FLARM, UAV category,
and missing longitude. IDs, callsigns, locations and timestamps are synthetic.
The envelope has a synthetic response time. This fixture makes no claim about
real coverage or the operational meaning of any particular aircraft.
