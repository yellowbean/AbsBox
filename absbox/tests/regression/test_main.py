import pandas as pd
from lenses import lens
import toolz as tz
import pytest
import re, math, json
from pathlib import Path
from collections import Counter
from itertools import dropwhile
import numpy_financial as npf
from datetime import datetime
import numpy as np


from .deals import *
from .assets import *
from .pool import *

from absbox import API,EnginePath,readInspect,PickApiFrom,readBondsCf
from absbox.exception import AbsboxError

config_file_path = Path(__file__).resolve().parent.parent / 'config.json'

def closeTo(a,b,r=2):
    assert math.floor(a * 10**r)/10**r == math.floor(b * 10**r)/10**r

def filterTxn(rs, f, rg):
    return [ r for r in rs if re.match(rg, r[f])] 

def filterRowsByStr(df, f, rg):
    """ Filter rows by regex on column f """
    return filterTxn(df.to_dict('records'), f, rg)

def listCloseTo(a,b,r=2):
    assert len(a) == len(b), f"Length not match {len(a)} {len(b)}"
    assert all([ closeTo(x,y,r)  for x,y in zip(a,b)]), f"List not match {a},{b}"

def listCloseByAbs(a,b, tol=0.01):
    assert len(a) == len(b), f"Length not match {len(a)} {len(b)}"
    assert all([ abs(x-y) <= tol  for x,y in zip(a,b)]), f"List not match {a},{b}"

def allEq(xs, x):
    return all([ _ == x for _ in xs])

def eqDataFrame(a,b, msg=""):
    """ Compare two DataFrame """
    assert a.shape == b.shape, f"Shape not match {a.shape} {b.shape}"
    assert a.compare(b).empty == True, f"DataFrame not match {a.compare(b)} \n {msg}"

def eqDataFrameByLens(a, b, l, fn=None, msg=""):
    """ a,b -> object to lookup, l -> lens to get DataFrame """
    da = a & l.get()
    db = b & l.get()
    if fn is None:
      eqDataFrame(da, db, msg=msg)
    else:
      eqDataFrame(fn(da), fn(db), msg=msg)


def seniorTest(x, y):
    xx = pd.concat([x.rename("Left"),y.rename("Right")],axis=1).fillna(0)
    xflags = xx["Left"]- xx["Right"] == xx["Left"]
    yflags = xx["Right"] - xx["Left"] == xx["Right"]
    rflags = xflags | yflags
    f = dropwhile( lambda y: not y, dropwhile(lambda x:x ,xflags))
    return len(list(f)) == 0 & Counter(rflags).get("False",0) <= 1

def insert_functional(lst, index, element):
    return lst[:index] + [element] + lst[index:]

def days_between_dates(date1, date2):
    """
    Calculate the number of days between two dates.
    
    Args:
        date1 (str): First date in "YYYY-MM-DD" format
        date2 (str): Second date in "YYYY-MM-DD" format
    
    Returns:
        int: Absolute number of days between the two dates
    """
    try:
        # Convert string dates to datetime objects
        d1 = datetime.datetime.strptime(date1, "%Y-%m-%d")
        d2 = datetime.datetime.strptime(date2, "%Y-%m-%d")
        
        # Calculate the difference and return absolute value in days
        delta = abs(d2 - d1)
        return delta.days
        
    except ValueError as e:
        raise ValueError(f"Invalid date format. Please use 'YYYY-MM-DD'. Error: {e}")

@pytest.fixture
def setup_api():
    with config_file_path.open('r') as config_file:
        config = json.load(config_file)
    api = API(config['test_server'], check=False, lang='english')
    return api


@pytest.mark.pool
def test_01(setup_api):
    testFlag = []
    r = setup_api.run(test01 , read=True , runAssump = testFlag)
    assert r['pool']['flow'].keys() == {"PoolConsol"}
    assert r['pool']['flow']['PoolConsol']['Principal'].sum() == 2200.0
    assert r['pool']['flow']['PoolConsol'].to_records()[0][0]== '2021-04-15'
    assert r['bonds']['A1'].interest.to_list()[0] == 19.56
    
    #r2 = setup_api.run(accruedDeal, read=True, runAssump = testFlag)
    #assert r['pool']['flow']['PoolConsol'] == r2['pool']['flow']['PoolConsol']
    #assert r['bonds']['A1'].interest.to_list() == r2['bonds']['A1'].interest.to_list()


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

def toCprRates(mflow, rnd=3):
    return [ round(_, rnd) for _ in  (1 - (1 - mflow.Prepayment.shift(-1) / mflow.Balance)**12).to_list() ]

def ppyRate(mflow, rnd=3):
    return [ round(_, rnd) for _ in  (mflow.Prepayment / mflow.Balance.shift(1)).to_list() ]

def defRate(mflow, rnd=3):
    return [ round(_, rnd) for _ in  (mflow.Default / mflow.Balance.shift(1)).to_list() ]

def toCdrRates(mflow, rnd=3):
    return [ round(_, rnd) for _ in  (1 - (1 - mflow.Default.shift(-1) / mflow.Balance)**12).to_list() ]


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

    # test on cutoff date
    r1 = setup_api.runAsset("2021-10-01"
                    ,[m]
                    ,poolAssump=("Pool"
                                    ,("Mortgage", None, None, None, None)
                                    ,None
                                    ,None)
                    ,read=True)
    assert r1[0].index[0]=='2021-10-01'

    
    # test on mortgage asset
    r = setup_api.runAsset("2021-02-01"
                    ,[m]
                    ,poolAssump=("Pool"
                                    ,("Mortgage", None, None, None, None)
                                    ,None
                                    ,None)
                    ,read=True)
    assert r[0].Principal.sum().item()==10000.0
    assert set(r[0].WAC.to_list()) == {0.075}
    assert r[0].shape == (81,16)
    testPmt = set((r[0].Principal + r[0].Interest).round(1))  - {0.0}
    pyPmt = npf.pmt(m[2]['currentRate']/12,m[2]['remainTerm'],-m[2]['currentBalance']).round(1)
    assert set([pyPmt.item()]) == testPmt
    
@pytest.mark.asset
def test_asset_03(setup_api):    
    ## Mortgage Performance
    r = setup_api.runAsset("2021-02-01"
                    ,[m]
                    ,poolAssump=("Pool"
                                    ,("Mortgage", {"CDR":0.01}, None, None, None)
                                    ,None
                                    ,None)
                    ,read=True)
    assert set(toCdrRates(r[0],2)[:-1]) == {0.01}
    
    r = setup_api.runAsset("2021-02-01"
                    ,[m]
                    ,poolAssump=("Pool"
                                    ,("Mortgage", {"CDR":0.01}, None, {"Rate":0.3,"Lag":5}, None)
                                    ,None
                                    ,None)
                    ,read=True)
    assert set(toCdrRates(r[0].iloc[:-5],2)[:-1]) == {0.01}
    assert round(r[0].CumRecovery.iloc[-1] / r[0].CumDefault.iloc[-1],2) == 0.3
    #assert listCloseTo((r[0].Default.iloc[:-5] * 0.3).round(1).to_list()
    #                    , r[0].Recovery.shift(-5).iloc[:-5].round(1).to_list()
    #                    ,r=2)
    r = setup_api.runAsset("2021-02-01"
                    ,[m]
                    ,poolAssump=("Pool"
                                    ,("Mortgage", None, {"CPR":0.01}, None, None)
                                    ,None
                                    ,None)
                    ,read=True)
    assert set(toCprRates(r[0],2)[:-1]) == {0.01}    

    r = setup_api.runAsset("2021-02-01"
                    ,[m]
                    ,poolAssump=("Pool"
                                    ,("Mortgage", {"CDR":0.02}, {"CPR":0.01}, None, None)
                                    ,None
                                    ,None)
                    ,read=True)
    assert set(toCprRates(r[0],2)[:-1]) == {0.01}
    assert set(toCdrRates(r[0],2)[:-1]) == {0.02}
    
    
    



@pytest.mark.asset
def test_asset_02(setup_api):
    """ Assump byTerm """

    byTermAssump = [ [0.01]*9+[0.02]*9
                    ,[0.02]*6+[0.03]*6
                    ,[0.03]*3+[0.04]*3  ]

    r = setup_api.runAsset("2020-01-02"
                        ,[m1]
                        ,poolAssump=("Pool"
                                        ,("Mortgage", {"byTerm":byTermAssump}, None, None, None)
                                        ,None
                                        ,None)
                        ,read=True)

    assert defRate(r[0])[1:] == [0.01, 0.01, 0.01, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02]

    ## pick 12month term 
    r = setup_api.runAsset("2020-01-02"
                        ,[m1 & lens[1]['originTerm'].set(12)
                            & lens[2]['remainTerm'].set(9)]
                        ,poolAssump=("Pool"
                                        ,("Mortgage", {"byTerm":byTermAssump}, None, None, None)
                                        ,None
                                        ,None)
                        ,read=True)
    assert defRate(r[0])[1:] == [0.02, 0.02, 0.02]+[0.03]*6
    ## using prepay
    r = setup_api.runAsset("2020-01-02"
                        ,[m1 & lens[1]['originTerm'].set(12)
                            & lens[2]['remainTerm'].set(9)]
                        ,poolAssump=("Pool"
                                        ,("Mortgage",None, {"byTerm":byTermAssump}, None, None)
                                        ,None
                                        ,None)
                        ,read=True)
    assert ppyRate(r[0])[1:] == [0.02, 0.02, 0.02]+[0.03]*6


@pytest.mark.pool
def test_pool_01(setup_api):
    r = setup_api.runPool(myPool
                        ,poolAssump=("Pool",("Mortgage",None,None,None,None)
                                        ,None
                                        ,None)
                        ,read = True
                        ,breakdown = False)
    assert 'breakdown' not in r['PoolConsol'], "breakdown should not be in PoolConsol"
    r = setup_api.runPool(myPool
                        ,poolAssump=("Pool",("Mortgage",None,None,None,None)
                                        ,None
                                        ,None)
                        ,read = True
                        ,breakdown = True)
    assert 'breakdown' in r['PoolConsol'], "breakdown should be in PoolConsol"  
    assert 2 == len(r['PoolConsol']['breakdown']), "breakdown should have 2 items"

@pytest.mark.analytics
def test_first_loss(setup_api):
    r0 = setup_api.runFirstLoss(test01
                    ,"A1"
                    ,poolAssump=("Pool",("Mortgage",{"CDRPadding":[0.01,0.02]}
                                                    ,{"CPR":0.02}
                                                    ,{"Rate":0.1,"Lag":5}
                                                    ,None)
                                    ,None
                                    ,None)
                    ,read=True)
    closeTo(r0[0], 31.601832129896755, r=6)

@pytest.mark.analytics
def test_irr_01(setup_api):
    r0 = setup_api.run(Irr01
                    ,poolAssump=("Pool",("Mortgage",{"CDRPadding":[0.01,0.02]},{"CPR":0.02},{"Rate":0.1,"Lag":5},None)
                                    ,None
                                    ,None)
                    ,runAssump = [("pricing",{"IRR":{"B":("holding",[("2021-04-01",-500)],500)}
                                              })]
                    ,read=True
                    )
    closeTo(r0['pricing']['summary'].loc["B"].IRR, 0.264238, r=6)

    r1 = setup_api.run(Irr01
                ,poolAssump=("Pool",("Mortgage",{"CDRPadding":[0.01,0.02]},{"CPR":0.02},{"Rate":0.1,"Lag":5},None)
                                ,None
                                ,None)
                ,runAssump = [("pricing",{"IRR":
                                          {"A1":("holding",[("2021-04-01",-500)],500,"2021-08-19",("byFactor",1.0))}
                                         }
                              )]
                ,read=True)

    closeTo(r1['pricing']['summary'].loc["A1"].IRR, 0.07196, r=6)

    r3 = setup_api.run(Irr01
                ,poolAssump=("Pool",("Mortgage",{"CDRPadding":[0.01,0.02]},{"CPR":0.02},{"Rate":0.1,"Lag":5},None)
                                ,None
                                ,None)
                ,runAssump = [("pricing",{"IRR":
                                          {"A1":("buy","2021-08-01",("byFactor",0.99),("byCash",200))}
                                          
                                         }
                              )]
                ,read=True)
    
    closeTo(r3['pricing']['summary'].loc["A1"].IRR, 0.139824, r=6)


@pytest.mark.analytics
def test_rootfind_stressppy(setup_api):
    poolPerf = ("Pool",("Mortgage",{"CDR":0.002},{"CPR":0.001},{"Rate":0.1,"Lag":18},None)
                                 ,None
                                 ,None)
    pricing = ("pricing",{"IRR":{"B":("holding",[("2021-04-15",-1000)],1000)}
                          })
    r = setup_api.runRootFinder(test01, poolPerf ,[pricing]
        ,("stressPrepayment",("bondMetTargetIrr", "B", 0.25))
    )
    assert r[1][1]['PoolLevel'][0]['MortgageAssump'][1] == {'PrepaymentCPR': 0.38640740263106543 } 

    assert r[0] == 386.40740263106545, "scale factor is off {r[0]}"
    
    r = setup_api.runRootFinder(test01, poolPerf ,[pricing]
        ,(("stressPrepayment", 1,400),("bondMetTargetIrr", "B", 0.25))
    )
    assert r[1][1]['PoolLevel'][0]['MortgageAssump'][1] == {'PrepaymentCPR': 0.38640737599372227  } 
    
    with pytest.raises(AbsboxError):
        r = setup_api.runRootFinder(test01, poolPerf ,[pricing]
            ,(("stressPrepayment", 1,35),("bondMetTargetIrr", "B", 0.25))
        )

@pytest.mark.analytics
def test_rootfind_stressdef(setup_api):
    poolPerf = ("Pool",("Mortgage",{"CDR":0.002},{"CPR":0.001},{"Rate":0.1,"Lag":18},None)
                                 ,None
                                 ,None)
    pricing = ("pricing",{"IRR":{"B":("holding",[("2021-04-15",-1000)],1000)}
                          })
    r = setup_api.runRootFinder(test01, poolPerf ,[pricing]
        ,("stressDefault",("bondMetTargetIrr", "B", 0.10))
    )
    assert r[1][1]['PoolLevel'][0]['MortgageAssump'][0] == {'DefaultCDR': 0.0760391873750556 } 

@pytest.mark.bond
def test_pac_01(setup_api):
    r = setup_api.run(pac01 , read=True , runAssump = [])
    assert r['bonds']["A1"].loc["2021-07-26":"2021-11-20"].balance.to_list() == [800.0, 750.0, 700.0, 650.0, 572.71]


@pytest.mark.bond
def test_pac_02(setup_api):
    r = setup_api.run(pac02 , read=True , runAssump = [])
    assert r['bonds']["A1"].loc["2021-07-26":"2021-11-20"].balance.to_list() == [800.0, 750.0, 700.0, 622.87, 545.42, ] 

    r = setup_api.run(pac02 & lens.bonds[0][1]['bondType'].modify(lambda x: tz.dissoc(x,"anchorBonds"))
                    , read=True , runAssump=[])
    assert r['bonds']['A1'].loc['2021-10-20'].balance.item() == 650

@pytest.mark.bond
def test_pac_03(setup_api):
    r = setup_api.run(pac03 , read=True , runAssump = [])
    groupBals = readBondsCf(r['bonds']).xs('balance',axis=1,level=2)[[("A","A1"),("A","A2")]].sum(axis=1).loc["2021-07-26":"2021-10-20"].to_list()
    assert groupBals == [1050.0, 980.0, 915.0, 880.0]

@pytest.mark.bond
def test_pac_04(setup_api):
    r = setup_api.run(pac04 , read=True , runAssump = [])
    groupBals = readBondsCf(r['bonds']).xs('balance',axis=1,level=2)[[("A","A1"),("A","A2")]].sum(axis=1).loc["2021-07-26":"2021-12-20"].to_list() 
    assert groupBals == [1050.0, 980.0, 915.0, 880.0, 850.0, 773.73], "Got"+str(groupBals)

@pytest.mark.bond
def test_bondGrp(setup_api):
    r = setup_api.run(bondGrp , read=True , runAssump = [])
    grpFlow = readBondsCf(r['bonds'])['A'].xs('balance',axis=1,level=1)
    assert grpFlow.A1.to_list()[:8] == [1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 993.93]
    assert grpFlow.A2.to_list()[:8] == [510.6, 436.68, 364.06, 290.75, 217.26, 143.1, 68.74, 0.0,]

    assert seniorTest(r['bonds']['A']['A2'].principal,r['bonds']['A']['A1'].principal), "A2 should be senior to A1"

    r = setup_api.run(bondGrp & lens.waterfall['default'][1][3].set("byName")
                      , read=True , runAssump = [])
    assert seniorTest(r['bonds']['A']['A1'].principal,r['bonds']['A']['A2'].principal), "byName: A1 should be senior to A2"
    
    r = setup_api.run(bondGrp & lens.waterfall['default'][1][3].set(('reverse',"byName")))
    assert seniorTest(r['bonds']['A']['A2'].principal,r['bonds']['A']['A1'].principal), "byName: A2 should be senior to A1"

    r = setup_api.run(bondGrp & lens.waterfall['default'][1][3].set("byProrata")
                      , read=True , runAssump = [])
    allEqTo08 = (r['bonds']['A']['A2'].principal / r['bonds']['A']['A1'].principal).round(2) == 0.8
    assert all(allEqTo08), "byProrata: A2 should be 0.8 of A1"

    r = setup_api.run(bondGrp & lens.waterfall['default'][1][3].set("byCurRate")
                          & lens.bonds[0][1][1]["A1"]['rate'].set(0.06)
                  , read=True , runAssump = [])
    assert seniorTest(r['bonds']['A']['A2'].principal,r['bonds']['A']['A1'].principal), "A2 should be senior to A1"

    r = setup_api.run(bondGrp & lens.waterfall['default'][1][3].set(("reverse", "byCurRate"))
                          & lens.bonds[0][1][1]["A1"]['rate'].set(0.06)
                  , read=True , runAssump = [])
    assert seniorTest(r['bonds']['A']['A1'].principal,r['bonds']['A']['A2'].principal), "A1 should be senior to A2"

    #test by maturity date
    d = bondGrp & lens.bonds[0][1][1]["A1"].modify(lambda x: tz.assoc(x,"maturityDate","2026-01-01"))\
        & lens.bonds[0][1][1]["A2"].modify(lambda x: tz.assoc(x,"maturityDate","2025-01-01"))\
        & lens.waterfall['default'][1][3].set("byMaturity")

    r = setup_api.run(d, read=True , runAssump = [])
    assert seniorTest(r['bonds']['A']['A2'].principal,r['bonds']['A']['A1'].principal), "A2 should be senior to A1"

    d = bondGrp & lens.bonds[0][1][1]["A2"].modify(lambda x: tz.assoc(x,"startDate","2020-01-02"))\
        & lens.waterfall['default'][1][3].set("byStartDate")

    r = setup_api.run(d, read=True , runAssump = [])
    assert seniorTest(r['bonds']['A']['A2'].principal,r['bonds']['A']['A1'].principal), "A2 should be senior to A1"

@pytest.mark.trigger
def test_trigger_chgBondRate(setup_api):
    withTrigger = test01 & lens.trigger.set({
                    "BeforeDistribution":{
                        "changeBndRt":{"condition":[">=","2021-08-20"]
                                    ,"effects":("changeBondRate", "A1", {"floater":[0.05, "SOFR1Y",-0.02,"MonthEnd"]}, 0.12)
                                    ,"status":False
                                    ,"curable":False}
                    }
                    })
    r = setup_api.run(withTrigger , read=True ,runAssump = [("interest",("SOFR1Y",0.04))])
    assert r['bonds']['A1'].rate.to_list() == [0.07, 0.12, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02]

@pytest.mark.pool
def test_pool_lease_end(setup_api):
    """ Lease end date """
    myPool = {'assets':[l1],'cutoffDate':"2022-01-01"}
    r = setup_api.runPool(myPool
                  ,poolAssump=("Pool",("Lease", None, ('days', 20) , ('byAnnualRate', 0.0), ("byExtTimes", 2))
                                       ,None
                                       ,None
                                       )
                  ,read=True)
    assert r['PoolConsol']['flow'].index[-1] == '2024-12-15'

@pytest.mark.trigger
def test_trigger_chgBondRate(setup_api):
    withTrigger = test01 & lens.trigger.set({
                    "BeforeDistribution":{
                        "changeBndRt":{"condition":[">=","2021-08-20"]
                                    ,"effects":("changeBondRate", "A1", {"floater":[0.05, "SOFR1Y",-0.02,"MonthEnd"]}, 0.12)
                                    ,"status":False
                                    ,"curable":False}
                    }
                    })
    r = setup_api.run(withTrigger , read=True ,runAssump = [("interest",("SOFR1Y",0.04))])
    print(r['bonds']['A1'].rate.to_list())
    assert r['bonds']['A1'].rate.to_list() == [0.07, 0.12, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02]

@pytest.mark.pool
def test_pool_lease_end(setup_api):
    """ Lease end date """
    myPool = {'assets':[l1],'cutoffDate':"2022-01-01"}
    r = setup_api.runPool(myPool
                  ,poolAssump=("Pool",("Lease", None, ('days', 20) , ('byAnnualRate', 0.0), ("byExtTimes", 2))
                                       ,None
                                       ,None
                                       )
                  ,read=True)
    assert r['PoolConsol']['flow'].index[-1] == '2024-12-15'

    r = setup_api.runPool(myPool
                  ,poolAssump=("Pool",("Lease", None, ('days', 20) , ('byAnnualRate', 0.0), ("earlierOf", "2023-11-15", 2))
                                       ,None
                                       ,None
                                       )
                  ,read=True)
    assert r['PoolConsol']['flow'].index[-1] == '2023-12-15'

    r = setup_api.runPool(myPool
                  ,poolAssump=("Pool",("Lease", None, ('days', 20) , ('byAnnualRate', 0.0), ("laterOf", "2023-11-15", 3))
                                       ,None
                                       ,None
                                       )
                  ,read=True)
    assert r['PoolConsol']['flow'].index[-1] == '2025-12-15'

@pytest.mark.collect
def test_collect_outstanding(setup_api): 
    complete = setup_api.run(test01, read=True,runAssump =[])
    rWithOsPoolFlow = setup_api.run(test01, read=True,runAssump =[("stop","2021-06-15")])

    combined = pd.concat([rWithOsPoolFlow['pool']['flow']['PoolConsol']
                          ,rWithOsPoolFlow['pool_outstanding']['flow']['PoolConsol']])
    eqDataFrame(complete['pool']['flow']['PoolConsol'], combined)

    poolPerf = ("Pool",("Mortgage",{"CDR":0.002},{"CPR":0.001},{"Rate":0.1,"Lag":18},None)
                                 ,None
                                 ,None)

    complete = setup_api.run(test01,poolAssump= poolPerf, read=True,runAssump =[])
    rWithOsPoolFlow = setup_api.run(test01, poolAssump= poolPerf, read=True, runAssump =[("stop","2021-06-15")])
    
    combined = pd.concat([rWithOsPoolFlow['pool']['flow']['PoolConsol']
                          ,rWithOsPoolFlow['pool_outstanding']['flow']['PoolConsol']])
    eqDataFrame(complete['pool']['flow']['PoolConsol'], combined)

    assert rWithOsPoolFlow['pool_outstanding']['flow']['PoolConsol'].shape == (44, 16), "Outstanding pool cashflow should be non empty"
    assert rWithOsPoolFlow['result']['logs'].to_dict(orient="records")[-1]['Comment'].startswith("Outstanding pool cashflow"), "Outstanding pool cashflow should have logs"
    
    assert complete['result']['logs'] is None , "in a complete run, there shouldn't be oustanding pool warning logs"

@pytest.mark.pool
def test_collect_pool_loanlevel_cashflow(setup_api): 
    rAgg = setup_api.run(test04, read=True,runAssump =[])
    rAssetLevel = setup_api.run(test04, read=True,runAssump =[],rtn=["AssetLevelFlow"])

    assert rAgg['pool']['breakdown']['PoolConsol'] == [], "by Default, breakdown should be empty list"
    
    eqDataFrame(rAgg['pool']['flow']['PoolConsol'],(rAssetLevel['pool']['flow']['PoolConsol'])
                ,msg="breakdown should be same with aggregation cashflow")

    combined = (rAssetLevel['pool']['breakdown']['PoolConsol'][1] + rAssetLevel['pool']['breakdown']['PoolConsol'][0]).drop(columns=["WAC"]).round(2)
    eqDataFrame(rAssetLevel['pool']['flow']['PoolConsol'].drop(columns=["WAC"])
                ,combined
                ,msg="breakdown should be same with aggregation cashflow")
    
    poolPerf = ("Pool",("Mortgage",{"CDR":0.002},{"CPR":0.001},{"Rate":0.1,"Lag":18},None)
                                  ,None
                                  ,None)

    rAgg = setup_api.run(test04,poolAssump=poolPerf, read=True,runAssump =[])
    rAssetLevel = setup_api.run(test04,poolAssump=poolPerf, read=True,runAssump =[],rtn=["AssetLevelFlow"])

    eqDataFrameByLens(rAgg, rAssetLevel, lens['pool']['flow']['PoolConsol']
                ,msg="breakdown should be same with aggregation cashflow(with performance)")

    combined2 = (rAssetLevel['pool']['breakdown']['PoolConsol'][1] + rAssetLevel['pool']['breakdown']['PoolConsol'][0]).drop(columns=["WAC"]).round(2)
    eqDataFrame(rAssetLevel['pool']['flow']['PoolConsol'].drop(columns=["WAC"])
                ,combined2
                ,msg="breakdown should be same with aggregation cashflow(with performance)")

@pytest.mark.report
def test_reports(setup_api): 
    """ Test reports on variuos asset class """
    pairs = {"mortgage01": (test01,None)}
    r = {}
    for k, (vd,vp) in pairs.items():
        r[k] = setup_api.run(vd, poolAssump=vp, read=True, runAssump =[("report", {"dates":"MonthEnd"})])

@pytest.mark.revolving
def test_revolving_01(setup_api):
    """ Test revolving pool with collection """
    revol_asset =  ["Mortgage",{
                        "originBalance": 1400, "originRate": ["fix", 0.045], "originTerm": 30, "freq": "Monthly", "type": "Level", "originDate": "2021-02-01",},
                    {"currentBalance": 1400, "currentRate": 0.08, "remainTerm": 30, "status": "current",}, ]    
    r = setup_api.run(test05, read=True, runAssump =[("revolving"
                                                       ,["constant",revol_asset]
                                                       ,("Pool",("Mortgage",None,None,None,None)
                                                                 ,None
                                                                 ,None))]
                      ,rtn=["AssetLevelFlow"])
    revolvingBuyTxn = filterTxn(r['accounts']['acc01'].to_dict(orient="records"),"memo",r".*PurchaseAsset.*")
    assert len(revolvingBuyTxn) == 3, "Should have 3 purchase asset txn"
    
    buyAmts = [ _['change'] for _ in revolvingBuyTxn]
    assert buyAmts == [-302.44,-75.61,-86.76], "Buy amount should be same with revolving asset"

    buy_asset1_flow = r['pool']['breakdown']['PoolConsol'][2]
    buy_asset2_flow = r['pool']['breakdown']['PoolConsol'][3]
    buy_asset3_flow = r['pool']['breakdown']['PoolConsol'][4]
    assert buy_asset1_flow.Principal.sum().round(2) == 302.44
    assert buy_asset2_flow.Principal.sum().round(2) == 75.61
    assert buy_asset3_flow.Principal.sum().round(2) == 86.76

    #breakdown cashflow should tieout with aggregated pool cashflow
    totalPrins = r['pool']['breakdown']['PoolConsol'] & lens.Each().Principal.collect() & lens.Each().modify(lambda x: x.sum())
    assert r['pool']['flow']['PoolConsol'].Principal.sum().round(2) == sum(totalPrins).round(2), "Breakdown cashflow should tieout with aggregated pool cashflow"

@pytest.mark.asset
def test_06(setup_api):
    r = setup_api.run(test06 , read=True , runAssump = [])
    assert r['pool']['flow']['PoolConsol'].Principal.sum() == 2175, "Total principal should be 2175.0"


@pytest.mark.waterfall
def test_limit_01(setup_api):
    formulaPay = \
      ["IfElse",["date","<=","2021-10-20"]
      ,[['payPrin', 'acc01', ['A1'],{"limit":{"formula":("const",30)}}]]
      ,[['payPrin', 'acc01', ['A1']]]
      ]

    test01_ = test01 & lens.waterfall['default'][1].set(formulaPay)
    r = setup_api.run(test01_,read=True)
    assert r['bonds']['A1'][:"2021-10-20"].principal.to_list() == [30.0, 30.0, 30.0, 30.0]
    assert r['bonds']['A1'].loc["2021-11-20"].principal.item() == 75.92

    formulaPay = \
      ["IfElse",["date","<=","2021-10-20"]
      ,[['payPrin', 'acc01', ['A1'],{"limit":{"balPct":0.4}}]]
      ,[['payPrin', 'acc01', ['A1']]]
      ]

    test01_ = test01 & lens.waterfall['default'][1].set(formulaPay)
    r =  setup_api.run(test01_,read=True)
    assert r['bonds']['A1'][:"2021-11-20"].principal.to_list() == [122.01, 30.78, 30.44, 30.58, 76.48]

    formulaPay = ['payPrin', 'acc01', ['A1'],{"limit":{"balCapAmt":75}}]
    
    test01_ = test01 & lens.waterfall['default'][1].set(formulaPay)
    r = setup_api.run(test01_,read=True)
    r['bonds']['A1'].principal.to_list() == [75]*13+[25]

@pytest.mark.waterfall
def test_support_account(setup_api):
    """ Test support account """
    test01_ = test01 & lens.accounts.set((('acc01', {'balance': 0}),('acc02', {'balance': 200})))\
                 & lens.waterfall['default'][0].modify(lambda x: x+[{"support":["account","acc02"]}])
    r =setup_api.run(test01_,read=True
                    ,poolAssump = ("Pool",("Mortgage",{"CDR":0.75},None,None,None)
                                           ,None
                                           ,None))
    assert r['accounts']['acc01'].loc['2023-09-20'].change.item() == -2.56
    assert r['accounts']['acc02'].loc['2023-09-20'].change.item() == -0.13

    test01_ = test01 & lens.accounts.set((('acc01', {'balance': 0}),('acc02', {'balance': 10}),('acc03', {'balance': 50})))\
                 & lens.waterfall['default'][0].modify(lambda x: x+[{"support":["support",("account","acc02"),("account","acc03")]}])
    r = setup_api.run(test01_,read=True
                    ,poolAssump = ("Pool",("Mortgage",{"CDR":0.75},None,None,None)
                                           ,None
                                           ,None)
                  )
    assert r['accounts']['acc01'].loc['2023-09-20'].change.item() == -2.56
    assert r['accounts']['acc02'].loc['2023-09-20'].change.item() == -0.13
    assert r['accounts']['acc02'].loc['2024-01-20'].change.item() == -1.96
    assert r['accounts']['acc03'].loc['2024-01-20'].change.item() == -0.73

@pytest.mark.dates 
def test_dates_preClosing(setup_api):
    preclosingDeal = test01
    pDates = preclosingDeal.dates
    bondNames = preclosingDeal.bonds & lens.Each()[0].collect()
    r = setup_api.run(preclosingDeal,read=True)
    
    # test for preclosing date 
    assert r['pool']['flow']['PoolConsol'].index[0] == pDates['closing']
    assert allEq([ r['bonds'][b].index[0] for b in bondNames ],pDates['firstPay'])
    
@pytest.mark.dates 
def test_dates_current(setup_api):
    currentDeal = test07 
    pDates = currentDeal.dates
    bondNames = currentDeal.bonds & lens.Each()[0].collect()
    r = setup_api.run(currentDeal,read=True)
    # test for current date
    assert r['pool']['flow']['PoolConsol'].index[0] == pDates['collect'][1]
    assert allEq([ r['bonds'][b].index[0] for b in bondNames ],pDates['pay'][1])

@pytest.mark.formula    
def test_formula_01(setup_api):
    
    # test issuance stats
    ## issuance balance 
    ### Balance
    ### Pool Factor
    issueBal = test07.pool['issuanceStat']['IssuanceBalance']
    r = setup_api.run(test07 , read=True , runAssump = [("inspect",("MonthEnd",("poolFactor",)))])
    x = pd.concat([readInspect(r['result']),(r['pool']['flow']['PoolConsol'].Balance / issueBal).rename("bench")],axis=1).sort_index()["2021-06-30":]
    assert all(abs(x['<PoolFactor>'] - x['bench']) < 0.001)
    
    ### cumu default balance - 0
    begDefaultBalance = 500
    test07WithDef = test07 & lens.pool['issuanceStat'].modify(lambda x: tz.assoc(x,'HistoryDefaults',begDefaultBalance))
    r = setup_api.run(test07WithDef , read=True , runAssump = [("inspect",("MonthEnd",("cumPoolDefaultedBalance",)))])
    assert set(r['pool']['flow']['PoolConsol'].CumDefault.to_list()) == {500}, "CumuDefault should be either 0 or 500"
    
    ### cumu default balance - 1
    
    r = setup_api.run(test07WithDef , read=True ,poolAssump=("Pool",("Mortgage",{"CDR":0.1},None,None,None)
                                                                , None
                                                                , None)
                                                , runAssump = [("inspect",("MonthEnd",("cumPoolDefaultedBalance",))
                                                                         ,("MonthEnd",("cumPoolDefaultedRate",)))
                                                               ])
    listCloseByAbs((r['pool']['flow']['PoolConsol'].Default.cumsum() + begDefaultBalance).to_list()
                    , r['pool']['flow']['PoolConsol'].CumDefault.to_list())
    listCloseByAbs((r['pool']['flow']['PoolConsol'].Default.cumsum() + begDefaultBalance)["2021-06-30":].to_list()
                   , readInspect(r['result'])['<CumulativePoolDefaultedBalance>']["2021-06-30":].to_list())
    
    ### by different pool
    
    
    
    
@pytest.mark.dates
def test_dates_custom(setup_api):
    customDeal = test08 
    pDates = customDeal.dates
    bondNames = customDeal.bonds & lens.Each()[0].collect()
    r = setup_api.run(customDeal,read=True)
    # test for custom date
    assert r['pool']['flow']['PoolConsol'].index.to_list() == [pDates['collect'][1]]+pDates['poolFreq'][1:]
    assert allEq([ r['bonds'][b].index.to_list() for b in bondNames ],[pDates['pay'][1]]+pDates['payFreq'][1:])
    
    customDeal = test09
    pDates = customDeal.dates
    bondNames = customDeal.bonds & lens.Each()[0].collect()
    r = setup_api.run(customDeal,read=True)
    # test for custom date
    assert r['pool']['flow']['PoolConsol'].index.to_list() == [pDates['closing']]+pDates['poolFreq'][1:]
    assert allEq([ r['bonds'][b].index.to_list() for b in bondNames ],[pDates['firstPay']]+pDates['payFreq'][1:])
    
@pytest.mark.fees
def test_fee(setup_api):
    r = setup_api.run(test01Fee,read=True)
    fp = -324.6
    sp = -75.40
    assert (fp+sp)*-1 == test01Fee.fees[0][1]['type']['fixFee']
    assert r['accounts']['acc01'].loc["2021-07-26"].change == fp
    assert r['accounts']['acc01'].loc["2021-08-20"].iloc[0].change == sp
    
    
    r = setup_api.run(test02Fee , read=True , runAssump=[])
    feeCashFlow = r['fees']['test_fee'].loc[r['fees']['test_fee'].payment>0,].payment
    assert set(feeCashFlow.to_list()) == {20.0}
    flowDates = ['2021-07-26','2021-10-20','2022-01-20','2022-04-20','2022-07-20','2022-10-20','2023-01-20','2023-04-20','2023-07-20']
    assert feeCashFlow.index.to_list() == flowDates
    
    r = setup_api.run(test03Fee , read=True , runAssump=[]) 
    cmp = pd.concat([r['fees']['test_fee'][['payment']].shift(-1),r['bonds']['A1'][['balance']]/100],axis=1)
    assert all(abs((cmp['payment'] - cmp['balance']).fillna(0))<0.01)
    
    #TODO missing fee type: annualized fee
    
    r = setup_api.run(test05Fee , read=True , runAssump=[])
    assert r['fees']['test_fee'].loc['2021-08-20'].to_list() == [18.85, 81.15, 0.0]
    assert r['fees']['test_fee'].loc['2021-09-20'].to_list() == [0.0, 18.85, 0.0]
    assert r['fees']['test_fee'].loc['2021-12-20'].to_list() == [0.0, 50.0, 0.0]
    
    r = setup_api.run(test06Fee , read=True , runAssump=[])
    assert r['fees']['test_fee'].loc['2021-07-26':"2021-09-20"].payment.to_list() == [50,30,5]
    
    r = setup_api.run(test07Fee , read=True , runAssump=[])
    assert r['fees']['test_fee'].loc["2021-08-20"].payment.item() == 16
    assert r['fees']['test_fee'].loc["2022-08-20"].payment.item() == 8
    
    r = setup_api.run(test08Fee , read=True , runAssump=[]) 
    #pInt = r['pool']['flow']['PoolConsol'].Interest.fillna(0).rename("poolBalance")
    #r['fees']['test_fee'].payment.cumsum()
    #pCumuInt = pInt.cumsum()
    #valid_df = pd.concat([ r['fees']['test_fee'].payment,r['fees']['test_fee'].payment.cumsum(), pInt,pCumuInt,(pCumuInt*0.03).round(3)],axis=1).sort_index()
    #valid_df
    assert r['fees']['test_fee'].payment.to_list()[:8] == [1.67, 0.39, 0.37, 0.36, 0.35,0.33,0.31,0.31,]
    
    # by collection period fee
    r = setup_api.run(test09Fee , read=True , runAssump=[]) 
    assert r['fees']['test_fee'].loc['2021-07-26'].payment.item() == 60
    assert r['fees']['test_fee'].loc['2021-08-20'].payment.item() == 15
    
    # by fee table
    r = setup_api.run(test10Fee , read=True , runAssump=[])
    pBalance = r['pool']['flow']['PoolConsol'].Balance 
    valid_df = pd.concat([ r['fees']['test_fee'], pBalance, pBalance * 0.02],axis=1).sort_index()
    
    assert valid_df.loc["2021-07-26"].payment.item() == 45.0
    assert valid_df.loc["2021-08-20"].payment.item() == 15.0
    assert valid_df.loc["2022-02-20"].payment.item() == 10.0
    assert valid_df.loc["2022-12-20"].payment.item() == 5.0
    
@pytest.mark.waterfall
def test_waterfall_bond(setup_api):
    # pay fee by seq
    #test11Fee
    r = setup_api.run(test11Fee , read=True , runAssump=[])
    seniorTest(r['fees']['fee1'].payment,r['fees']['fee2'].payment)
    
    r = setup_api.run(test2BondsIntBySeq , read=True , runAssump=[])
    assert r['bonds']['A1'].loc['2021-07-26'].interest.item() == 7.82
    assert r['bonds']['A2'].loc['2021-07-26'].interest.item() == 11.78
    
@pytest.mark.account
def test_account(setup_api):
    r = setup_api.run(threeAccounts , read=True , runAssump=[])
    
    assert r['accounts']['acc03'].change.to_list() == [-10,-10,-10]
    assert r['accounts']['acc02'].change.to_list() == [-10] * 5
    assert r['accounts']['acc01'].loc['2021-08-20'].change.to_list()[:2] == [10.0]*2 
    
@pytest.mark.sensitivity
def test_sensitivity_01(setup_api):
    # senstivity on structs
    test02 = test01 & lens.bonds.Each()[1]['balance'].modify(lambda x: 0.9*x)
    dealMap = {
        "Normal":test01,"Shrink":test02
    }
    
    rs = setup_api.runStructs(dealMap, read=True)
    
    assert rs.keys() == {"Normal","Shrink"}, "sensitivity run should have two results"
    
    assert rs['Shrink']['bonds']['A1'].principal.sum().item() == 900
    assert closeTo(rs['Normal']['bonds']['A1'].principal.sum().item() ,1000)


@pytest.mark.sensitivity
def test_sensitivity_02(setup_api):
    # senstivity on pool assump 
    myAssumption = ("Pool",("Mortgage",{"CDR":0.01},None,None,None)
                                ,None
                                ,None)

    myAssumption2 = ("Pool",("Mortgage",None,{"CPR":0.01},None,None)
                                    ,None
                                    ,None)
    
    rs = setup_api.runByScenarios(test01
                                ,poolAssump={"withCdr":myAssumption
                                            ,"withCpr":myAssumption2}
                                ,read=True)
    
    assert rs.keys() == {"withCdr","withCpr"}
    
    assert rs['withCdr']['pool']['flow']['PoolConsol'].Default.sum().item() > 0
    assert rs['withCdr']['pool']['flow']['PoolConsol'].Prepayment.sum().item() == 0
    
    assert rs['withCpr']['pool']['flow']['PoolConsol'].Prepayment.sum().item() > 0
    assert rs['withCpr']['pool']['flow']['PoolConsol'].Default.sum().item() == 0
    

@pytest.mark.sensitivity
def test_sensitivity_03(setup_api):
    # senstivity on run assumption 
    runAssumption01 = []
    runAssumption02 = [("call", ("if", ["date", ">", "2022-10-01"]))]
    
    rAssump = {
        "r0":runAssumption01
        ,"r1":runAssumption02
    }

    rs = setup_api.runByDealScenarios(test01
                                    ,runAssump=rAssump
                                    ,read=True)
    
    assert rs.keys() == {"r0","r1"}
    
    assert rs['r1']['result']['status'].loc[2].to_list() == ['2022-10-20', '', 'DealEnd', 'Clean Up']

@pytest.mark.sensitivity
def test_sensitivity_04(setup_api):
    # senstivity on combo  
    test02 = test01 & lens.bonds.Each()[1]['balance'].modify(lambda x: 0.9*x)
    dealMap = {
        "Normal":test01,"Shrink":test02
    }
    
    myAssumption = ("Pool",("Mortgage",{"CDR":0.01},None,None,None)
                            ,None
                            ,None)

    myAssumption2 = ("Pool",("Mortgage",None,{"CPR":0.01},None,None)
                                    ,None
                                    ,None)
    
    runAssumption01 = []
    runAssumption02 = [("call", ("if", ["date", ">", "2022-10-01"]))]
    
    rAssump = {
        "r0":runAssumption01
        ,"r1":runAssumption02
    }        
    rs = setup_api.runByCombo(dealMap
                        ,poolAssump={"withCdr":myAssumption
                                    ,"withCpr":myAssumption2}
                        ,runAssump = rAssump
                        ,read=True)
    
    assert len(rs.keys())==8