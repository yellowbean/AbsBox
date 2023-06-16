from absbox.local.generic import Generic
from absbox import API


localAPI = API("https://absbox.org/api/latest")

test01 = Generic(
    "TEST01"
    ,{"cutoff":"2021-03-01","closing":"2021-06-15","firstPay":"2021-07-26"
     ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthEnd","stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":20
          ,"status":"current"}]]}
    ,(("acc01",{"balance":0}),)
    ,(("A1",{"balance":1000
             ,"rate":0.07
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"floater":["SOFR1Y",0.01,"QuarterEnd"]}
             ,"bondType":{"Sequential":None}})
      ,("B",{"balance":1000
             ,"rate":0.0
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.00}
             ,"bondType":{"Equity":None}
             }))
    ,(("trusteeFee",{"type":{"fixFee":30}}),)
    ,{"amortizing":[
         ["payFee",["acc01"],['trusteeFee']]
         ,["payInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payResidual","acc01","B"]
     ]}
    ,[["CollectedInterest","acc01"]
      ,["CollectedPrincipal","acc01"]
      ,["CollectedPrepayment","acc01"]
      ,["CollectedRecoveries","acc01"]]
    ,None
    ,None)


r = localAPI.run(test01,assumptions=[{"Rate":["SOFR1Y"
                                              ,["2021-01-01",0.03]
                                              ,["2022-01-01",0.05]
                                             ,["2022-08-01",0.06]]}])
r['bonds']['A1']    