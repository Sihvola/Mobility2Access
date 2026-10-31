"""CLI to run GIS -> road-network OD -> Gaussian 2SFCA."""
import argparse
from pathlib import Path
from .io import load_table, save_table
from .routing import build_network_distances, calculate_from_geodata, download_osm_walking_network


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Calculate walking road-network distances and Gaussian 2SFCA from GIS files"
    )
    parser.add_argument("--units", required=True, help="GeoJSON/GPKG of grids or streets with population")
    parser.add_argument("--parks", required=True, help="GeoJSON/GPKG parks with park_area_ha")
    parser.add_argument("--origins", help="Optional points with unit_id for unit residential origins")
    parser.add_argument("--entrances", help="Optional Point GeoJSON/GPKG with park_id; multiple per park")
    network = parser.add_mutually_exclusive_group(required=True)
    network.add_argument("--graphml", help="Prepared, projected OSMnx walking network GraphML")
    network.add_argument("--download-osm", action="store_true", help="Download OSM walking network via Overpass API")
    parser.add_argument("--thresholds", default="beijing2019_elderly",
                        help="Beijing empirical profile, park_column, or a single distance in km")
    parser.add_argument("--population-column", default="population")
    parser.add_argument("--max-snap-m", type=float, default=1000.0)
    parser.add_argument("--osm-buffer-km", type=float, help="OSM bbox buffer, kilometers")
    parser.add_argument("--output", required=True, help="Accessibility output (.geojson, .gpkg, or .csv)")
    parser.add_argument("--od-output", required=True, help="Network OD output (.csv)")
    args = parser.parse_args(argv)
    try:
        import osmnx as ox
    except ImportError:
        if args.graphml:
            parser.error('GraphML loading requires pip install -e ".[osm]"')
        ox = None
    choice = args.thresholds
    if choice not in {"beijing2019_elderly", "park_column"}:
        try:
            choice = float(choice)
        except ValueError:
            parser.error("--thresholds must be beijing2019_elderly, park_column, or a number in km")
    units = load_table(args.units)
    parks = load_table(args.parks)
    entrances = load_table(args.entrances) if args.entrances else None
    origins = load_table(args.origins) if args.origins else None
    graph = ox.io.load_graphml(args.graphml) if args.graphml else None
    result, od = calculate_from_geodata(
        units, parks, graph=graph, entrances=entrances, origins=origins,
        population_column=args.population_column, thresholds=choice,
        max_snap_m=args.max_snap_m, osm_buffer_km=args.osm_buffer_km,
    )
    od_path = Path(args.od_output)
    od_path.parent.mkdir(parents=True, exist_ok=True)
    od.to_csv(od_path, index=False)
    output_path = Path(args.output)
    save_table(result.units, output_path)
    save_table(result.parks, output_path.with_name(output_path.stem + "_parks.csv"))
    save_table(result.lorenz, output_path.with_name(output_path.stem + "_lorenz.csv"))
    print(f"Wrote {len(od):,} network-distance pairs: {od_path}")
    print(f"Wrote {len(result.units):,} unit accessibility results: {output_path}")
    print(f"Population-weighted Gini: {result.gini:.4f}")
    print(f"Parks with no reachable demand: {int(result.parks.no_demand_in_catchment.sum())}")


if __name__ == "__main__":
    main()