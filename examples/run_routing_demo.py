"""Offline demo with a tiny synthetic footpath network (no OSM download)."""
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, box
from mobility2access import calculate_from_geodata

crs = "EPSG:32650"  # Projected in meters; coordinates are synthetic
x, y = 400000, 4400000
G = nx.MultiDiGraph(crs=crs)
for j in range(3):
    for i in range(3):
        n = f"{i}-{j}"
        G.add_node(n, x=x + i * 1000, y=y + j * 1000)
for j in range(3):
    for i in range(3):
        for di, dj in [(1, 0), (0, 1)]:
            if i + di < 3 and j + dj < 3:
                a, b = f"{i}-{j}", f"{i+di}-{j+dj}"
                G.add_edge(a, b, length=1000)
                G.add_edge(b, a, length=1000)
units = gpd.GeoDataFrame({
    "unit_id": ["G1", "G2", "G3"],
    "elderly_population": [100, 200, 150],
}, geometry=[box(x-50, y-50, x+50, y+50),
             box(x+950, y+950, x+1050, y+1050),
             box(x+1950, y-50, x+2050, y+50)], crs=crs)
parks = gpd.GeoDataFrame({"park_id": ["P1", "P2"], "park_area_ha": [10, 40]},
    geometry=[box(x+1950, y+1950, x+2050, y+2050),
              box(x-50, y+1950, x+50, y+2050)], crs=crs)
entrances = gpd.GeoDataFrame({"park_id": ["P1", "P2"]},
    geometry=[Point(x+2000, y+2000), Point(x, y+2000)], crs=crs)
result, od = calculate_from_geodata(
    units, parks, graph=G, entrances=entrances,
    population_column="elderly_population", thresholds="beijing2019_elderly",
)
print("Synthetic walking network OD (km):\n", od.to_string(index=False))
print("\nAccessibility (m²/person):\n", result.units[["unit_id", "accessibility_m2_per_person"]].to_string(index=False))
print("\nPopulation-weighted Gini:", round(result.gini, 4))