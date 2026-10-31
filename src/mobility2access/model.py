"""Gaussian two-step floating catchment area with arbitrary study units."""
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from .thresholds import resolve_thresholds

@dataclass
class AccessibilityResults:
    units: pd.DataFrame
    parks: pd.DataFrame
    gini: float
    lorenz: pd.DataFrame

def gaussian_decay(distance_km, threshold_km):
    """Truncated Gaussian: w(0)=1; w(D)=0."""
    d = np.asarray(distance_km, dtype=float)
    D = np.asarray(threshold_km, dtype=float)
    if np.any(np.isnan(d)) or np.any(d < 0) or np.any(np.isneginf(d)):
        raise ValueError("network_distance_km must be >=0; use +inf for unreachable")
    if np.any(~np.isfinite(D)) or np.any(D <= 0):
        raise ValueError("Catchment thresholds must be positive and finite")
    ratio = d / D
    w = np.where(d < D, (np.exp(-0.5 * np.minimum(ratio, 1.0)**2) - np.exp(-0.5)) /
                 (1.0 - np.exp(-0.5)), 0.0)
    return np.maximum(w, 0.0)

def _weighted_lorenz(accessibility: np.ndarray, pop: np.ndarray):
    mask = pop > 0
    a, p = accessibility[mask], pop[mask]
    order = np.argsort(a, kind="stable")
    a, p = a[order], p[order]
    x = np.r_[0.0, np.cumsum(p, dtype=float) / p.sum()]
    gain = a * p
    total = gain.sum()
    y = np.r_[0.0, np.cumsum(gain) / total] if total > 0 else x.copy()
    gini = float(np.clip(1.0 - np.sum((y[1:] + y[:-1]) * np.diff(x)), 0, 1))
    return gini, pd.DataFrame({"population_share": x, "access_share": y})

def calculate_accessibility(
    units: pd.DataFrame,
    parks: pd.DataFrame,
    distances: pd.DataFrame,
    *,
    population_column: str = "population",
    thresholds: Any,
) -> AccessibilityResults:
    """Gaussian 2SFCA using unit/park/road-distance tables. Output: m²/person."""
    for name, df, fields in [
        ("units", units, {"unit_id", population_column}),
        ("parks", parks, {"park_id", "park_area_ha"}),
        ("distances", distances, {"unit_id", "park_id", "network_distance_km"}),
    ]:
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame (or GeoDataFrame)")
        missing = fields - set(df.columns)
        if missing:
            raise ValueError(f"{name} missing columns {sorted(missing)}")
    if units.empty or parks.empty:
        raise ValueError("units and parks must not be empty")
    if units["unit_id"].isna().any() or units["unit_id"].duplicated().any():
        raise ValueError("units.unit_id must be unique and not null")
    if parks["park_id"].isna().any() or parks["park_id"].duplicated().any():
        raise ValueError("parks.park_id must be unique and not null")
    unit_ids = pd.Index(units["unit_id"].astype(str))
    park_ids = pd.Index(parks["park_id"].astype(str))
    if unit_ids.duplicated().any() or park_ids.duplicated().any():
        raise ValueError("IDs must remain unique after converting to strings")
    pop = pd.to_numeric(units[population_column], errors="raise").to_numpy(dtype=float)
    areas = pd.to_numeric(parks["park_area_ha"], errors="raise").to_numpy(dtype=float)
    if np.any(~np.isfinite(pop)) or np.any(pop < 0) or pop.sum() <= 0:
        raise ValueError("Population counts must be finite, >=0, and sum to >0")
    if np.any(~np.isfinite(areas)) or np.any(areas <= 0):
        raise ValueError("Park area must be positive and finite (hectares)")
    cutoff = resolve_thresholds(parks, thresholds)
    d = distances[["unit_id", "park_id", "network_distance_km"]].copy()
    if d[["unit_id", "park_id"]].isna().any().any():
        raise ValueError("Distance IDs cannot be null")
    if d.duplicated(["unit_id", "park_id"]).any():
        raise ValueError("A unit-park OD pair occurs more than once")
    ui = unit_ids.get_indexer(d["unit_id"].astype(str))
    pj = park_ids.get_indexer(d["park_id"].astype(str))
    if (ui < 0).any() or (pj < 0).any():
        raise ValueError("Every OD pair must reference a known unit_id and park_id")
    dd = pd.to_numeric(d["network_distance_km"], errors="raise").to_numpy(dtype=float)
    if np.any(np.isnan(dd)) or np.any(dd < 0) or np.any(np.isneginf(dd)):
        raise ValueError("Distances must be nonnegative, or +inf if unreachable")
    inside = np.isfinite(dd) & (dd < cutoff[pj])
    ui, pj, dd = ui[inside], pj[inside], dd[inside]
    weights = gaussian_decay(dd, cutoff[pj])
    demand = np.bincount(pj, weights=weights * pop[ui], minlength=len(parks))
    ratio = np.divide(areas * 10000.0, demand, out=np.zeros(len(parks)), where=demand > 0)
    acc = np.bincount(ui, weights=weights * ratio[pj], minlength=len(units))
    gini, lorenz = _weighted_lorenz(acc, pop)
    result_units = units.copy()
    result_units["accessibility_m2_per_person"] = acc
    result_parks = parks.copy()
    result_parks["catchment_km"] = cutoff
    result_parks["weighted_demand_population"] = demand
    result_parks["park_supply_ratio_m2_per_person"] = ratio
    result_parks["no_demand_in_catchment"] = demand == 0
    return AccessibilityResults(result_units, result_parks, gini, lorenz)
