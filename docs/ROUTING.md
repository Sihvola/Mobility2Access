# Road-network distance calculation (v0.2)

## What is computed?

The algorithm takes spatial **study units** (grids/streets), **parks**, a pedestrian **road graph**, and optionally park **entrance points** and population-weighted **residential origin points**. It outputs `unit_id,park_id,network_distance_km`, compatible with the original Gaussian 2SFCA model. Route length follows graph edges, not straight-line distances.

## Required inputs

| Input | Geometry | Required fields | Notes |
| --- | --- | --- | --- |
| Units | Polygon or Point | `unit_id`, population field | One row per output unit; representative point is used by default. |
| Parks | Polygon or Point | `park_id`, `park_area_ha` | Area input is in hectares; polygons allow fallback to boundary. |
| Entrances (optional, recommended) | Point | `park_id` | Multiple park entries allowed; minimum walking distance to **any** entrance. |
| Origins (optional) | Point | `unit_id` | Exactly one per unit; supports population-weighted origins or real residential locations. |
| Graph | Projected NetworkX/OSMnx graph | Node `x,y`; edge `length` (meters); graph `crs` | Use a **projected metric CRS**, e.g. local UTM. Edges can be directed. |

All spatial inputs need defined CRS and are reprojected to the graph CRS. Distances are based on road-graph lengths in **meters** and output in **kilometers**. Units with no accessible park get no OD rows (never an invented zero distance). Long-form output avoids large dense n×m matrices.

### Snapping and approximations

1. A unit polygon is represented by one point. Use `origins` to improve fidelity where population is unevenly distributed across streets or large polygons.
2. Park entrance points are **strongly preferred**: by default, park Point geometry is used or a park polygon boundary point closest to any graph node serves as a *proxy* for a real entrance. It does **not** identify legal park entrances, gates or connectivity inside a park.
3. Each point snaps to its nearest graph node; the off-network connection is approximated by Euclidean meters. This connection is **not guaranteed to be a walkable path**. `max_snap_m=1000` by default raises an error if the nearest road is farther away. Choose a smaller threshold for dense urban road networks.
4. A walking network downloaded from OpenStreetMap may omit informal paths, indoor routes, temporary restrictions or restricted park gates. OSMnx walking roads should be inspected before published results.
5. Reverse shortest-path searches honor **edge direction**. Routing complexity scales primarily with the number of park entries, not the number of residential units.
6. `max_distance_km` can cap the OD extraction. The high-level wrapper automatically uses the largest distance cutoff in `thresholds`; pairs outside each individual park cutoff are subsequently filtered by the 2SFCA model.

## From a prepared road graph (offline)

```python
from mobility2access import build_network_distances, calculate_accessibility
import geopandas as gpd
import osmnx as ox

units = gpd.read_file("units.gpkg")
parks = gpd.read_file("parks.gpkg")
entrances = gpd.read_file("entrances.gpkg")
graph = ox.io.load_graphml("projected_walking.graphml")

distances = build_network_distances(
    units, parks, graph, entrances=entrances, max_distance_km=8.0
)
distances.to_csv("network_distances.csv", index=False)
result = calculate_accessibility(
    units, parks, distances,
    population_column="elderly_population",
    thresholds="beijing2019_elderly",
)
```

For a single-call interface use `result, distances = calculate_from_geodata(units, parks, graph=graph, entrances=entrances, population_column="elderly_population", thresholds="beijing2019_elderly")`.

## Downloading OSM roads (online)

```python
from mobility2access import calculate_from_geodata
result, distances = calculate_from_geodata(
    units, parks, entrances=entrances,
    population_column="elderly_population",
    thresholds="beijing2019_elderly",
    graph=None,  # download OSMnx pedestrian road network
)
```

The download area is the geometry extent + buffer. By default, the buffer is the largest park threshold plus 2 km; use `osm_buffer_km` to override. OSMnx obtains data from the public Overpass service. **Large-city queries may time out or be rate-limited**; use a prepared city-wide road graph instead for full Beijing studies. No live OSM data are bundled or required for offline tests.

## CLI (online example)

```bash
pip install -e ".[osm,test]"
mobility2access-route \
  --units data/synthetic/grids.geojson \
  --parks data/synthetic/parks.geojson \
  --entrances data/synthetic/park_entrances.geojson \
  --download-osm \
  --population-column elderly_population \
  --thresholds beijing2019_elderly \
  --od-output outputs/od.csv \
  --output outputs/grid_access.geojson
```

Swap `--download-osm` for `--graphml walking.graphml` to reuse a saved projected graph. Outputs are generated under the requested paths, with accompanying park diagnostics and Lorenz CSVs.

## Validation and reproducibility

The test suite covers exact distances on a known synthetic network, directed one-way paths, entrance choices, missing/unreachable pairs, cutoff filtering, coordinate reprojection, polygon fallback and snapping safety. Use `python examples/run_routing_demo.py` for the offline example. **These tests are not a validation against historical Beijing mobility records or actual OpenStreetMap routes.** For scientific use, independently verify OD distances with known routes and check the origin and entrance placement strategy.