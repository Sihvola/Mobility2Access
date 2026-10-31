# Method and assumptions

## Gaussian 2SFCA

For each park j with area S_j (m²), service radius D_j (km), study unit i with population P_i, and road-network distance d_ij:

```text
w(d,D) = (exp(-0.5*(d/D)^2) - exp(-0.5)) / (1 - exp(-0.5)),  0 <= d < D
       = 0,                                                      d >= D
R_j = S_j / sum_i [P_i * w(d_ij,D_j)]
A_i = sum_j [R_j * w(d_ij,D_j)]
```

The supply measure is park area (hectares * 10,000), so accessibility is in m² per person. Each park may have a different cutoff D_j, applied consistently in both steps. Missing OD pairs are treated as unreachable. A park with no weighted demand has R_j set to 0, and is flagged in park diagnostics. Results retain the original study unit rows (including geometry if provided).

## Beijing older-adult profile

Historical empirical cutoffs from the paper's reported Figure 2: 5.3021 km (small), 6.9710 km (medium), 7.8076 km (large), based on the 75th percentile of observed visitor home-to-park network distances. The study investigated parks over 2 ha. The implemented class rule assigns area <20 ha to small; 20–100 ha medium; >100 ha large. The 20 ha boundary is a documented implementation convention.

Other ages, other park types or other cities require local calibration or explicit user-configured cutoffs.

## Threshold calibration

`calibrate_thresholds` accepts PREPROCESSED park visits (age_group, park_area_ha, network_distance_km). It takes a pandas linear-interpolated 75th percentile by age group and park size. It does not reconstruct mobile-phone trajectories or infer homes and parks from raw signaling records.

## Equity assessment

Sort study units by individual accessibility A_i and weight each A_i by the selected unit population P_i. Lorenz coordinates are cumulative shares of population and P_i * A_i. Gini = 1 - sum over adjacent points of the trapezoid areas multiplied by 2. When everyone has zero access, the software defines Gini as 0 by convention.

This weighted definition must be compared with the precise denominator and weighting in any original published result before claiming numeric replication.

## Scope

This package is a clean Python reconstruction of the key accessibility workflow, not an exact reproduction of every reported Beijing statistic. All bundled data are synthetic. Road-network OD distances must currently be prepared externally.
