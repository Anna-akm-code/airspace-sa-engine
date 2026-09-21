# Data sources and attribution

Review date: 2026-09-21. Source code, data, API access and map assets have separate
terms. MIT covers Anna's own repository code, not third-party material.
Dependencies retain their own licenses; none are vendored here. Public fixtures
and demo objects are invented, not redistributed aviation datasets. Runtime
files under `runs/` must stay private and outside publication.

## OpenAIP

OpenAIP states that its data is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/) license.

OpenAIP also explicitly states that third parties may share, remix, transform and build on its data, and may ship OpenAIP data with paid/commercial applications as long as they do not exclusively sell OpenAIP data itself, for example as a paid standalone data-update service.

Official source: [OpenAIP](https://www.openaip.net/)

For outputs containing OpenAIP data, retain appropriate attribution and applicable license notices.

OpenAIP is used here as a structured integration source, not as the sole authoritative source for operational aviation information. Manual comparison against authoritative Finnish aeronautical information is handled separately.

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
