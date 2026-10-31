"""Build network-distance OD tables for Gaussian 2SFCA.

Routing uses network edge ``length`` in meters and an explicitly projected,
metric graph CRS. For directed networks, paths run from residential origins
to park entrances (reverse searches from park entrances are an optimization).
"""
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd


def _gis_dependencies():
    try:
        import geopandas as gpd
        import networkx as nx
        from scipy.spatial import cKDTree
        from pyproj import CRS
        from shapely.geometry import Point
        from shapely.ops import nearest_points
        from shapely.strtree import STRtree
    except ImportError as exc:
        raise ImportError('Routing requires pip install -e ".[routing]"') from exc
    return gpd, nx, cKDTree, CRS, Point, nearest_points, STRtree


def _required_geometry(frame, id_column, label, gpd):
    if not isinstance(frame, gpd.GeoDataFrame):
        raise TypeError(f"{label} must be a GeoDataFrame with geometry and CRS")
    if frame.crs is None:
        raise ValueError(f"{label} must have a declared CRS")
    if id_column not in frame:
        raise ValueError(f"{label} needs a {id_column} column")
    if frame.empty or frame[id_column].isna().any():
        raise ValueError(f"{label} must have non-null IDs and at least one row")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError(f"{label} contains empty or missing geometries")


def _graph_nodes(graph, nx, CRS):
    if not isinstance(graph, (nx.Graph, nx.DiGraph, nx.MultiGraph, nx.MultiDiGraph)):
        raise TypeError("graph must be a NetworkX graph, typically an OSMnx walking graph")
    if graph.number_of_nodes() == 0 or graph.number_of_edges() == 0:
        raise ValueError("Road graph must contain nodes and edges")
    if "crs" not in graph.graph:
        raise ValueError("Road graph needs graph.graph['crs'] (projected metric CRS)")
    crs = CRS.from_user_input(graph.graph["crs"])
    if not crs.is_projected or any(a.unit_name.lower() not in ("metre", "meter") for a in crs.axis_info):
        raise ValueError("Road graph CRS must be projected in meters (e.g. local UTM); use ox.project_graph")
    node_ids = list(graph.nodes)
    xy = np.asarray([[graph.nodes[n].get("x", np.nan), graph.nodes[n].get("y", np.nan)]
                     for n in node_ids], dtype=float)
    if not np.isfinite(xy).all():
        raise ValueError("Every graph node must have finite x/y coordinates")
    for *_, data in graph.edges(data=True):
        length = data.get("length")
        if length is None or not np.isfinite(length) or length < 0:
            raise ValueError("Every road edge needs a finite, nonnegative length in meters")
    return crs, node_ids, xy


def build_network_distances(
    units: Any,
    parks: Any,
    graph: Any,
    *,
    origins: Any = None,
    entrances: Any = None,
    max_distance_km: float | None = None,
    max_snap_m: float = 1000,
) -> pd.DataFrame:
    """Return a long-form OD table usable by ``calculate_accessibility``.

    The residential origin is each unit's representative point unless ``origins``
    supplies a point per ``unit_id``. Park destinations are ``entrances`` points
    (multiple points per park allowed). Without entrance data, park Point geometry
    is used, or for polygon parks the boundary point closest to any graph node.
    The polygon fallback is only a proxy, not an inferred true entrance.

    All inputs need declared CRS. Graph nodes are projected x/y meters, road
    edges have meter ``length`` weights. Results include straight-line offsets
    from input points to their snapped nodes; these connectors are approximate.
    Disconnected and out-of-range pairs are omitted, never assigned distance 0.
    """
    gpd, nx, KDTree, CRS, Point, nearest_points, STRtree = _gis_dependencies()
    _required_geometry(units, "unit_id", "units", gpd)
    _required_geometry(parks, "park_id", "parks", gpd)
    if units.unit_id.astype(str).duplicated().any():
        raise ValueError("Unit IDs must be unique")
    if parks.park_id.astype(str).duplicated().any():
        raise ValueError("Park IDs must be unique")
    if not np.isfinite(max_snap_m) or max_snap_m <= 0:
        raise ValueError("max_snap_m must be a positive finite number")
    if max_distance_km is not None and (not np.isfinite(max_distance_km) or max_distance_km <= 0):
        raise ValueError("max_distance_km must be positive and finite")
    crs, node_ids, xy = _graph_nodes(graph, nx, CRS)
    tree = KDTree(xy)
    orig = units.to_crs(crs)
    dest = parks.to_crs(crs)
    unit_ids = units.unit_id.astype(str).tolist()
    park_ids = parks.park_id.astype(str).tolist()

    if origins is None:
        origin_points = [geom if geom.geom_type == "Point" else geom.representative_point()
                         for geom in orig.geometry]
    else:
        _required_geometry(origins, "unit_id", "origins", gpd)
        o = origins.to_crs(crs)
        if o.unit_id.astype(str).duplicated().any() or set(o.unit_id.astype(str)) != set(unit_ids):
            raise ValueError("origins must contain exactly one point per unit_id")
        if not all(g.geom_type == "Point" for g in o.geometry):
            raise ValueError("origins must contain Point geometries")
        origin_points = [dict(zip(o.unit_id.astype(str), o.geometry))[u] for u in unit_ids]

    # Known entrances are strongly preferred, particularly for large parks.
    park_points = defaultdict(list)
    if entrances is not None:
        _required_geometry(entrances, "park_id", "entrances", gpd)
        e = entrances.to_crs(crs)
        if not all(g.geom_type == "Point" for g in e.geometry):
            raise ValueError("entrances must contain Point geometries")
        for pid, geometry in zip(e.park_id.astype(str), e.geometry):
            if pid not in park_ids:
                raise ValueError(f"entrances reference unknown park_id: {pid}")
            park_points[pid].append(geometry)

    if any(not park_points[p] for p in park_ids):
        road_points = [Point(*pair) for pair in xy]
        boundary_tree = STRtree(road_points)
        for pid, geometry in zip(park_ids, dest.geometry):
            if park_points[pid]:
                continue
            if geometry.geom_type in {"Polygon", "MultiPolygon"}:
                # Choose a boundary point closest to a road node, rather than a
                # centroid in the interior of a large park.
                nearest_idx = int(boundary_tree.nearest(geometry.boundary))
                point = nearest_points(geometry.boundary, road_points[nearest_idx])[0]
            elif geometry.geom_type == "Point":
                point = geometry
            else:
                raise ValueError("Park geometry must be a Point or (Multi)Polygon")
            park_points[pid].append(point)

    def snap(points, ids, kind):
        coordinates = np.asarray([(p.x, p.y) for p in points], dtype=float)
        if not np.isfinite(coordinates).all():
            raise ValueError(f"{kind} has non-finite coordinates")
        offsets, indices = tree.query(coordinates)
        bad = np.flatnonzero(offsets > max_snap_m)
        if len(bad):
            i = int(bad[0])
            raise ValueError(f"{kind} {ids[i]} is {offsets[i]:.1f}m from the nearest road node; "
                             f"exceeds max_snap_m={max_snap_m}. Check the road coverage and entrances")
        return [(node_ids[int(idx)], float(off)) for idx, off in zip(indices, offsets)]

    snapped_origins = snap(origin_points, unit_ids, "unit")
    destination_points = [point for pid in park_ids for point in park_points[pid]]
    destination_ids = [pid for pid in park_ids for _ in park_points[pid]]
    snapped_destinations = snap(destination_points, destination_ids, "park")
    grouped_destinations = defaultdict(dict)
    for pid, (node, offset) in zip(destination_ids, snapped_destinations):
        current = grouped_destinations[pid].get(node, np.inf)
        grouped_destinations[pid][node] = min(current, offset)

    # Group unit rows by snapped node: one routing search per park entrance,
    # not one Dijkstra search per grid cell (important for city-scale grids).
    origin_by_node = defaultdict(list)
    for i, (node, offset) in enumerate(snapped_origins):
        origin_by_node[node].append((i, offset))
    backwards = graph.reverse(copy=False) if graph.is_directed() else graph
    cutoff_m = None if max_distance_km is None else max_distance_km * 1000
    rows = []
    for park_j, pid in enumerate(park_ids):
        best_by_unit = {}
        for entrance_node, entrance_offset in grouped_destinations[pid].items():
            search_cutoff = None if cutoff_m is None else max(0.0, cutoff_m - entrance_offset)
            shortest = nx.single_source_dijkstra_path_length(
                backwards, entrance_node, cutoff=search_cutoff, weight="length"
            )
            for node, distance in shortest.items():
                for i, origin_offset in origin_by_node.get(node, ()):
                    total = origin_offset + distance + entrance_offset
                    if cutoff_m is not None and total > cutoff_m:
                        continue
                    if total < best_by_unit.get(i, np.inf):
                        best_by_unit[i] = total
        for i, meters in best_by_unit.items():
            rows.append((i, park_j, meters / 1000))

    rows.sort(key=lambda item: (item[0], item[1]))
    return pd.DataFrame(
        [(unit_ids[i], park_ids[j], d) for i, j, d in rows],
        columns=["unit_id", "park_id", "network_distance_km"],
    )


def download_osm_walking_network(units, parks, *, buffer_km: float = 8.0):
    """Download OSM pedestrian routing network covering input geometries + buffer.

    Requires OSMnx >=2 and an internet connection to the Overpass API. This can
    be expensive or rate-limited over large cities; for Beijing-wide studies,
    use a pre-downloaded network GraphML and ``build_network_distances``.
    """
    try:
        import osmnx as ox
    except ImportError as exc:
        raise ImportError('OSM downloading requires pip install -e ".[osm]"') from exc
    gpd, *_ = _gis_dependencies()
    _required_geometry(units, "unit_id", "units", gpd)
    _required_geometry(parks, "park_id", "parks", gpd)
    if not np.isfinite(buffer_km) or buffer_km <= 0:
        raise ValueError("buffer_km must be positive and finite")
    combined = pd.concat([
        units[["geometry"]].to_crs("EPSG:4326"),
        parks[["geometry"]].to_crs("EPSG:4326")
    ], ignore_index=True)
    coverage = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")
    metric_crs = coverage.estimate_utm_crs()
    if metric_crs is None:
        raise ValueError("Cannot infer local projected CRS for study area")
    bounds = coverage.to_crs(metric_crs).total_bounds
    west, south, east, north = bounds + np.array([-1, -1, 1, 1]) * buffer_km * 1000
    from shapely.geometry import box
    bbox_poly = gpd.GeoSeries([box(west, south, east, north)], crs=metric_crs)
    west, south, east, north = bbox_poly.to_crs("EPSG:4326").total_bounds
    ox.settings.use_cache = True
    graph = ox.graph.graph_from_bbox((west, south, east, north), network_type="walk",
                                     retain_all=True, truncate_by_edge=True)
    return ox.projection.project_graph(graph)


def calculate_from_geodata(
    units,
    parks,
    *,
    graph=None,
    entrances=None,
    origins=None,
    population_column="population",
    thresholds="beijing2019_elderly",
    max_snap_m=1000,
    osm_buffer_km=None,
):
    """Calculate accessibility directly from GIS units, parks, and a road graph.

    If graph is None, download walking network from OSM. Returns
    (AccessibilityResults, long_form_network_distances). The maximum cutoff
    across supplied parks limits the routing search and output rows.
    """
    from .model import calculate_accessibility
    from .thresholds import resolve_thresholds
    cutoffs = resolve_thresholds(parks, thresholds)
    if graph is None:
        if osm_buffer_km is None:
            osm_buffer_km = float(np.max(cutoffs)) + 2.0
        graph = download_osm_walking_network(units, parks, buffer_km=osm_buffer_km)
    distances = build_network_distances(
        units, parks, graph, origins=origins, entrances=entrances,
        max_distance_km=float(np.max(cutoffs)), max_snap_m=max_snap_m,
    )
    return (calculate_accessibility(units, parks, distances,
                                    population_column=population_column,
                                    thresholds=thresholds), distances)