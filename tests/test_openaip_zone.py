import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from shapely.geometry import MultiPolygon, Polygon

from sa_engine.geometry import find_alerts
from sa_engine.models import ActivationStatus, AlertType, VerificationStatus, ZoneType
from sa_engine.openaip_adapter import parse_zone


@pytest.fixture
def records():
    path = Path(__file__).parent / 'fixtures' / 'openaip_airspaces.json'
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.mark.parametrize('index,zone_type,alert_type', [
    (0, ZoneType.RESTRICTED, AlertType.RESTRICTED_AREA_ENTRY),
    (1, ZoneType.DANGER, AlertType.DANGER_AREA_EXPOSURE),
    (2, ZoneType.PROHIBITED, AlertType.PROHIBITED_AREA_ENTRY),
])
def test_finite_zone_conversion(records, aircraft_inside, index, zone_type, alert_type):
    raw = records[index]
    original = deepcopy(raw)
    zone = parse_zone(raw)
    assert raw == original
    assert zone.id == raw['_id']
    assert zone.name == raw['name']
    assert zone.zone_type is zone_type
    assert zone.source == 'openaip'
    assert zone.activation_status is ActivationStatus.UNKNOWN
    assert isinstance(zone.polygon, Polygon)
    assert len(zone.polygon.interiors) == 1
    alerts = find_alerts(aircraft_inside, [zone], now=1010)
    assert len(alerts) == 1
    assert alerts[0].alert_type is alert_type
    assert alerts[0].verification_status is VerificationStatus.POTENTIAL
    assert find_alerts(replace(aircraft_inside, baro_altitude_ft=4000), [zone], now=1010) == []


@pytest.mark.parametrize('index', [0, 3])
@pytest.mark.parametrize('lon,lat,expected', [
    (24.25,60.25,1),  # first component interior
    (24,61,1),       # exterior edge
    (24,60,1),       # exterior vertex
    (25,61,0),       # hole interior
    (24.5,61,1),     # hole boundary is covered
    (26.5,60.5,0),   # gap between components
])
def test_fixture_geometry_detection(records, aircraft_inside, index, lon, lat, expected):
    zone = parse_zone(records[index])
    aircraft = replace(aircraft_inside, lon=lon, lat=lat)
    assert len(find_alerts(aircraft, [zone], now=1010)) == expected


def test_unlimited_multipolygon(records, aircraft_inside):
    zone = parse_zone(records[3])
    assert isinstance(zone.polygon, MultiPolygon)
    assert len(zone.polygon.geoms) == 2
    assert zone.upper.unlimited
    assert (zone.upper.value, zone.upper.unit, zone.upper.reference) == (None, None, None)
    aircraft = replace(aircraft_inside, lon=27.5, lat=60.5, baro_altitude_ft=120000)
    alerts = find_alerts(aircraft, [zone], now=1010)
    assert len(alerts) == 1
    assert alerts[0].verification_status is VerificationStatus.CONFIRMED
    alerts = find_alerts(replace(aircraft, baro_altitude_ft=None), [zone], now=1010)
    assert alerts[0].verification_status is VerificationStatus.UNKNOWN


@pytest.mark.parametrize('field', ['_id','name','type','lowerLimit','upperLimit','geometry'])
def test_missing_required_field(records, field):
    del records[0][field]
    with pytest.raises(ValueError, match=field):
        parse_zone(records[0])


@pytest.mark.parametrize('field,value', [
    ('_id', None), ('name', ' '), ('type', True), ('type', []), ('type', 7),
    ('lowerLimit', None), ('upperLimit', {}), ('geometry', None),
    ('geometry', {'type': 'Point', 'coordinates': [24,60]}),
    ('geometry', {'type': 'Polygon', 'coordinates': [[[24,60],[25,60]]]}),
])
def test_malformed_required_field(records, field, value):
    records[0][field] = value
    with pytest.raises(ValueError):
        parse_zone(records[0])


@pytest.mark.parametrize('key,value', [
    ('value', '3500'), ('value', True), ('value', float('nan')),
    ('value', float('inf')), ('unit', True), ('unit', 99),
    ('referenceDatum', []), ('referenceDatum', 99),
])
def test_malformed_vertical_limit(records, key, value):
    records[0]['upperLimit'][key] = value
    with pytest.raises(ValueError):
        parse_zone(records[0])


def test_unlimited_lower_rejected(records):
    records[0]['lowerLimit'] = records[3]['upperLimit']
    with pytest.raises(ValueError, match='lower boundary cannot be unlimited'):
        parse_zone(records[0])


@pytest.mark.parametrize('raw', [None, [], 'invalid'])
def test_zone_requires_object(raw):
    with pytest.raises(ValueError, match='must be an object'):
        parse_zone(raw)
