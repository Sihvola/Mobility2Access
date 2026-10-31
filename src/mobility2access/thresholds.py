"""Park-size-specific catchment thresholds (distances in kilometers)."""
from collections.abc import Mapping
import numpy as np
import pandas as pd

BEIJING_2019_ELDERLY_KM = {"small": 5.3021, "medium": 6.9710, "large": 7.8076}

def park_size_class(area_ha, *, require_study_range=False):
    """Small: <20 ha; medium: 20-100 ha; large: >100 ha."""
    area = np.asarray(area_ha, dtype=float)
    if np.any(~np.isfinite(area)) or np.any(area <= 0):
        raise ValueError("park_area_ha must be finite and positive")
    if require_study_range and np.any(area <= 2):
        raise ValueError("The Beijing 2019 profile was fitted on parks >2 ha.")
    return np.where(area < 20, "small", np.where(area <= 100, "medium", "large"))

def resolve_thresholds(parks: pd.DataFrame, thresholds="beijing2019_elderly") -> np.ndarray:
    """Choose Beijing empirical, uniform, class-specific or per-park cutoffs."""
    if "park_area_ha" not in parks.columns:
        raise ValueError("parks must include park_area_ha")
    areas = pd.to_numeric(parks["park_area_ha"], errors="raise").to_numpy(dtype=float)
    if isinstance(thresholds, str):
        if thresholds == "beijing2019_elderly":
            names = park_size_class(areas, require_study_range=True)
            values = [BEIJING_2019_ELDERLY_KM[name] for name in names]
        elif thresholds == "park_column":
            if "threshold_km" not in parks.columns:
                raise ValueError("For thresholds='park_column', parks need threshold_km")
            values = parks["threshold_km"].to_numpy()
        else:
            raise ValueError("Unknown thresholds profile")
    elif isinstance(thresholds, Mapping):
        if set(thresholds) != {"small", "medium", "large"}:
            raise ValueError("threshold mappings must have keys small, medium, large")
        names = park_size_class(areas)
        values = [thresholds[name] for name in names]
    elif isinstance(thresholds, (float, int, np.floating, np.integer)) and not isinstance(thresholds, (bool, np.bool_)):
        values = np.repeat(thresholds, len(parks))
    else:
        raise TypeError("Unsupported thresholds specification")
    vals = np.asarray(values, dtype=float)
    if vals.shape != (len(parks),) or np.any(~np.isfinite(vals)) or np.any(vals <= 0):
        raise ValueError("All park catchment thresholds must be finite and positive")
    return vals

def calibrate_thresholds(visits: pd.DataFrame, *, quantile=0.75) -> pd.DataFrame:
    """Estimate age-by-park-size threshold from pre-identified visits."""
    required = {"age_group", "park_area_ha", "network_distance_km"}
    missing = required - set(visits.columns)
    if missing:
        raise ValueError(f"visits are missing columns: {sorted(missing)}")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")
    tmp = visits.copy()
    if tmp.empty or tmp["age_group"].isna().any():
        raise ValueError("visits must be nonempty and age_group cannot be missing")
    dist = pd.to_numeric(tmp["network_distance_km"], errors="raise").to_numpy(dtype=float)
    if np.any(~np.isfinite(dist)) or np.any(dist < 0):
        raise ValueError("Visit distances must be finite and nonnegative")
    tmp["network_distance_km"] = dist
    tmp["size_class"] = park_size_class(tmp["park_area_ha"].to_numpy(dtype=float))
    grouped = tmp.groupby(["age_group", "size_class"], sort=True, observed=True)["network_distance_km"]
    return grouped.agg(n_visits="size", threshold_km=lambda x: x.quantile(quantile)).reset_index()
