# Data sources and attribution

Review date: 2026-09-21. Source code, data, API access and map assets have separate
terms. MIT covers Anna's own repository code, not third-party material.
Dependencies retain their own licenses; none are vendored here. Public fixtures
and demo objects are invented, not redistributed aviation datasets. Runtime
files under `runs/` must stay private and outside publication.

## OpenAIP

Official OpenAIP airspace pages identify data as **Creative Commons
Attribution-NonCommercial 4.0 International, unless otherwise stated**:
[official dataset footer](https://www.openaip.net/data/airspaces/676bc0c9ced6d3b9b28e542a).
That footer was available through the search index; direct official-page access
returned HTTP 403 in this environment. This is evidence of the stated license,
not complete verification of current API/account terms. Anna must reopen
[OpenAIP](https://www.openaip.net/) and check current terms before publication or
live/derived-data use. No blanket commercial-use permission is asserted.

For permitted outputs containing OpenAIP data, include attribution such as:
**Airspace data: OpenAIP, Garrecht Avionik GmbH and contributors; CC BY-NC 4.0
unless otherwise stated.** Link the source and
[license](https://creativecommons.org/licenses/by-nc/4.0/), retain supplied
notices, and identify adaptations (for example, conversion to domain geometry).
Check record-specific exceptions. The CC deed requires credit, a license link
and indication of changes, and limits use to noncommercial purposes.

OpenAIP is an integration source, not the sole authoritative aviation source.
[Manual Finnish comparisons](docs/openaip_manual_check.md) are a separate,
still-pending process; passing tests do not establish operational authority.

## OpenSky Network

The current official [Terms of Use](https://opensky-network.org/about/terms-of-use)
limit the base permission to nonprofit research/education. Any commercial or
for-profit use requires a written license; operational REST use in products,
services or automated systems, including internal use, requires prior written
agreement. Having credentials alone does not establish permission for that use.

The terms restrict redistribution and require anonymization/de-identification
for publication/disclosure. Do not treat a raw capture or saved live map as a
freely publishable artifact. Publications using the data require the specified
citation and a copy/link sent to OpenSky; follow section 4 for the exact details:
Sch?fer et al., *Bringing up OpenSky: A large-scale ADS-B sensor network for
research*, ACM/IEEE IPSN, April 2014.

Live OpenSky observations are **not distributed** with this repository. The
public reproducible example uses synthetic fixtures/traffic. Review the full
terms and obtain any required permission before live use or data publication;
this repository's MIT license cannot grant it.

## Maps and public screenshots

The default Folium map uses OpenStreetMap tiles. Preserve the displayed
OpenStreetMap contributor attribution and check
[OpenStreetMap copyright/licensing](https://www.openstreetmap.org/copyright)
when publishing map images. A synthetic scenario removes live aviation-data
redistribution concerns, but does not remove basemap attribution obligations.
