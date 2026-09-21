# Manual Finnish airspace sanity check

Status: Three manual record comparisons recorded below, as reported by the
reviewer. This is a small manual sanity check, not exhaustive validation.
Automated tests use fake HTTP responses and do not validate live data.

1. Set OPENAIP_API_KEY in your environment or local .env (already gitignored).
   Never paste the key into source, command arguments, screenshots or reports.
2. Run `python inspect_zones.py`. It fetches every FI page, then displays up to
   three EFP/EFR/EFD-named candidates, preferring one of each naming family.
   Names select candidates; the adapter maps the actual numeric type.
3. To revisit selected records, use `python inspect_zones.py --name "EXACT NAME"
   --name "SECOND EXACT NAME" --limit 3` on one command line.
4. Compare 2–3 selected records against current authoritative Finnish
   aeronautical information (Fintraffic AIS Finland's Finnish AIP/eAIP,
   relevant ENR airspace listings and charts). Record the exact source,
   effective date and retrieval date. Check applicable amendments/supplements;
   this comparison does not establish current activation or legal infringement.
5. Compare identifier/name, P/R/D classification, lower and upper limits
   including units and vertical reference, and broad geographic footprint.
   An OpenAIP internal ID may differ from the published airspace designator.
   A bounding box is only a coarse check: inspect raw geometry and the chart
   for disjoint parts, holes and obvious location/shape mismatches.

OpenAIP is not authoritative. Do not label a zone verified until the comparison
has actually been performed. Preserve discrepancies for investigation.

## Recorded manual comparisons

These reviewer-reported checks cover three records only. They do not validate
all Finnish OpenAIP data or establish OpenAIP as authoritative. Official Finnish
aeronautical information remains the authoritative reference for operational use.

OpenAIP's `0 ft GND` representation is recorded separately from the official
source's `SFC` wording. The comparisons below do not change domain altitude
reference semantics. Precise geometry, broad geographic footprint, polygon parts
and holes were not reported as checked; no geometry validation is claimed.

### EFP10 LOVIISA

| Field | OpenAIP | Authoritative Finnish source |
| --- | --- | --- |
| Designation / name | EFP10 LOVIISA | EFP10 LOVIISA |
| Type | prohibited | Prohibited-area designation EFP10 |
| Lower limit | 0 ft GND (surface representation) | SFC |
| Upper limit | FL65 | FL65 |
| Activity type | Not recorded in this comparison | NUCLEAR |
| Activity time | Not recorded in this comparison | H24 |

Result: consistent for designation/type and vertical limits checked.
Activity details above are recorded from the official source; no comparison of
OpenAIP activation handling was reported.

### EFR100

| Field | OpenAIP | Authoritative Finnish source |
| --- | --- | --- |
| Designation / name | EFR100 | EFR100 / IT?INEN RAJOITUSALUE |
| Type | restricted | restricted |
| Lower limit | 0 ft GND (surface representation) | SFC |
| Upper limit | FL280 | FL280 |

Result: consistent for type and vertical limits checked.

### EFD100 KATAJALUOTO

| Field | OpenAIP | Authoritative Finnish source |
| --- | --- | --- |
| Designation / name | EFD100 KATAJALUOTO | EFD100 KATAJALUOTO |
| Type | danger | Danger-area designation EFD100 |
| Lower limit | 0 ft GND (surface representation) | SFC |
| Upper limit | UNLIMITED | UNL |

Result: consistent for designation/type and vertical limits checked.

Exact official source URLs/sections, source effective dates, retrieval dates,
reviewer identity and comparison dates were not supplied with these results.
They remain unrecorded; no dates or citations have been inferred. These checks
do not establish current activation, operational suitability or legal infringement.

## Client assumptions and failures

The client requests one-based pages using `page`, and requires integer `page`
and `totalPages` plus an `items` list of objects. An empty first page with
`totalPages` 0 or 1 is accepted. Inconsistent page numbers, changing page counts,
and empty pages in a multi-page result fail visibly. These assumptions still
need live confirmation; the old script printed these fields but saved no response.
Each page is fetched once in order. Server-provided duplicates are preserved;
there is no ID deduplication or guarantee of a snapshot while the server changes.

Timeout, connection and HTTP failures propagate as requests exceptions. Invalid
JSON/envelopes raise OpenAIPResponseError. Adapter failures remain ValueError.
No retries or partial results are returned. The manual script stops on failures.
An injected session belongs to its caller; use a requests.Session context manager
when connection reuse is desired. The default transport uses requests.get.

The synthetic-aircraft end-to-end demo is documented in [README](../README.md).
Running it demonstrates software behavior and does not complete this comparison.
