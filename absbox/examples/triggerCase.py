from ..local.generic import Generic

defautlRateTrigger = {"defaultRateTrigger": 
                        {"condition":[("cumPoolDefaultedRate",),">", 0.05]
                        ,"effects":("newStatus","Accelerated")
                        ,"status":False
                        ,"curable":False}}


trigger01 = Generic(
    "Trigger_Default:01"
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
    ,{"AfterCollect": defautlRateTrigger}
    ,("PreClosing","Amortizing")
    )

trigger02 = Generic(
    "Trigger_ongoing_Default:02"
    ,{"collect":["2021-10-01","2021-11-01"]
      ,"pay":["2021-09-20","2021-10-20"]
      ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthFirst","stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":20
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":20
          ,"status":"current"}]]
      ,'issuanceStat':{"HistoryDefaults":50,"IssuanceBalance":1500}}
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
    ,{"AfterCollect": defautlRateTrigger}
    ,"Amortizing"
    )




defautlRollingRateTrigger = {"defaultRateTrigger": 
                              {"condition":[("avg"
                                              , ("cumPoolDefaultedRate",)
                                              , ("cumPoolDefaultedRateTill",-1,)
                                              , ("cumPoolDefaultedRateTill",-2,)
                                              ),">", 0.05]
                              ,"effects":("newStatus","Accelerated")
                              ,"status":False
                              ,"curable":False}}



trigger03 = Generic(
    "Trigger_rolling_Default rate:03"
    ,{"collect":["2021-10-01","2021-11-01"]
      ,"pay":["2021-09-20","2021-10-20"]
      ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthFirst","stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":20
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":20
          ,"status":"current"}]]
      ,'issuanceStat':{"HistoryDefaults":50,"IssuanceBalance":1500}}
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
    ,{"AfterCollect": defautlRollingRateTrigger}
    ,"Amortizing"
    )


trigger04 = Generic(
    "Trigger with waterfall action"
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
    ,{
        "AfterCollect":
          {"poolDef":
            {"condition":[("cumPoolDefaultedBalance",),">",20]
            ,"effects":("actions"
                        ,["calcInt", "A1"]
                        ,["payInt","acc01",["A1"]]
                        )
            ,"status":False
            ,"curable":False}
          }}
    ,("PreClosing","Amortizing")
    )