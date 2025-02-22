from absbox import Generic
import toolz as tz
from lenses import lens


test01 = Generic(
    "TEST01- preclosing"
    ,{"cutoff":"2021-03-01","closing":"2021-04-15","firstPay":"2021-07-26","firstCollect":"2021-04-28"
     ,"payFreq":["DayOfMonth",20]
     ,"poolFreq":"MonthEnd"
     ,"stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":30
          ,"status":"current"}]]}
    ,(("acc01",{"balance":0}),)
    ,(("A1",{"balance":1000
             ,"rate":0.07
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.08}
             ,"bondType":{"Sequential":None}})
      ,("B",{"balance":1000
             ,"rate":0.0
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.00}
             ,"bondType":{"Equity":None}
             }))
    ,tuple()
    ,{"default":[
         ["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payIntResidual","acc01","B"]
     ]
     }
    ,[["CollectedInterest","acc01"]
      ,["CollectedPrincipal","acc01"]
      ,["CollectedPrepayment","acc01"]
      ,["CollectedRecoveries","acc01"]]
    ,None
    ,None
    ,None
    ,None
    ,("PreClosing","Amortizing")
    )


test02 = Generic(
    "TEST02- Amortizing Deal"
    ,{"lastCollect":"2021-03-01","lastPay":"2021-04-15"
      ,"nextPay":"2021-07-26","nextCollect":"2021-04-28"
     ,"payFreq":["DayOfMonth",20] ,"poolFreq":"MonthEnd"
     ,"stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":30
          ,"status":"current"}]]}
    ,(("acc01",{"balance":0}),)
    ,(("A1",{"balance":1000
             ,"rate":0.07
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.08}
             ,"bondType":{"Sequential":None}})
      ,("B",{"balance":1000
             ,"rate":0.0
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.00}
             ,"bondType":{"Equity":None}
             }))
    ,tuple()
    ,{"default":[
         ["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payIntResidual","acc01","B"]
     ],
     }
    ,[["CollectedInterest","acc01"]
      ,["CollectedPrincipal","acc01"]
      ,["CollectedPrepayment","acc01"]
      ,["CollectedRecoveries","acc01"]]
    ,None
    ,None
    ,None
    ,None
    ,"Amortizing"
    )

Irr01 = Generic(
    "IRR Case"
    ,{"cutoff":"2021-03-01","closing":"2021-04-01","firstPay":"2021-06-20"
     ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthFirst","stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":20
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
             ,"startDate":"2021-04-01"
             ,"rateType":{"Fixed":0.08}
             ,"bondType":{"Sequential":None}})
      ,("B",{"balance":1000
             ,"rate":0.0
             ,"originBalance":1000
             ,"originRate":0.07
             ,"startDate":"2021-04-01"
             ,"rateType":{"Fixed":0.00}
             ,"bondType":{"Equity":None}
             }))
    ,tuple()
    ,{"amortizing":[
         ["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payIntResidual","acc01","B"]
     ]}
    ,[["CollectedInterest","acc01"]
      ,["CollectedPrincipal","acc01"]
      ,["CollectedPrepayment","acc01"]
      ,["CollectedRecoveries","acc01"]]
    ,None
    ,None
    ,None
    ,None
    ,("PreClosing","Amortizing")
    )