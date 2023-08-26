from absbox.local.china import *
from absbox.local.generic import * 
from absbox.local.component import * 
from absbox.local.util import * 



def mkDeal(x:dict):
    name = getValWithKs(x, ['name', "名称", "comment", '备注'], defaultReturn="")
    dates = getValWithKs(x, ['dates', "date", "日期"])
    accs = list((accName,acc) for accName,acc in getValWithKs(x, ['accounts', "account", "账户", "帐户"]).items())
    
    fees = list((fn,fv|{"name":fn,"名称":fn})
                for (fn,fv) in getValWithKs(x
                                            , ['expense', 'expenses', 'fee', "fees", "费用"]).items())
    
    pool = getValWithKs(x, ['pool', "collateral", "资产池"])
    # _assets = [mkAsset(x) for x in getValWithKs(_pool
    #                                             , ['assets', 'loans', 'mortgages', "清单", "资产清单"])]
    # _asOfDate = getValWithKs(_pool, ["asOfDate", "asofDate", "封包日"])
    # _issuanceStat = readIssuance(_pool)
    # _futureCf = mkCf(getValWithKs(_pool,["归集表","现金流归集表","projected","cashflow"],defaultReturn=[]))

    bonds = list((bn,bo)
                for bn,bo in getValWithKs(x
                                         , ['bond', "bonds", "notes", "债券", "支持证券"]).items())
                      
    waterfall = getValWithKs(x, ['waterfall', "现金流分配", "分配规则"])
    
    collection = getValWithKs(x,['collect','colleciton', 'collectionRule', 'aggregation','归集规则','归集'])
    liqFacility = getValWithKs(x, ['liqFacility', 'liqProvider', "insurance"
                                  ,"cashAdvance", "liquidity", "流动性支持"
                                  , "流动性提供方", "增信方", "担保"], defaultReturn=None)
    
    rateSwap = getValWithKs(x, ['rateSwap', "IRSwap", "利率互换"])
    
    currencySwap = None  #TODO 
    
    if (_t:=getValWithKs(x ,['trigger', "triggers", "事件", "触发事件"])):
        trigger = renameKs2(_t, chinaDealCycle|englishDealCycle)
    else:
        trigger = None

    #trigger = renameKs2(getValWithKs(x ,['trigger', "triggers", "事件", "触发事件"]) 
    #                    , chinaDealCycle|englishDealCycle)
    
    status = getValWithKs(x, ['status', 'stage', "状态", "阶段"], defaultReturn="Amortizing")
    
    custom = getValWithKs(x, ['custom', "自定义"])
    
    ledgers = getValWithKs(x, ['ledger', "ledgers", "科目"])
    
    deal = Generic(
        name
        ,dates 
        ,pool
        ,accs
        ,bonds
        ,fees
        ,waterfall
        ,collection
        ,liqFacility
        ,rateSwap
        ,currencySwap
        ,trigger
        ,status
        ,custom
        ,ledgers
    )

    return deal