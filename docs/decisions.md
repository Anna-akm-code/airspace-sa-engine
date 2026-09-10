ADR = Architecture Decision Record
#ADR-001 — Why OpenAIP rather than the authoritative AIP

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