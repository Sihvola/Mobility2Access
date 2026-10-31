"""Command-line entry point: python -m mobility2access or mobility2access."""
import argparse
from pathlib import Path
from .io import load_table, save_table
from .model import calculate_accessibility

def main(argv=None):
    p = argparse.ArgumentParser(description="Gaussian 2SFCA using study units, population, parks and road distances")
    p.add_argument("--units", required=True, help="CSV, GeoJSON, or GPKG with unit_id & population")
    p.add_argument("--parks", required=True, help="CSV with park_id & park_area_ha")
    p.add_argument("--distances", required=True, help="CSV with unit_id, park_id, network_distance_km")
    p.add_argument("--population-column", default="population", help="Column for target population count")
    p.add_argument("--thresholds", required=True, help="'beijing2019_elderly', 'park_column', or numeric cutoff (km)")
    p.add_argument("--output", required=True, help="Output CSV/GeoJSON/GPKG")
    args = p.parse_args(argv)
    choice = args.thresholds
    if choice not in {"beijing2019_elderly", "park_column"}:
        try:
            choice = float(choice)
        except ValueError:
            p.error("--thresholds must be a profile, 'park_column', or a number (km)")
    result = calculate_accessibility(
        load_table(args.units), load_table(args.parks), load_table(args.distances),
        population_column=args.population_column, thresholds=choice,
    )
    output = Path(args.output)
    save_table(result.units, output)
    park_out = output.with_name(output.stem + "_park_diagnostics.csv")
    lorenz_out = output.with_name(output.stem + "_lorenz.csv")
    save_table(result.parks, park_out)
    result.lorenz.to_csv(lorenz_out, index=False)
    print(f"Saved {len(result.units)} unit results to {output}")
    print(f"Park diagnostics: {park_out}")
    print(f"Lorenz data: {lorenz_out}")
    print(f"Population-weighted Gini: {result.gini:.4f}")
    n = int(result.parks["no_demand_in_catchment"].sum())
    if n:
        print(f"Warning: {n} parks had zero weighted demand (see diagnostics)")

if __name__ == "__main__":
    main()
