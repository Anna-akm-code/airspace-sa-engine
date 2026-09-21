"""Synthetic projected geometry: no guessed degree-to-metre conversions."""

from dataclasses import replace
from math import isfinite
from unittest.mock import Mock

import pytest
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import transform

from sa_engine.geometry import find_alerts
from sa_engine.models import VerificationStatus
from sa_engine.projection import TO_FINLAND_METRES, distance_to_boundary_m

TO_GEOGRAPHIC = Transformer.from_crs('EPSG:3067', 'EPSG:4326', always_xy=True)


def geographic(geometry):
    return transform(TO_GEOGRAPHIC.transform, geometry)


def distance(metric_geometry, x, y):
    lon, lat = TO_GEOGRAPHIC.transform(x, y)
    return distance_to_boundary_m(geographic(metric_geometry), lon, lat)


def test_finland_transform_axis_order_and_units():
    x, y = TO_FINLAND_METRES.transform(24.9384, 60.1699)
    assert isfinite(x) and isfinite(y)
    assert 380000 < x < 390000
    assert 6670000 < y < 6680000
    assert all(axis.unit_name == 'metre' for axis in TO_FINLAND_METRES.target_crs.axis_info)


def test_known_one_kilometre():
    square = box(400000, 6700000, 402000, 6702000)
    assert square.distance(Point(401000,6701000)) == 0  # Wrong operation for our goal.
    result = distance(square, 401000, 6701000)
    assert isinstance(result, float)
    assert result == pytest.approx(1000, abs=0.01)


def test_metric_boundary_point():
    assert distance(box(400000,6700000,402000,6702000),400000,6701000) == pytest.approx(0, abs=0.01)


def test_source_edge_boundary_stays_zero():
    # Middle of a long geographic edge need not lie on its projected vertex chord.
    polygon = box(24,60,26,62)
    assert distance_to_boundary_m(polygon,24,61) == 0.0


def test_nearest_boundary_is_hole():
    outer = box(400000,6700000,410000,6710000)
    hole = box(404000,6704000,406000,6706000)
    polygon = Polygon(outer.exterior.coords, [hole.exterior.coords])
    assert distance(polygon,403000,6705000) == pytest.approx(1000, abs=0.01)


def test_multipolygon_second_component():
    geometry = MultiPolygon([box(390000,6700000,392000,6702000),
                             box(400000,6700000,402000,6702000)])
    assert distance(geometry,401000,6701000) == pytest.approx(1000, abs=0.01)


@pytest.mark.parametrize('geometry', [Point(24,60), Polygon(),
    Polygon([(24,60),(25,61),(25,60),(24,61),(24,60)])])
def test_reject_bad_geometry(geometry):
    with pytest.raises(ValueError):
        distance_to_boundary_m(geometry,24.5,60.5)


@pytest.mark.parametrize('lon,lat', [(float('nan'),60),(24,91)])
def test_reject_bad_position(lon,lat):
    with pytest.raises(ValueError):
        distance_to_boundary_m(box(24,60,25,61),lon,lat)


@pytest.mark.parametrize('zone_fixture,status', [
    ('danger_zone',VerificationStatus.CONFIRMED),
    ('msl_zone',VerificationStatus.POTENTIAL),
    ('agl_zone',VerificationStatus.UNKNOWN),
])
def test_distance_for_each_verification(request, aircraft_inside, zone_fixture, status):
    zone = request.getfixturevalue(zone_fixture)
    alerts = find_alerts(aircraft_inside,[zone],now=1010)
    assert len(alerts) == 1
    assert alerts[0].verification_status is status
    assert isfinite(alerts[0].distance_to_boundary_m)
    assert alerts[0].distance_to_boundary_m > 0


def test_missing_altitude_and_boundary(danger_zone, aircraft_inside):
    vertex = danger_zone.polygon.exterior.coords[0]
    aircraft = replace(aircraft_inside,lon=vertex[0],lat=vertex[1],baro_altitude_ft=None)
    alert = find_alerts(aircraft,[danger_zone],now=1010)[0]
    assert alert.verification_status is VerificationStatus.UNKNOWN
    assert alert.distance_to_boundary_m == pytest.approx(0,abs=0.01)


def test_non_alert_pairs_never_project(danger_zone, aircraft_outside, aircraft_above, monkeypatch):
    helper = Mock(side_effect=AssertionError('Must not project excluded pairs'))
    monkeypatch.setattr('sa_engine.geometry.distance_to_boundary_m',helper)
    assert find_alerts(aircraft_outside,[danger_zone],now=1010) == []
    assert find_alerts(aircraft_above,[danger_zone],now=1010) == []
    helper.assert_not_called()
