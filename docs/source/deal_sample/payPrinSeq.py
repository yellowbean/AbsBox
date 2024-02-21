from absbox import Generic

test01 = Generic(
    "Pay Prin Seq"
    ,{"collect":["2022-05-01","2022-06-01"] 
      ,"pay":["2022-06-15","2022-07-15"] # next distribution date
      ,"payFreq":["DayOfMonth",20]
      ,"poolFreq":"MonthEnd"
      ,"stated":"2030-01-01"}
    ,{'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":20
          ,"status":"current"}]]
      ,'issuanceStat':{"IssuanceBalance":10000}
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
             ,"originRate":0.00
             ,"startDate":"2020-01-03"
             ,"rateType":{"Fixed":0.00}
             ,"bondType":{"Equity":None}
             }))
    ,(("trusteeFee",{"type":{"fixFee":30}}),)
    ,{"amortizing":[
         ["payFee","acc01",['trusteeFee']]
         ,["accrueAndPayInt","acc01",["A1","A2"]]
         #,["payPrinBySeq","acc01",["A1","A2"]]
         ,["payPrinBySeq","acc01",["A1","A2"],{"limit":{"formula":("constant",100)}}]
         ,["payPrin","acc01",["B"]]
         ,["payIntResidual","acc01","B"]
     ]}
    ,[["CollectedCash","acc01"]]
    ,None
    ,None
    ,None
    ,None
    ,"Amortizing"
    )