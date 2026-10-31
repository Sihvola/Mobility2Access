import numpy as np
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, box
import pytest

from mobility2access import build_network_distances, calculate_from_geodata

CRS = "EPSG:32650"
X, Y = 400000, 4400000


def network(directed=True):
    graph = nx.MultiDiGraph(crs=CRS) if directed else nx.MultiGraph(crs=CRS)
    graph.add_node("A", x=X, y=Y)
    graph.add_node("B", x=X+1000, y=Y)
    graph.add_node("C", x=X+1000, y=Y+1000)
    graph.add_node("D", x=X+2000, y=Y+1000)
    graph.add_edge("A", "B", length=1000)
    graph.add_edge("B", "C", length=1000)
    graph.add_edge("C", "D", length=1000)
    if directed:
        graph.add_edge("B", "A", length=1000)
        graph.add_edge("C", "B", length=1000)
        graph.add_edge("D", "C", length=1000)
    return graph


def input_gdf():
    units = gpd.GeoDataFrame(
        {"unit_id": ["uA", "uB"], "pop": [100, 150]},
        geometry=[box(X-10, Y-10, X+10, Y+10),
                  box(X+990, Y+990, X+1010, Y+1010)], crs=CRS,
    )
    parks = gpd.GeoDataFrame({"park_id": ["pC"], "park_area_ha": [10]},
        geometry=[box(X+990, Y+990, X+1010, Y+1010)], crs=CRS)
    return units, parks


def test_network_not_euclidean_and_model_integration():
    units, parks = input_gdf()
    entrances = gpd.GeoDataFrame({"park_id":["pC"]}, geometry=[Point(X+1000,Y+1000)], crs=CRS)
    d = build_network_distances(units, parks, network(), entrances=entrances)
    assert d.unit_id.tolist() == ["uA", "uB"]
    np.testing.assert_allclose(d.network_distance_km, [2,0])
    # A-to-C straight line is sqrt(2) km but path length is 2 km.
    result, auto = calculate_from_geodata(units, parks, graph=network(), entrances=entrances,
       population_column="pop", thresholds=3.0)
    assert isinstance(result.units, gpd.GeoDataFrame)
    assert (result.units.accessibility_m2_per_person > 0).all()
    np.testing.assert_allclose(auto.network_distance_km, d.network_distance_km)


def test_multiple_entrances_uses_shorter_path():
    units, parks = input_gdf()
    entrances = gpd.GeoDataFrame({"park_id": ["pC", "pC"]},
       geometry=[Point(X+1000,Y+1000), Point(X,Y)], crs=CRS)
    od = build_network_distances(units, parks, network(), entrances=entrances)
    np.testing.assert_allclose(od.network_distance_km, [0,0])


def test_directed_network_reverses_search_correctly():
    units, parks = input_gdf()
    # One-way C->B->A only, so uA cannot reach the park at C.
    G = nx.DiGraph(crs=CRS)
    G.add_node("A",x=X,y=Y)
    G.add_node("B",x=X+1000,y=Y)
    G.add_node("C",x=X+1000,y=Y+1000)
    G.add_edge("C","B",length=1000)
    G.add_edge("B","A",length=1000)
    ent=gpd.GeoDataFrame({"park_id":["pC"]},geometry=[Point(X+1000,Y+1000)],crs=CRS)
    od=build_network_distances(units,parks,G,entrances=ent)
    assert od.unit_id.tolist()==["uB"]
    assert od.network_distance_km.iloc[0]==0


def test_cutoff_excludes_unreachable_without_zeros():
    units, parks = input_gdf()
    ent=gpd.GeoDataFrame({"park_id":["pC"]},geometry=[Point(X+1000,Y+1000)],crs=CRS)
    od=build_network_distances(units,parks,network(),entrances=ent,max_distance_km=1.0)
    assert od.unit_id.tolist()==["uB"]


def test_polygon_fallback_boundary_reaches_road():
    units, parks = input_gdf()
    od = build_network_distances(units, parks, network(), max_snap_m=100)
    assert set(od.unit_id) == {"uA", "uB"}
    assert od.network_distance_km.min() < 0.1


def test_explicit_origins_override_representative_points():
    units, parks = input_gdf()
    origins=gpd.GeoDataFrame({"unit_id":["uB","uA"]},
       geometry=[Point(X,Y),Point(X,Y)],crs=CRS)
    ent=gpd.GeoDataFrame({"park_id":["pC"]},geometry=[Point(X+1000,Y+1000)],crs=CRS)
    od=build_network_distances(units,parks,network(),origins=origins,entrances=ent)
    np.testing.assert_allclose(od.network_distance_km, [2,2])


def test_connector_offsets_and_snap_safety():
    units, parks=input_gdf()
    origins=gpd.GeoDataFrame({"unit_id":["uA","uB"]},
        geometry=[Point(X+100,Y),Point(X+1000,Y+1000)],crs=CRS)
    ent=gpd.GeoDataFrame({"park_id":["pC"]},geometry=[Point(X+1000,Y+1000)],crs=CRS)
    d=build_network_distances(units, parks, network(), origins=origins, entrances=ent)
    np.testing.assert_allclose(d.network_distance_km,[2.1,0])
    with pytest.raises(ValueError,match="max_snap_m"):
        build_network_distances(units, parks, network(), origins=origins, entrances=ent, max_snap_m=50)


def test_geographic_crs_graph_rejected():
    units, parks=input_gdf()
    G=network()
    G.graph['crs']='EPSG:4326'
    with pytest.raises(ValueError,match="projected"):
        build_network_distances(units, parks, G)


def test_missing_length_rejected():
    units, parks=input_gdf()
    G=network()
    for *_, data in G.edges(data=True):
        data.pop('length', None)
        break
    with pytest.raises(ValueError,match="length"):
        build_network_distances(units, parks, G)


def test_mixed_crs_transforms_coordinates():
    units,parks=input_gdf()
    ent=gpd.GeoDataFrame({'park_id':['pC']}, geometry=[Point(X+1000,Y+1000)],crs=CRS)
    d=build_network_distances(units.to_crs(4326),parks.to_crs(4326),network(),entrances=ent.to_crs(4326))
    np.testing.assert_allclose(d.network_distance_km, [2,0], atol=1e-7)