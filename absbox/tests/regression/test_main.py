import pandas as pd
from lenses import lens
import toolz as tz
import pytest
import re, math, json
from pathlib import Path
from collections import Counter

from .deals import *
from .assets import *

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



@pytest.fixture
def setup_api():
    with config_file_path.open('r') as config_file:
        config = json.load(config_file)
    api = API(config['test_server'], check=False, lang='english')
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

def ppyRate(mflow):
    return [ round(_, 3) for _ in  (mflow.Prepayment / mflow.Balance.shift(1)).to_list() ]

def defRate(mflow):
    return [ round(_, 3) for _ in  (mflow.Default / mflow.Balance.shift(1)).to_list() ]


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
                    ,runAssump = [("pricing",{"IRR":{"B":("holding",[("2021-04-01",-500)],500)}})]
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
    
    closeTo(r3['pricing']['summary'].loc["A1"].IRR, 0.12248, r=6)


@pytest.mark.analytics
def test_rootfind_stressppy(setup_api):
    poolPerf = ("Pool",("Mortgage",{"CDR":0.002},{"CPR":0.001},{"Rate":0.1,"Lag":18},None)
                                 ,None
                                 ,None)
    pricing = ("pricing",{"IRR":{"B":("holding",[("2021-04-15",-1000)],1000)}})
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
    pricing = ("pricing",{"IRR":{"B":("holding",[("2021-04-15",-1000)],1000)}})
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
    assert r['bonds']["A1"].loc["2021-07-26":"2021-11-20"].balance.to_list() == [800.0, 750.0, 694.21, 617.05, 539.56] 


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
    rWithOsPoolFlow = setup_api.run(test01,poolAssump= poolPerf, read=True,runAssump =[("stop","2021-06-15")])
    
    combined = pd.concat([rWithOsPoolFlow['pool']['flow']['PoolConsol']
                          ,rWithOsPoolFlow['pool_outstanding']['flow']['PoolConsol']])
    eqDataFrame(complete['pool']['flow']['PoolConsol'], combined)

    assert rWithOsPoolFlow['pool_outstanding']['flow']['PoolConsol'].shape == (44, 16), "Outstanding pool cashflow should be non empty"
    assert rWithOsPoolFlow['result']['logs'].to_dict(orient="records")[-1]['Comment'].startswith("Oustanding pool cashflow hasn't been collected yet"), "Outstanding pool cashflow should have logs"
    
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
    # combined = pd.concat([rWithOsPoolFlow['pool']['flow']['PoolConsol']
    #                       ,rWithOsPoolFlow['pool_outstanding']['flow']['PoolConsol']])
    # eqDataFrame(complete['pool']['flow']['PoolConsol'], combined)

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


# @pytest.mark.analytics
# def test_rootfinder_by_formula(setup_api):
#     poolPerf = ("Pool",("Mortgage",{"CDR":0.002},{"CPR":0.001},{"Rate":0.1,"Lag":18},None)
#                                  ,None
#                                  ,None)
#     r = setup_api.runRootFinder(test01, poolPerf ,[]
#         ,("stressPrepayment",("byFormula", ("bondTxnAmt", "<PayInt:B>","B") , 500))
#     )
#     assert r[1][1]['PoolLevel'][0]['MortgageAssump'][1] == {'PrepaymentCPR': 0.38642105474696914 } 

