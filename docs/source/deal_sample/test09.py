from absbox import Generic

fm = {"formula": 
        ("substract",("poolBalance",)
                    ,("factor",("poolBalance",), 0.99))}

test01 = Generic(
    "TEST01"
    ,{"cutoff":"2021-03-01","closing":"2021-06-15","firstPay":"2021-07-26"
     ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthEnd","stated":"2030-01-01"}
    ,{'assets':[
        ["Mortgage"
        ,{"originBalance":120,"originRate":["fix",0.045],"originTerm":70
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":200
          ,"currentRate":0.08
          ,"remainTerm":60
          ,"borrowerNum":1
          ,"status":"current"}]]}
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
    ,(("trusteeFee",{"type":{"fixFee":30}})
      ,("borrowerFee",{"type":{"numFee":[["DayOfMonth",20],("borrowerNumber",),1]}}))
    ,{"amortizing":[
          ["calcFee",'borrowerFee']
         ,["payFee","acc01",['borrowerFee']]
         ,["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"],fm]
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

from absbox import API

#localAPI = API("<url to calculation engine>",'english')

r = localAPI.run(test01,
                 runAssump=[("inspect",(["DayOfMonth",20],fm['formula']))],
                 read=True)

