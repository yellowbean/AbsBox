from absbox import API


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

from absbox.local.generic import Generic

GNMA_36208ALG4 = Generic(
    "820146/36208ALG4/G2-Custom AR"
    ,{"collect":["2023-05-01","2023-05-31"]
        ,"pay":["2023-05-26","2023-06-28"]
        ,"stated":"2070-01-01"
        ,"poolFreq":"MonthEnd"
        ,"payFreq":["DayOfMonth",20]}
    ,{'assets':[asset]}
    ,(("acc01",{"balance":0}),)
    ,(("A1",{"balance":20_899.37
             ,"rate":0.025
             ,"originBalance":1_553_836.00
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"floater": ["USCMT1Y",0.01,"YearFirst"],"dayCount":"DC_30_360_US"}
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
       ,"feeDueDate":"2023-04-26"})
     )
    ,{"amortizing":[
         ["calcFee","Ginnie_Mae_guaranty","service_fee"]
         ,["payFee",["acc01"],['Ginnie_Mae_guaranty',"service_fee"]]
         ,["payInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]]
      ,"endOfCollection":[
          ["calcInt","A1"]
      ]}
    ,[["CollectedInterest","acc01"]
      ,["CollectedPrincipal","acc01"]
      ,["CollectedPrepayment","acc01"]
      ,["CollectedRecoveries","acc01"]]
    ,None
    ,None)

if __name__ == "__main__":
    localAPI = API("http://localhost:8081",lang='english')
    r = localAPI.run(GNMA_36208ALG4
                    ,assumptions = [{"Rate":["USCMT1Y",0.0468]}]
                    ,read=True)