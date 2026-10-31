import numpy as np
import pandas as pd
import pytest
from mobility2access import calculate_accessibility, gaussian_decay

def make_inputs():
    units = pd.DataFrame({"unit_id": ["u1", "u2"], "elderly": [10, 30]})
    parks = pd.DataFrame({"park_id": ["a", "b"], "park_area_ha": [10, 20]})
    distances = pd.DataFrame({
        "unit_id": ["u1", "u2", "u1", "u2"],
        "park_id": ["a", "a", "b", "b"],
        "network_distance_km": [0, 1, 1, 0],
    })
    return units, parks, distances

def test_gaussian_boundary_and_midpoint():
    arr = gaussian_decay([0, 2.5, 5.0, 6.0, float('inf')], 5)
    assert np.isclose(arr[0], 1)
    assert 0 < arr[1] < 1
    assert np.array_equal(arr[2:], np.zeros(3))

def test_two_steps_by_hand():
    units = pd.DataFrame({"unit_id": ["a", "b"], "population": [10, 30]})
    parks = pd.DataFrame({"park_id": ["p"], "park_area_ha": [2]})
    od = pd.DataFrame({"unit_id": ["a", "b"], "park_id": ["p", "p"], "network_distance_km": [0., 3.]})
    w2 = (np.exp(-0.5*(3/6)**2) - np.exp(-0.5)) / (1-np.exp(-0.5))
    denom = 10 + 30*w2
    expected = np.array([20000/denom, 20000*w2/denom])
    res = calculate_accessibility(units, parks, od, thresholds=6.0)
    np.testing.assert_allclose(res.units.accessibility_m2_per_person, expected)
    assert np.isclose(res.parks.weighted_demand_population.iloc[0], denom)
    assert np.isclose(res.units.accessibility_m2_per_person.iloc[0]*10 + res.units.accessibility_m2_per_person.iloc[1]*30, 20000)

def test_size_specific_and_conservation():
    u,p,d = make_inputs()
    res = calculate_accessibility(u,p,d,population_column='elderly', thresholds={'small':4.,'medium':6.,'large':8.})
    np.testing.assert_allclose(res.parks.catchment_km, [4,6])
    assert np.isclose(np.dot(u.elderly, res.units.accessibility_m2_per_person), 300000)
    assert (res.units.accessibility_m2_per_person > 0).all()

def test_unreachable_pair_absent_or_infinity():
    u,p,d = make_inputs()
    p=p.iloc[:1].copy()
    a=calculate_accessibility(u,p,d.iloc[[0]].copy(),population_column='elderly',thresholds=2.)
    assert a.units.accessibility_m2_per_person.iloc[1] == 0
    b=d.iloc[:2].copy()
    b['network_distance_km'] = b['network_distance_km'].astype(float)
    b.loc[1,'network_distance_km']=float('inf')
    c=calculate_accessibility(u,p,b,population_column='elderly',thresholds=2.)
    np.testing.assert_allclose(a.units.accessibility_m2_per_person, c.units.accessibility_m2_per_person)

def test_zero_weighted_demand_park_flagged():
    u,p,d = make_inputs()
    p=p.iloc[:1].copy()
    d=d.iloc[:2].copy()
    d['network_distance_km']=[10,11]
    res=calculate_accessibility(u,p,d,population_column='elderly',thresholds=4.)
    assert res.parks.no_demand_in_catchment.iloc[0]
    assert (res.units.accessibility_m2_per_person == 0).all()
    assert res.gini == 0

def test_street_ids_and_units_preserved():
    u,p,d=make_inputs()
    u['street_name']=['X','Y']
    u['unit_id']=['S-001','S-002']
    d['unit_id']=d['unit_id'].replace({'u1':'S-001','u2':'S-002'})
    out=calculate_accessibility(u,p,d,population_column='elderly',thresholds=5.)
    assert out.units.unit_id.tolist()==['S-001','S-002']
    assert out.units.street_name.tolist()==['X','Y']

def test_duplicate_pair_rejected():
    u,p,d=make_inputs()
    d=pd.concat([d,d.iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError, match='more than once'):
        calculate_accessibility(u,p,d,population_column='elderly',thresholds=5.)

def test_missing_population_column_rejected():
    u,p,d=make_inputs()
    with pytest.raises(ValueError,match='missing columns'):
        calculate_accessibility(u,p,d,population_column='no_such_column',thresholds=5.)

def test_negative_distances_rejected_not_zeroed():
    u,p,d=make_inputs()
    d.loc[0,'network_distance_km']=-1
    with pytest.raises(ValueError,match='nonnegative'):
        calculate_accessibility(u,p,d,population_column='elderly',thresholds=5.)

def test_bad_od_reference_rejected():
    u,p,d=make_inputs()
    d.loc[0,'unit_id']='other'
    with pytest.raises(ValueError,match='known'):
        calculate_accessibility(u,p,d,population_column='elderly',thresholds=5.)

def test_population_zero_does_not_break_weighted_lorenz():
    u,p,d=make_inputs()
    u.loc[0,'elderly']=0
    out=calculate_accessibility(u,p,d,population_column='elderly',thresholds=4.)
    assert out.gini == 0

def test_simple_gini_half():
    u = pd.DataFrame({'unit_id':['A','B'], 'population':[1,1]})
    p = pd.DataFrame({'park_id':['P'], 'park_area_ha':[1.]})
    d = pd.DataFrame({'unit_id':['B'],'park_id':['P'],'network_distance_km':[0.]})
    out=calculate_accessibility(u,p,d,thresholds=1.)
    assert np.isclose(out.gini, .5)
    assert np.allclose(out.lorenz.population_share, [0,.5,1])
    assert np.allclose(out.lorenz.access_share, [0,0,1])
