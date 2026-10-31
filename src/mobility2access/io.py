"""Read/write study unit files; GeoPandas is an optional dependency."""
from pathlib import Path
import pandas as pd

def load_table(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype={"unit_id": str, "park_id": str})
    if path.suffix.lower() in {".geojson", ".gpkg", ".shp"}:
        try:
            import geopandas as gpd
        except ImportError as ex:
            raise ImportError("For GIS polygon files, install: pip install -e '.[gis]'") from ex
        result = gpd.read_file(path)
        for key in ("unit_id", "park_id"):
            if key in result.columns:
                result[key] = result[key].astype(str)
        return result
    raise ValueError("Files must be .csv, .geojson, .gpkg, or .shp")

def save_table(frame, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv":
        frame.drop(columns=["geometry"], errors="ignore").to_csv(path, index=False)
    elif path.suffix.lower() in {".geojson", ".gpkg"}:
        try:
            import geopandas as gpd
        except ImportError as ex:
            raise ImportError("For GIS spatial outputs, install: pip install -e '.[gis]'") from ex
        if not isinstance(frame, gpd.GeoDataFrame):
            raise ValueError("GeoJSON/GeoPackage output requires polygon input units with geometry")
        frame.to_file(path, driver="GPKG" if path.suffix.lower() == ".gpkg" else "GeoJSON")
    else:
        raise ValueError("Output path must end in .csv, .gpkg, or .geojson")
