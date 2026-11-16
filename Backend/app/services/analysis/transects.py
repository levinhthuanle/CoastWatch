"""
Transect generation and shoreline displacement measurement.
"""
import logging
import math
from typing import Any, Dict, List, Tuple

import numpy as np
from shapely.geometry import LineString, MultiLineString, Point, mapping
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


def _perpendicular_transect(
    point: Point,
    bearing_deg: float,
    half_length_m: float,
    epsg: int = 32648,
) -> LineString:
    """
    Create a transect line perpendicular to a given bearing, centred on *point*.

    Args:
        point: Shapely Point (lon, lat) in EPSG:4326
        bearing_deg: Bearing of the shoreline at this point (degrees from North)
        half_length_m: Half-length of the transect in metres
        epsg: UTM CRS for metric distance calculations

    Returns:
        Shapely LineString in EPSG:4326
    """
    from pyproj import Transformer  # type: ignore

    # Convert point to UTM for metric distance
    to_utm = Transformer.from_crs(4326, epsg, always_xy=True)
    to_wgs = Transformer.from_crs(epsg, 4326, always_xy=True)

    x_m, y_m = to_utm.transform(point.x, point.y)

    # Perpendicular bearing
    perp_bearing_rad = math.radians((bearing_deg + 90) % 360)

    dx = math.sin(perp_bearing_rad) * half_length_m
    dy = math.cos(perp_bearing_rad) * half_length_m

    p1 = to_wgs.transform(x_m - dx, y_m - dy)
    p2 = to_wgs.transform(x_m + dx, y_m + dy)

    return LineString([p1, p2])


def _bearing_between(p1: tuple, p2: tuple) -> float:
    """Compute azimuth (degrees from North) from p1 to p2 in geographic coords."""
    lon1, lat1 = math.radians(p1[0]), math.radians(p1[1])
    lon2, lat2 = math.radians(p2[0]), math.radians(p2[1])

    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def generate_transects(
    shoreline_geojson: Dict[str, Any],
    spacing_m: float = 100.0,
    half_length_m: float = 200.0,
) -> List[Dict[str, Any]]:
    """
    Generate transect lines perpendicular to a shoreline.

    Args:
        shoreline_geojson: GeoJSON dict with LineString (or MultiLineString) geometry
        spacing_m: Distance between transects along the shoreline in metres
        half_length_m: Half-length of each transect in metres

    Returns:
        List of GeoJSON Feature dicts with LineString geometry
    """
    try:
        from pyproj import Transformer  # type: ignore
        geom_type = shoreline_geojson.get("type", "")

        if geom_type == "FeatureCollection":
            geometries = [
                f["geometry"]
                for f in shoreline_geojson.get("features", [])
                if f.get("geometry")
            ]
        elif geom_type == "Feature":
            geometries = [shoreline_geojson["geometry"]]
        else:
            geometries = [shoreline_geojson]

        lines = []
        for geom in geometries:
            if geom["type"] == "LineString":
                lines.append(LineString(geom["coordinates"]))
            elif geom["type"] == "MultiLineString":
                for coords in geom["coordinates"]:
                    lines.append(LineString(coords))

        if not lines:
            return []

        shoreline = unary_union(lines)

        # Project to UTM for metric operations
        # Zone 48N covers Vietnam (approx 102–108°E)
        to_utm = Transformer.from_crs(4326, 32648, always_xy=True)
        to_wgs = Transformer.from_crs(32648, 4326, always_xy=True)

        if hasattr(shoreline, "geom_type") and shoreline.geom_type in ("MultiLineString", "GeometryCollection"):
            shore_coords = []
            for geom in shoreline.geoms:
                shore_coords.extend(list(geom.coords))
        elif hasattr(shoreline, "coords"):
            shore_coords = list(shoreline.coords)
        else:
            shore_coords = []

        if not shore_coords:
            return []

        utm_coords = [to_utm.transform(lon, lat) for lon, lat in shore_coords]
        utm_line = LineString(utm_coords)
        total_length = utm_line.length

        transects = []
        distance = 0.0
        idx = 0

        while distance <= total_length:
            utm_pt = utm_line.interpolate(distance)
            wgs_pt_xy = to_wgs.transform(utm_pt.x, utm_pt.y)
            wgs_pt = Point(wgs_pt_xy)

            # Bearing from nearby point
            ahead_distance = min(distance + 10, total_length)
            utm_pt2 = utm_line.interpolate(ahead_distance)
            bearing = math.degrees(
                math.atan2(utm_pt2.x - utm_pt.x, utm_pt2.y - utm_pt.y)
            )

            perp_bearing_rad = math.radians((bearing + 90) % 360)
            dx = math.sin(perp_bearing_rad) * half_length_m
            dy = math.cos(perp_bearing_rad) * half_length_m

            p1 = to_wgs.transform(utm_pt.x - dx, utm_pt.y - dy)
            p2 = to_wgs.transform(utm_pt.x + dx, utm_pt.y + dy)

            transect_line = LineString([p1, p2])

            transects.append({
                "type": "Feature",
                "geometry": mapping(transect_line),
                "properties": {
                    "transect_id": idx,
                    "distance_along_shore_m": distance,
                    "epr_m_per_year": None,
                    "displacement_m": None,
                },
            })

            distance += spacing_m
            idx += 1

        logger.info("Generated %d transects with %dm spacing", len(transects), spacing_m)
        return transects

    except ImportError:
        logger.warning("pyproj not available; returning empty transects")
        return []


def measure_displacement(
    transects: List[Dict[str, Any]],
    shoreline_t1_geojson: Dict[str, Any],
    shoreline_t2_geojson: Dict[str, Any],
) -> List[float]:
    """
    Measure shoreline displacement along each transect between two dates.

    Returns:
        List of displacements in metres (positive = seaward, negative = landward)
    """
    try:
        from pyproj import Transformer  # type: ignore

        to_utm = Transformer.from_crs(4326, 32648, always_xy=True)

        def _geojson_to_shapely(geojson: Dict) -> Any:
            geom_type = geojson.get("type", "")
            if geom_type == "FeatureCollection":
                lines = []
                for f in geojson.get("features", []):
                    g = f.get("geometry", {})
                    if g.get("type") == "LineString":
                        lines.append(LineString(g["coordinates"]))
                    elif g.get("type") == "MultiLineString":
                        for part in g["coordinates"]:
                            lines.append(LineString(part))
                return unary_union(lines) if lines else None
            elif geom_type == "Feature":
                g = geojson["geometry"]
                if g["type"] == "MultiLineString":
                    return unary_union([LineString(part) for part in g["coordinates"]])
                return LineString(g["coordinates"])
            elif geom_type == "LineString":
                return LineString(geojson["coordinates"])
            elif geom_type == "MultiLineString":
                return unary_union([LineString(part) for part in geojson["coordinates"]])
            return None

        shore_t1 = _geojson_to_shapely(shoreline_t1_geojson)
        shore_t2 = _geojson_to_shapely(shoreline_t2_geojson)

        displacements = []

        for transect_feature in transects:
            transect_coords = transect_feature["geometry"]["coordinates"]
            transect_line = LineString(transect_coords)

            disp = 0.0

            if shore_t1 and shore_t2:
                int1 = transect_line.intersection(shore_t1)
                int2 = transect_line.intersection(shore_t2)

                if not int1.is_empty and not int2.is_empty:
                    # Take first intersection point if multiple
                    pt1 = int1 if int1.geom_type == "Point" else list(int1.geoms)[0]
                    pt2 = int2 if int2.geom_type == "Point" else list(int2.geoms)[0]

                    p1_utm = to_utm.transform(pt1.x, pt1.y)
                    p2_utm = to_utm.transform(pt2.x, pt2.y)

                    disp = math.sqrt(
                        (p2_utm[0] - p1_utm[0]) ** 2 + (p2_utm[1] - p1_utm[1]) ** 2
                    )

                    # Sign: positive if t2 is farther seaward than t1
                    # Use transect midpoint as reference direction
                    mid = transect_line.centroid
                    mid_utm = to_utm.transform(mid.x, mid.y)
                    vec_t1 = (p1_utm[0] - mid_utm[0], p1_utm[1] - mid_utm[1])
                    vec_t2 = (p2_utm[0] - mid_utm[0], p2_utm[1] - mid_utm[1])
                    dot = vec_t1[0] * vec_t2[0] + vec_t1[1] * vec_t2[1]
                    mag_t2 = math.sqrt(vec_t2[0] ** 2 + vec_t2[1] ** 2) + 1e-10
                    mag_t1 = math.sqrt(vec_t1[0] ** 2 + vec_t1[1] ** 2) + 1e-10

                    if mag_t2 > mag_t1:
                        disp = disp  # seaward
                    else:
                        disp = -disp  # landward

            displacements.append(disp)

        return displacements

    except ImportError:
        logger.warning("pyproj not available; returning zero displacements")
        return [0.0] * len(transects)


def compute_epr(
    displacements: List[float],
    years_elapsed: float,
) -> List[float]:
    """
    Compute End Point Rate (EPR) for each transect.

    EPR = displacement / years_elapsed  (m/year)

    Args:
        displacements: List of displacements in metres per transect
        years_elapsed: Time between the two shorelines in fractional years

    Returns:
        List of EPR values (m/year) per transect
    """
    if years_elapsed <= 0:
        raise ValueError("years_elapsed must be positive")

    return [d / years_elapsed for d in displacements]
