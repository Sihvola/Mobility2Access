"""Run: python examples/run_demo.py (after pip install -e .)."""
from pathlib import Path
import pandas as pd
from mobility2access import calculate_accessibility, calibrate_thresholds

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
parks = pd.read_csv(DATA / "parks.csv")

for scale, units_filename, dist_filename in [
    ("Grid", "grids.csv", "grid_road_distances.csv"),
    ("Street", "streets.csv", "street_road_distances.csv"),
]:
    units = pd.read_csv(DATA / units_filename)
    distances = pd.read_csv(DATA / dist_filename)
    result = calculate_accessibility(
        units, parks, distances,
        population_column="elderly_population",
        thresholds="beijing2019_elderly",
    )
    print(f"\n{scale} example (ALL input data synthetic):")
    print(result.units[["unit_id", "accessibility_m2_per_person"]].to_string(index=False))
    print(f"Gini = {result.gini:.4f}")
    print("Catchment thresholds:", result.parks["catchment_km"].round(4).tolist())

print("\nOptional recalibration using SYNTHETIC park visits:")
print(calibrate_thresholds(pd.read_csv(DATA / "sample_park_visits.csv")).to_string(index=False))
