# Manual Finnish airspace sanity check

Status: PENDING. No live OpenAIP or authoritative comparison was performed for
Chunks B/C. Automated tests use fake HTTP responses and do not validate live data.

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

| Field | Zone 1 | Zone 2 | Zone 3 |
| --- | --- | --- | --- |
| OpenAIP ID / name | pending | pending | pending |
| OpenAIP retrieval UTC | | | |
| Authoritative source URL / section / chart | | | |
| Source effective / retrieval date | | | |
| Identifier / name comparison | | | |
| P/R/D type comparison | | | |
| Lower: value / unit / reference | | | |
| Upper: value / unit / reference or unlimited | | | |
| Broad footprint, parts and holes | | | |
| Discrepancies / unresolved questions | | | |
| Reviewer / comparison date / result | pending | pending | pending |

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
