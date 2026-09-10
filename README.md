# Airspace SA Engine

A small Python situational-awareness engine for evaluating aircraft positions against airspace zones.

The project is both a portfolio project and a hands-on way to learn aviation data, geospatial processing, external APIs, and deterministic rule-based alerting.

## What it does

Given an aircraft state and a set of airspace zones, the engine determines whether the aircraft is horizontally inside a zone and whether its altitude can be meaningfully compared with the zone's vertical limits.

It produces an `AirspaceAlert` describing the situation rather than claiming that a legal airspace infringement has occurred.

## Current milestone — M1

The deterministic detection engine is complete.

Implemented so far:

* domain models for aircraft, airspace zones, vertical limits, and alerts
* altitude units and references including MSL, AGL, flight level, and standard pressure
* deterministic horizontal containment using Shapely
* explicit handling of boundary cases
* vertical comparison states: `COMPARABLE`, `APPROXIMATE`, and `UNKNOWN`
* freshness and on-ground checks
* danger, restricted, and prohibited area alert mapping
* pytest test suite with 23 passing tests
* 100% geometry coverage and 99% total coverage

## Design principles

* Detection is deterministic. An LLM will never decide whether an alert exists.
* Danger areas and prohibited areas are not treated as equivalent.
* Units may be converted, but altitude references are never silently merged.
* Unknown vertical information does not erase valid horizontal containment.
* Alerts describe detected conditions, not legal conclusions.

## Next milestone

Stage 3 integrates OpenAIP airspace data.

The next steps include:

* authenticated API requests
* OpenAIP airspace type and vertical-limit parsing
* GeoJSON polygon handling
* pagination
* synthetic test fixtures
* validation of parsed data against Finnish aeronautical information

Real OpenAIP responses will not be committed to the public repository. Synthetic fixtures will mirror the API structure without reproducing source data.

## Tech

Python · pytest · Shapely · Ruff · requests · OpenAIP

## Project status

Work in progress.
