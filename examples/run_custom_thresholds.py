"""Alternative threshold setups: constant / custom park classes / per park."""
from pathlib import Path
import pandas as pd
from mobility2access import calculate_accessibility

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
units = pd.read_csv(DATA / "grids.csv")
parks = pd.read_csv(DATA / "parks.csv")
distances = pd.read_csv(DATA / "grid_road_distances.csv")

for label, thresholds in {
    "common 5km": 5.0,
    "user class-specific": {"small": 4.5, "medium": 6.0, "large": 9.0},
}.items():
    res = calculate_accessibility(units, parks, distances,
        population_column="elderly_population", thresholds=thresholds)
    print(label, "Gini", round(res.gini, 3))

parks["threshold_km"] = [4.5, 6.0, 9.0]
res = calculate_accessibility(units, parks, distances,
    population_column="elderly_population", thresholds="park_column")
print("Park-specific values", res.parks["catchment_km"].tolist())
