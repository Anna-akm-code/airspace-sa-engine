import pytest
from shapely.geometry import MultiPolygon, Point, Polygon

from sa_engine.models import (
    VerticalReference,
    VerticalUnit,
    ZoneType,
)
from sa_engine.openaip_adapter import (
    parse_geometry,
    parse_vertical_limit,
    parse_zone_type,
)


def test_parse_restricted_zone_type():
    assert parse_zone_type(1) == ZoneType.RESTRICTED


def test_parse_danger_zone_type():
    assert parse_zone_type(2) == ZoneType.DANGER


def test_parse_prohibited_zone_type():
    assert parse_zone_type(3) == ZoneType.PROHIBITED


def test_parse_unsupported_zone_type():
    # Code inside this block is expected to raise a ValueError
    # "match" checks the error message
    with pytest.raises(ValueError, match="Unsupported OpenAIP airspace type: 7"): 
        parse_zone_type(7)

def test_parse_vertical_limit_ground():
    result = parse_vertical_limit(
        {
            "value": 0,
            "unit": 1,
            "referenceDatum": 0,
        }
    )

    assert result.value == 0
    assert result.unit is VerticalUnit.FT
    assert result.reference is VerticalReference.GND
    assert result.unlimited is False


def test_parse_vertical_limit_msl():
    result = parse_vertical_limit(
        {
            "value": 3500,
            "unit": 1,
            "referenceDatum": 1,
        }
    )

    assert result.value == 3500
    assert result.unit is VerticalUnit.FT
    assert result.reference is VerticalReference.MSL
    assert result.unlimited is False


def test_parse_vertical_limit_flight_level():
    result = parse_vertical_limit(
        {
            "value": 195,
            "unit": 6,
            "referenceDatum": 2,
        }
    )

    assert result.value == 195
    assert result.unit is VerticalUnit.FL
    assert result.reference is VerticalReference.STANDARD_PRESSURE
    assert result.unlimited is False


def test_parse_vertical_limit_unlimited():
    result = parse_vertical_limit(
        {
            "value": 999,
            "unit": 6,
            "referenceDatum": 2,
        }
    )

    assert result.unlimited is True
    assert result.value is None
    assert result.unit is None
    assert result.reference is None

def test_parse_vertical_limit_rejects_unsupported_unit():
    with pytest.raises(
        ValueError,
        match="Unsupported OpenAIP vertical limit",
    ):
        parse_vertical_limit(
            {
                "value": 1000,
                "unit": 99,
                "referenceDatum": 1,
            }
        )


# Check that GeoJSON → Shapely Polygon → usable for detection
def test_parse_polygon_geometry():
    raw_geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [24.0, 60.0],
                [25.0, 60.0],
                [25.0, 61.0],
                [24.0, 61.0],
                [24.0, 60.0],
            ]
        ],
    }

    result = parse_geometry(raw_geometry)

    assert isinstance(result, Polygon)
    assert list(result.exterior.coords) == [
        tuple(coordinate) for coordinate in raw_geometry["coordinates"][0]
    ]
    assert result.covers(Point(24.0, 60.5))
    assert result.covers(Point(24.5, 60.5))


# outer polygon → inside, hole → NOT inside
def test_parse_polygon_geometry_preserves_hole():
    raw_geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [24.0, 60.0],
                [26.0, 60.0],
                [26.0, 62.0],
                [24.0, 62.0],
                [24.0, 60.0],
            ],
            [
                [24.5, 60.5],
                [25.5, 60.5],
                [25.5, 61.5],
                [24.5, 61.5],
                [24.5, 60.5],
            ],
        ],
    }

    result = parse_geometry(raw_geometry)

    assert result.covers(Point(24.25, 60.25))
    assert not result.covers(Point(25.0, 61.0))


def test_parse_multipolygon_geometry():
    raw_geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [24.0, 60.0],
                    [25.0, 60.0],
                    [25.0, 61.0],
                    [24.0, 61.0],
                    [24.0, 60.0],
                ]
            ],
            [
                [
                    [26.0, 60.0],
                    [27.0, 60.0],
                    [27.0, 61.0],
                    [26.0, 61.0],
                    [26.0, 60.0],
                ]
            ],
        ],
    }

    result = parse_geometry(raw_geometry)

    assert isinstance(result, MultiPolygon)
    assert result.covers(Point(24.5, 60.5))
    assert result.covers(Point(26.5, 60.5))    

def test_parse_geometry_rejects_unsupported_type():
    raw_geometry = {
        "type": "Point",
        "coordinates": [24.5, 60.5],
    }

    with pytest.raises(
        ValueError,
        match="Unsupported OpenAIP geometry type: Point",
    ):
        parse_geometry(raw_geometry)

@pytest.mark.parametrize("geometry_type", ["Polygon", "MultiPolygon"])
def test_parse_geometry_rejects_empty_geometry(geometry_type):
    with pytest.raises(ValueError, match="OpenAIP geometry must not be empty"):
        parse_geometry({"type": geometry_type, "coordinates": []})


def test_parse_geometry_rejects_self_intersecting_polygon():
    raw_geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [24.0, 60.0],
                [25.0, 61.0],
                [25.0, 60.0],
                [24.0, 61.0],
                [24.0, 60.0],
            ]
        ],
    }

    with pytest.raises(ValueError, match="OpenAIP geometry is invalid"):
        parse_geometry(raw_geometry)
