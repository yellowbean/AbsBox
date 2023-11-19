from absbox import API
from absbox import Generic


asset = ["AdjustRateMortgage"
        ,{"originBalance":73_875.00
          ,"originRate":["floater",0.04,{"index":"USCMT1Y"
                                        ,"spread":0.01
                                        ,"reset":"YearFirst"}]
          ,"originTerm":360
          ,"freq":"Monthly","type":"Level","originDate":"1999-05-01"
          ,"arm":{"initPeriod":2,"firstCap":0.01,"periodicCap":0.01,"lifeCap":0.09}}
          ,{"currentBalance":20_788.41
          ,"currentRate":0.0215
          ,"remainTerm":77
          ,"status":"current"}]

GNMA_36208ALG4 = Generic(
    "820146/36208ALG4/G2-Custom AR"
    ,{"collect":["2023-05-01","2023-05-31"]
        ,"pay":["2023-05-26","2023-06-28"]
        ,"stated":"2070-01-01"
        ,"poolFreq":"MonthEnd"
        ,"payFreq":["DayOfMonth",20]}
    ,{'assets':[asset]
      ,'issuanceStat':{"IssuanceBalance":10000}}
    ,(("acc01",{"balance":0}),)
    ,(("A1",{"balance":20_899.37
             ,"rate":0.025
             ,"originBalance":1_553_836.00
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"floater": [0.07,"USCMT1Y",0.01,"YearFirst"],"dayCount":"DC_30_360_US"}
             ,"bondType":{"Sequential":None}
             ,"lastAccrueDate":"2023-04-30"})
      ,)
    ,(("Ginnie_Mae_guaranty",
       {"type":{"annualPctFee":[("poolBalance",),0.0006]}
       ,"feeDueDate":"2023-04-26"}),
      ("service_fee",
       {"type":{"annualPctFee":[("poolBalance",)
                                ,("Max"
                                  ,("substract",("poolWaRate",),("bondRate","A1"))
                                  ,("constant",0))]}
       ,"feeDueDate":"2023-04-26"}))
    ,{"amortizing":[
         ["calcFee","Ginnie_Mae_guaranty","service_fee"]
         ,["payFee","acc01",['Ginnie_Mae_guaranty',"service_fee"]]
         ,["payInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]]
      ,"endOfCollection":[
          ["liqSupport","Ginnie_Mae","account","acc01"
              ,{"formula": 
                ("floorWithZero"
                ,("substract",("cumPoolDefaultedBalance",)
                            ,("liqBalance","Ginnie_Mae")))}
              ]
          ,["calcInt","A1"]]}
    ,[["CollectedInterest","acc01"]
      ,["CollectedPrincipal","acc01"]
      ,["CollectedPrepayment","acc01"]
      ,["CollectedRecoveries","acc01"]]
    ,{"Ginnie_Mae":{"type":"Unlimited","start":"2023-05-26"}}
    ,None)


# r = localAPI.run(GNMA_36208ALG4
#                 ,runAssump = [("inspect",("MonthEnd",("cumPoolDefaultedBalance",))
#                                          ,("MonthEnd",("liqBalance","Ginnie_Mae")))
#                               ,("interest",("USCMT1Y",0.0468))]
#                 ,poolAssump = ("Pool"
#                               ,("Mortgage",{"CDR":0.005},None,{"Rate":0.3,"Lag":4},None)
#                               ,None
#                               ,None)
#                 ,read=True)

# Inspect cumulative defaulted balance
# r['result']['inspect']['<CumulativePoolDefaultedBalance>']

# Inspect credit provided by Ginnie Mae
# r['result']['inspect']['<LiqBalance:Ginnie_Mae>']

# the cash deposited to SPV in account `acc01`
# r['accounts']['acc01'][r['accounts']['acc01']["memo"]=="<Support:Ginnie_Mae>"]


