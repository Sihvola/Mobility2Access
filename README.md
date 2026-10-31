# Mobility2Access

**Behavior-informed park accessibility: park-size-dependent Gaussian 2SFCA with interchangeable study units.**

This is a **runnable Python research-code reconstruction** of the core accessibility workflow in:

> Guo, S., Song, C., Pei, T., et al. (2019). *Accessibility to urban parks for elderly residents: Perspectives from mobile phone data*. Landscape and Urban Planning, 191, 103642. https://doi.org/10.1016/j.landurbplan.2019.103642

The original contribution is to **estimate distance catchments from observed home-to-park trips**, accounting for **population age and park size**, and then use those limits in the established Gaussian 2SFCA model. The Gini and Lorenz analyses characterize unequal access; these are established measures, not novel algorithms. This repository is not yet a validation against the original Beijing input data.

[中文说明 / Chinese guide](README.zh-CN.md) · [Scientific method](docs/METHOD.md) · [Input formats](docs/DATA_FORMAT.md)

## Core inputs: just four datasets / choices

1. **Study units** (`unit_id`, chosen `population` count; optional boundaries) — grid, street/subdistrict, neighborhood or another scale.
2. **Parks** (`park_id`, `park_area_ha`) — park supply.
3. **Shortest road-network distances** (`unit_id`, `park_id`, `network_distance_km`) — origin-to-park distance table for the selected study units.
4. **Catchment distance threshold** — a Beijing 2019 size-dependent empirical profile, one common cutoff, custom size categories or park-specific values.

The **park area and road distance data are mathematically essential** even though users chiefly change the study-unit boundaries, population and thresholds. Raw phone data is **not** required when thresholds have already been estimated.

## Install + run

```bash
python -m pip install -e ".[test]"
python examples/run_demo.py
pytest -q
```

Run a user-ready CLI example with **completely synthetic data**:

```bash
mobility2access \
  --units data/synthetic/grids.csv \
  --parks data/synthetic/parks.csv \
  --distances data/synthetic/grid_road_distances.csv \
  --population-column elderly_population \
  --thresholds beijing2019_elderly \
  --output outputs/grid_access.csv
```

Use streets/subdistricts instead of grid cells (replace **both** unit population and corresponding unit-to-park road distances):

```bash
mobility2access \
  --units data/synthetic/streets.csv \
  --parks data/synthetic/parks.csv \
  --distances data/synthetic/street_road_distances.csv \
  --population-column elderly_population \
  --thresholds beijing2019_elderly \
  --output outputs/street_access.csv
```

To use boundary polygons and produce a spatial GeoPackage or GeoJSON, install `pip install -e ".[gis]"` and replace `--units` with `grids.geojson` or `streets.geojson` and `--output` with `outputs/accessibility.gpkg` or `outputs/accessibility.geojson`.

## Python API

```python
import pandas as pd
from mobility2access import calculate_accessibility

units = pd.read_csv("data/synthetic/grids.csv")
parks = pd.read_csv("data/synthetic/parks.csv")
network_distances = pd.read_csv("data/synthetic/grid_road_distances.csv")

result = calculate_accessibility(
    units, parks, network_distances,
    population_column="elderly_population",
    thresholds="beijing2019_elderly",
)
print(result.units[["unit_id", "accessibility_m2_per_person"]])
print("Gini:", result.gini)
```

Change the threshold with a single argument:

```python
thresholds=5.0  # fixed 5 km for all parks
thresholds={"small": 4.0, "medium": 6.0, "large": 8.0}
thresholds="park_column"  # add `threshold_km` to every park row
```

For other age groups, cities or years, **calibrate new thresholds** or provide your own values. The Beijing preset is a historical empirical parameter for adults aged >=60, not an age-neutral standard.

## Historical Beijing elder thresholds (km)

| Park size | Park area (ha) | 75th percentile distance (km) |
|---|---|---:|
| Small | 2–20 | 5.3021 |
| Medium | 20–100 | 6.9710 |
| Large | >100 | 7.8076 |

These figures come from Figure 2 of the supplied article explanation. Code assigns the boundary 20ha to medium; historical preset requires parks **over 2ha**. Check your new data's eligibility and calibration before applying them.

## What the model outputs

For each input unit: `accessibility_m2_per_person` (m² park area per member of the selected population group). Park diagnostics include the actual cutoff, weighted demand and per-park supply ratio. It also returns population-weighted Gini and Lorenz curve values.

The computational kernel handles **long-form OD edges**, rather than allocating a potentially enormous `number of units × number of parks` dense distance/weight matrix. It still requires a correct externally prepared road-network distance table.

## Transparency / scientific limitations

- **No raw mobile subscriber data are included.** Demo populations, GIS polygons, parks, visits and road distance values are all synthetic.
- The project does not yet infer homes, parks visited, or trajectories from phone location timeseries; `calibrate_thresholds()` works on derived visit distances.
- The main method is reconstructed using the supplied MATLAB algorithm, article description and author clarification. It is not certified to reproduce published maps or numerical summaries without original inputs.
- Population-weighted Gini convention is stated in [docs/METHOD.md](docs/METHOD.md); it may differ from the published figure's exact calculation protocol.
- The **source code is available under BSD-3-Clause** (see [LICENSE](LICENSE)). The research article and third-party datasets have their own separate copyright and licensing terms.

## License, citation and OpenStreetMap attribution

**Software license.** Mobility2Access source code is released under the [BSD 3-Clause License](LICENSE) (Copyright © 2026 Sihui Guo and Mobility2Access contributors). This software license covers the repository's original code; it does **not** relicense the 2019 journal article or third-party datasets.

**Citing this work.** GitHub's **Cite this repository** feature uses [CITATION.cff](CITATION.cff) to generate a software citation for **Mobility2Access v0.2.0**. When publishing results based on the behavior-informed threshold method, **also cite the original research article**:

> Guo, S., Song, C., Pei, T., et al. (2019). Accessibility to urban parks for elderly residents: Perspectives from mobile phone data. *Landscape and Urban Planning*, 191, 103642. https://doi.org/10.1016/j.landurbplan.2019.103642

The software currently has **no separately registered DOI or official GitHub Release**; do not use the paper DOI as a software DOI.

**OpenStreetMap and third-party data.** The optional OSMnx workflow downloads and uses data from **© OpenStreetMap contributors**, available under the [Open Database License (ODbL)](https://www.openstreetmap.org/copyright). When distributing OSM-derived geographic datasets, maps or other produced works, comply with the ODbL and [OSM attribution guidance](https://osmfoundation.org/wiki/Attribution_Guidelines), including the required credit and any applicable share-alike obligations. The BSD-3-Clause license of *this code* does not replace ODbL for OSM data. The bundled demo files are **synthetic** and do not contain a downloaded OSM network.

## Recommended next checks

Validate source routes and park entrances; check whether denominators should use total residents or target-group residents; benchmark accessible outputs against selected published numbers if data become available; confirm the original visits' 75% quantile protocol and 20ha boundary convention.

## v0.2: Automatic walking-network distances from GIS inputs

The new `mobility2access.routing` module converts **GeoDataFrames of grid/street units and parks** into the long-form road-distance table, then feeds it to Gaussian 2SFCA. Routing is based on an actual *network* rather than straight-line distance. You can reuse your own OSMnx/NetworkX graph offline or download a pedestrian graph using OSMnx and the Overpass API.

### Install

```bash
pip install -e ".[routing,test]"        # offline routing with your own graph
pip install -e ".[osm,test]"            # also supports OpenStreetMap download and GraphML
python examples/run_routing_demo.py      # tiny offline graph; no network connection
pytest -q
```

### One-step Python workflow

```python
import geopandas as gpd
from mobility2access import calculate_from_geodata

units = gpd.read_file("data/synthetic/grids.geojson")
parks = gpd.read_file("data/synthetic/parks.geojson")
entrances = gpd.read_file("data/synthetic/park_entrances.geojson")

# With graph=None, the package obtains an OSM *walking* graph online.
# Or provide graph=your_projected_osmnx_graph to work entirely offline.
result, distances = calculate_from_geodata(
    units, parks,
    entrances=entrances,
    population_column="elderly_population",
    thresholds="beijing2019_elderly",
)
distances.to_csv("network_distances.csv", index=False)
result.units.to_file("accessibility.geojson", driver="GeoJSON")
```

### Command line (no Python code needed)

```bash
# Requires network access and the [osm] extra:
mobility2access-route \
  --units data/synthetic/grids.geojson \
  --parks data/synthetic/parks.geojson \
  --entrances data/synthetic/park_entrances.geojson \
  --download-osm \
  --population-column elderly_population \
  --thresholds beijing2019_elderly \
  --od-output outputs/od.csv \
  --output outputs/accessibility.geojson

# Or replace --download-osm with --graphml /path/to/projected-walking.graphml.
```

**Method details and important limitations:** [Road network workflow](docs/ROUTING.md). The included GIS layers are **synthetic, not actual Beijing park locations**. Downloading OSM data depends on Overpass availability and can be expensive or fail for large Beijing-wide areas. For city-scale work, prepare and reuse an appropriately projected, sufficiently buffered pedestrian network. Entrance points are strongly recommended; without them polygon boundaries are approximated by the nearest network node. Connector distances between geometries and snapped nodes are straight lines and not guaranteed walkable. No real OSM network download is executed by the CI tests.