import pandas as pd
import numpy as np
import pytest
from mobility2access import resolve_thresholds, calibrate_thresholds, park_size_class

def test_beijing_historical_thresholds():
    p=pd.DataFrame({'park_area_ha':[10,35,120]})
    np.testing.assert_allclose(resolve_thresholds(p),[5.3021,6.971,7.8076])

def test_park_column_thresholds():
    p=pd.DataFrame({'park_area_ha':[3,20], 'threshold_km':[2.0,9.0]})
    np.testing.assert_allclose(resolve_thresholds(p,'park_column'),[2,9])

def test_beijing_preset_rejects_out_of_study_parks():
    p=pd.DataFrame({'park_area_ha':[1.9,20.]})
    with pytest.raises(ValueError,match='>2 ha'):
        resolve_thresholds(p)
    np.testing.assert_allclose(resolve_thresholds(p,3.),[3.,3.])

def test_boundary_choice_20_ha_medium():
    assert park_size_class([19.99,20,100,101]).tolist()==['small','medium','medium','large']

def test_calibrate_age_and_park_class():
    v=pd.DataFrame({
      'age_group':['60+']*4+['18-59']*4,
      'park_area_ha':[10]*8,
      'network_distance_km':[1,2,3,4,2,4,6,8],
    })
    res=calibrate_thresholds(v)
    assert np.isclose(res.loc[res.age_group=='60+','threshold_km'].iloc[0],3.25)
    assert np.isclose(res.loc[res.age_group=='18-59','threshold_km'].iloc[0],6.5)

def test_invalid_age_group():
    v=pd.DataFrame({'age_group':[None], 'park_area_ha':[10], 'network_distance_km':[1.]})
    with pytest.raises(ValueError,match='age_group'):
        calibrate_thresholds(v)
