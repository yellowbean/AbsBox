import pandas as pd
from lenses import lens
import toolz as tz
import pytest

from absbox.tests.regression.deals import *

from absbox import API,EnginePath,readInspect,PickApiFrom



@pytest.fixture
def setup_api():


    api = API(EnginePath.DEV,check=False,lang='english')
    
    
    return api

@pytest.mark.pool
def test_01(setup_api):
    r = setup_api.run(test01 , read=True , runAssump = [])
    assert r['pool']['flow'].keys() == {"PoolConsol"}
    assert r['pool']['flow']['PoolConsol'].to_records()[0][0]== '2021-04-15'



