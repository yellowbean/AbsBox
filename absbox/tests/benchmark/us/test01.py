from absbox.local.generic import Generic

test01 = Generic(
    "TEST01"
    ,{"cutoff":"2021-03-01","closing":"2021-06-15","firstPay":"2021-07-26"
     ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthEnd","stated":"2030-01-01"}
    ,{'breakdown':[["Mortgage"
        ,{"originBalance":120,"originRate":["Fixed",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":120
          ,"currentRate":0.08
          ,"remainTerm":20
          ,"status":"Current"}]]}
    ,(("acc01",{"balance":0}),)
    ,(("A1",{"balance":100
             ,"rate":0.07
             ,"originBalance":100
             ,"originRate":0.07
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.08}
             ,"bondType":{"Sequential":None}})
      ,("B",{"balance":20
             ,"rate":0.0
             ,"originBalance":100
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