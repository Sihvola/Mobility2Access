# Data format

All three model tables can be CSV or pandas DataFrames. Study units may also be GeoDataFrames for spatial outputs.

## Units

Required: `unit_id` and a user-chosen population count column (e.g. `elderly_population`). Optional columns and geometry are retained. IDs must be non-null and unique; population counts must be finite and nonnegative; total population must be positive. Grid, neighborhood, street and other unit types are supported as long as distances match their scale.

## Parks

Required: `park_id` and `park_area_ha`. Positive, finite area (ha). Optional `threshold_km` for `thresholds="park_column"`. Historical Beijing older-adult threshold profile requires parks >2 ha.

## OD network distance

Required: `unit_id`, `park_id`, `network_distance_km`, with one row per unit/park pair. Distances in km, nonnegative; use +infinity for unreachable pairs or omit them. Negative or NaN distances are invalid. IDs must reference input units and parks.

## Threshold input

- `"beijing2019_elderly"`: 5.3021 / 6.9710 / 7.8076 km by park size.
- `5.0`: uniform 5 km radius.
- `{"small": 4.5, "medium": 6.0, "large": 9.0}`: custom per-size cutoffs.
- `"park_column"`: one park-specific value per row of parks, in `threshold_km`.

## Output

`AccessibilityResults.units`: original units, plus `accessibility_m2_per_person`.

`AccessibilityResults.parks`: original park fields, `catchment_km`, `weighted_demand_population`, `park_supply_ratio_m2_per_person`, `no_demand_in_catchment`.

`AccessibilityResults.gini`: weighted Gini; `AccessibilityResults.lorenz`: cumulative population and access shares.

For geometry-containing inputs, install geopandas via `pip install -e ".[gis]"` and save outputs as GeoJSON or GeoPackage. This tool does not derive OD distance from geometry.

## Synthetic fixtures

See `data/synthetic` for small, synthetic grid/street tables and visits. They do not contain actual phone signaling records.
