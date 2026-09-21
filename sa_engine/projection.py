"""Finland-focused horizontal boundary distances in EPSG:3067 metres."""

from functools import partial
from math import isfinite

from pyproj import Transformer
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import transform

# Reuse one configured transform. Shapely coordinates are always x/y (lon/lat).
TO_FINLAND_METRES = Transformer.from_crs('EPSG:4326', 'EPSG:3067', always_xy=True)
_project = partial(TO_FINLAND_METRES.transform, errcheck=True)


def distance_to_boundary_m(geometry: Polygon | MultiPolygon, lon: float, lat: float) -> float:
    """Shortest nonnegative planar distance to all projected boundary rings.

    Inputs are geographic lon/lat; target CRS is Finland-specific, not global.
    Ring vertices are projected and joined by straight segments. Exact source
    boundary incidence remains zero despite nonlinear projection of those edges.
    Invalid input/projection fails visibly; geometry is never repaired.
    """
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise ValueError('Boundary distance requires Polygon or MultiPolygon')
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError('Boundary distance requires valid nonempty geometry')
    if (not isfinite(lon) or not isfinite(lat)
            or not -180 <= lon <= 180 or not -90 <= lat <= 90):
        raise ValueError('Position must contain finite WGS84 longitude/latitude')
    minx, miny, maxx, maxy = geometry.bounds
    if not (-180 <= minx <= maxx <= 180 and -90 <= miny <= maxy <= 90):
        raise ValueError('Geometry must use WGS84 longitude/latitude coordinates')
    point = Point(lon, lat)
    projected_geometry = transform(_project, geometry)
    projected_point = transform(_project, point)
    if projected_geometry.is_empty or not projected_geometry.is_valid:
        raise ValueError('Projected geometry is invalid or empty')
    distance = float(projected_geometry.boundary.distance(projected_point))
    if not isfinite(distance):
        raise ValueError('Projected boundary distance is not finite')
    # No degree distance or broad tolerance is used here: only exact incidence.
    if geometry.boundary.covers(point):
        return 0.0
    return distance
