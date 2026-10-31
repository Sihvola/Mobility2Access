# Mobility2Access

**Behavior-informed spatial accessibility and equity analysis in Python.**

Mobility2Access implements a Gaussian two-step floating catchment area (2SFCA) model with configurable service-distance thresholds, including age- and park-size-informed empirical thresholds from:

> Guo, S., Song, C., Pei, T., et al. (2019). Accessibility to urban parks for elderly residents: Perspectives from mobile phone data. *Landscape and Urban Planning*, **191**, 103642. https://doi.org/10.1016/j.landurbplan.2019.103642

[中文说明](README.zh-CN.md)

## Why this tool?

The classical Gaussian 2SFCA calculation and Gini index are established methods. The distinctive research idea behind this package is to **calibrate park catchment distances from observed visits**, accounting for age-related mobility and the attraction of different park sizes. The package also supports other populations and study units.

The study reported historical Beijing values for park visits by older adults (>=60): **5.3021 km** (small, 2–20 ha), **6.9710 km** (medium, 20–100 ha), and **7.8076 km** (large, >100 ha). Boundary handling in this software assigns 20 ha to medium. These are **empirical Beijing estimates, not universal standards**.

## Install

```bash
pip install -e ".[test]"
pytest -q
python examples/run_demo.py
```

For GeoJSON and GeoPackage input/output: `pip install -e ".[gis,test]"`.

## Python API

```python
import pandas as pd
from mobility2access import calculate_accessibility

units = pd.read_csv("data/synthetic/grids.csv")
parks = pd.read_csv("data/synthetic/parks.csv")
od = pd.read_csv("data/synthetic/grid_road_distances.csv")

result = calculate_accessibility(
    units, parks, od,
    population_column="elderly_population",
    thresholds="beijing2019_elderly",
)
print(result.units[["unit_id", "accessibility_m2_per_person"]])
print(result.parks[["park_id", "catchment_km"]])
print(result.gini)
```

### Required data

- **Units**: `unit_id`, selected population column; optional geometry and metadata. Units can be grids or streets.
- **Parks**: `park_id`, `park_area_ha`; optionally `threshold_km`.
- **Distances (long OD table)**: `unit_id`, `park_id`, `network_distance_km`. Distances must match the chosen unit scale. Missing pairs mean unreachable.
- **Thresholds**: `"beijing2019_elderly"`, a positive number in km, a `{"small": ..., "medium": ..., "large": ...}` mapping, or `"park_column"`.

The software **does not currently generate road-network distances from geometries**. Calculate them separately before calling the model.

## Command-line example

```bash
mobility2access \
  --units data/synthetic/grids.csv \
  --parks data/synthetic/parks.csv \
  --distances data/synthetic/grid_road_distances.csv \
  --population-column elderly_population \
  --thresholds beijing2019_elderly \
  --output outputs/grid_accessibility.csv
```

Outputs include unit accessibility (m²/person), park-level supply-to-demand diagnostics, population-weighted Lorenz data, and Gini.

## Calibrate thresholds from preprocessed park visits

```python
from mobility2access import calibrate_thresholds
visits = pd.read_csv("data/synthetic/sample_park_visits.csv")
print(calibrate_thresholds(visits, quantile=0.75))
```

Each row must be an already-identified park visit with `age_group`, `park_area_ha`, and `network_distance_km`. The package does **not** process raw mobile-phone signaling trajectories or contain personal mobility data.

## Reproducibility and scope

- This is a **Python reconstruction of the core method**, not a verified numeric reproduction of every result reported in the original Beijing study.
- Provided data are **synthetic** and should never be interpreted as observed visits or access in Beijing.
- Gini is calculated using population-weighted individual accessibility; compare definitions carefully when reproducing published estimates.
- Empty-demand park catchments are flagged and assigned a zero supply-to-demand ratio.
- There is **no software license yet**. Do not assume that public visibility would grant reuse rights.

See [Method](docs/METHOD.md) and [Data format](docs/DATA_FORMAT.md).

## Citation

Please cite the original Guo et al. (2019) paper when using the research method. Software citation metadata can be added once attribution and licensing have been reviewed.
