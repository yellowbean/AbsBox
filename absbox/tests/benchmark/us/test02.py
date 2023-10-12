from absbox.local.generic import Generic

test01 = Generic(
    "Multiple Waterfall"
    ,{"cutoff":"2021-03-01","closing":"2021-06-15","firstPay":"2021-07-26"
     ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthEnd","stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":20
          ,"status":"current"}]]
      ,'issuanceStat':{'IssuanceBalance':2200}
      }
    ,(("acc01",{"balance":0}),)
    ,(("A1",{"balance":500
             ,"rate":0.07
             ,"originBalance":500
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.08}
             ,"bondType":{"Sequential":None}})
      ,("A2",{"balance":500
             ,"rate":0.07
             ,"originBalance":500
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
    ,(("trusteeFee",{"type":{"fixFee":30}}),)
    ,{"amortizing":[
         ["payFee","acc01",['trusteeFee']]
         ,["accrueAndPayInt","acc01",["A1","A2"]]
         ,["payPrin","acc01",["A1","A2"]]
         ,["payPrin","acc01",["B"]]
         ,["payPrinResidual","acc01",["B"]]]
      ,"cleanUp":[]
      ,"endOfCollection":[]       # execute when collect money from pool
      ,("amortizing","defaulted"):[]   #execute when deal is `defaulted`
      ,("amortizing","accelerated"):[ #execute when deal is `accelerated`
         ["payFee","acc01",['trusteeFee']]
         ,["accrueAndPayInt","acc01",["A1","A2"]]
         ,["payPrin","acc01",["A1"]] 
         ,["payPrin","acc01",["A2"]]
         ,["payPrin","acc01",["B"]]
         ,["payPrinResidual","acc01",["B"]]
      ] 
      }
    ,[["CollectedInterest","acc01"]
      ,["CollectedPrincipal","acc01"]
      ,["CollectedPrepayment","acc01"]
      ,["CollectedRecoveries","acc01"]]
    ,None
    ,None
    ,None
    ,{"AfterCollect":{
        "DefaultTrigger": 
         {"condition":[("cumPoolDefaultedRate",),">",0.05]
          ,"effects":("newStatus","Accelerated")
          ,"status":False
          ,"curable":False}}}
    ,("PreClosing","Amortizing")
)

