import pandas as pd
from lenses import lens
import toolz as tz
import pytest
import re, math

from absbox.tests.regression.deals import *
from absbox.tests.regression.assets import *

from absbox import API,EnginePath,readInspect,PickApiFrom

def closeTo(a,b,r=2):
    assert math.floor(a * 10**r)/10**r == math.floor(b * 10**r)/10**r

def filterTxn(rs, f, rg):
    return [ r for r in rs if re.match(rg, r[f])] 

@pytest.fixture
def setup_api():
    api = API(EnginePath.DEV, check=False,lang='english')
    return api

@pytest.mark.pool
def test_01(setup_api):
    r = setup_api.run(test01 , read=True , runAssump = [])
    assert r['pool']['flow'].keys() == {"PoolConsol"}
    assert r['pool']['flow']['PoolConsol'].to_records()[0][0]== '2021-04-15'

@pytest.mark.collect
def test_collect_01(setup_api):
    r = setup_api.run(test01 , read=True , runAssump = [])
    assert r['pool']['flow']['PoolConsol'].to_records()[0][0]== '2021-04-15'
    assert r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Interest"].values.sum() == filterTxn( r['accounts']['acc01'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedInterest.*")[0]['change']
    assert r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Principal"].values.sum() == filterTxn( r['accounts']['acc01'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedPrincipal.*")[0]['change']
    assert r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Prepayment"].values.sum() == 0.00
    assert r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Default"].values.sum() == 0.00
    assert r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Recovery"].values.sum() == 0.00

    # two accounts with Principal and Interest
    testSepAcc = tz.pipe( test01 & lens.accounts.modify( lambda xs: tuple(tz.cons( ('acc02',{"balance":0}), xs )))
                        ,lambda d : d & lens.collection[0][1].set("acc02")
                        )

    r = setup_api.run(testSepAcc , read=True , runAssump = [])
    assert r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Interest"].values.sum() == filterTxn( r['accounts']['acc02'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedInterest.*")[0]['change']
    assert r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Principal"].values.sum() == filterTxn( r['accounts']['acc01'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedPrincipal.*")[0]['change']

    # three accounts with Principal( 30% 70%) and Interest
    test2SepAcc = tz.pipe( test01 & lens.accounts.modify( lambda xs: tuple(tz.cons( ('acc02',{"balance":0}), xs )))
                                  & lens.accounts.modify( lambda xs: tuple(tz.cons( ('acc03',{"balance":0}), xs )))
                        ,lambda d : d & lens.collection.set([["CollectedInterest","acc02"]
                                                            ,["CollectedPrincipal",[0.7,"acc01"],[0.3,"acc03"]]
                                                            ,["CollectedPrepayment","acc01"]
                                                            ,["CollectedRecoveries","acc01"]]
                            )
                        )
    r = setup_api.run(test2SepAcc , read=True , runAssump = [])
    assert r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Interest"].values.sum() == filterTxn( r['accounts']['acc02'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedInterest.*")[0]['change']
    principalCollectedAtPeriod0 = r['pool']['flow']['PoolConsol'].loc[:'2021-04-15']["Principal"].values.sum()
    closeTo(principalCollectedAtPeriod0 *0.7
            , filterTxn( r['accounts']['acc01'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedPrincipal.*")[0]['change']
            , 2 )
    closeTo(principalCollectedAtPeriod0*0.3
            , filterTxn( r['accounts']['acc03'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedPrincipal.*")[0]['change']
            , 2)

    # multiple pool with ratio split collection
    testMultiplePool = test01 & lens.accounts.set((("acc01",{"balance":0}),("acc02",{"balance":0}),("acc03",{"balance":0}))) \
                              & lens.pool.set({"PoolA":{'assets':[["Mortgage"
                                                        ,{"originBalance":1320.0,"originRate":["fix",0.045],"originTerm":30
                                                        ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
                                                        ,{"currentBalance":1320.0
                                                        ,"currentRate":0.08
                                                        ,"remainTerm":30
                                                        ,"status":"current"}]]},
                                            "PoolB":{'assets':[["Mortgage"
                                                        ,{"originBalance":880.0,"originRate":["fix",0.045],"originTerm":30
                                                        ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
                                                        ,{"currentBalance":880.0
                                                        ,"currentRate":0.08
                                                        ,"remainTerm":30
                                                        ,"status":"current"}]]}}) \
                              & lens.collection.set([[["PoolA",],"CollectedInterest","acc01"]
                                                    ,[["PoolB",],"CollectedInterest","acc03"]
                                                    ,[["PoolA","PoolB"],"CollectedPrincipal",[0.7,"acc02"],[0.3,"acc03"]]
                                                    ])
    r = setup_api.run(testMultiplePool , read=True , runAssump = [])

    # acc01 get all interest from pool A 
    closeTo(r['pool']['flow']['PoolA'].loc[:'2021-04-15']["Interest"].values.sum()
            , filterTxn( r['accounts']['acc01'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedInterest.*")[0]['change'])
    # acc03 get all interest from pool B
    closeTo(r['pool']['flow']['PoolB'].loc[:'2021-04-15']["Interest"].values.sum()
            , filterTxn( r['accounts']['acc03'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedInterest.*")[0]['change'])
    # acc02 get 70% of principal from pool A and Pool B 
    closeTo((r['pool']['flow']['PoolA'].loc[:'2021-04-15']["Principal"].values.sum() +\
            r['pool']['flow']['PoolB'].loc[:'2021-04-15']["Principal"].values.sum())*0.7
            , filterTxn( r['accounts']['acc02'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedPrincipal.*")[0]['change'])
    # acc03 get all interest from pool B and 30% of principal from pool A and Pool B
    closeTo((r['pool']['flow']['PoolA'].loc[:'2021-04-15']["Principal"].values.sum() +\
            r['pool']['flow']['PoolB'].loc[:'2021-04-15']["Principal"].values.sum())*0.3
            , filterTxn( r['accounts']['acc03'].loc[:'2021-04-15'].to_dict('records'), 'memo', ".*CollectedPrincipal.*")[0]['change'])

def toCprRates(mflow):
    return [ round(_, 3) for _ in  (1 - (1 - mflow.Prepayment.shift(-1) / mflow.Balance)**12).to_list() ]

@pytest.mark.asset
def test_asset_01(setup_api):
    """ PSA """
    r = setup_api.runAsset("2020-01-02"
                    ,[m]
                    ,poolAssump=("Pool"
                                    ,("Mortgage", None, {"PSA":1.0}, None, None)
                                    ,None
                                    ,None)
                    ,read=True)

    assert toCprRates(r[0])[:80] == ([ _/1000 for _ in  range(2,62,2)] + [0.06]*50)

    # m with 60 remaining term
    r = setup_api.runAsset("2020-01-02"
                     ,[m & lens[2]['remainTerm'].set(60)]
                     ,poolAssump=("Pool"
                                    ,("Mortgage", None, {"PSA":1.0}, None, None)
                                    ,None
                                    ,None)
                     ,read=True)
    assert toCprRates(r[0])[:60] == ([ _/1000 for _ in  range(2,62,2)][20:] + [0.06]*50)

    r = setup_api.runAsset("2020-01-02"
                     ,[m & lens[2]['remainTerm'].set(10)]
                     ,poolAssump=("Pool"
                                    ,("Mortgage", None, {"PSA":1.0}, None, None)
                                    ,None
                                    ,None)
                     ,read=True)
    assert toCprRates(r[0])[:10] == ([0.06]*10)