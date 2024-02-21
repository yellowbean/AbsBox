deal_data = {
    "name":"AggRule by condition"
    ,"dates":{"cutoff":"2021-06-01"
              ,"closing":"2021-07-15"
              ,"firstPay":"2021-08-26"
              ,"payFreq":["DayOfMonth",20]
              ,"poolFreq":"MonthEnd"
              ,"stated":"2030-01-01"}
    ,"pool":{'assets':[["Mortgage"
                        ,{"originBalance":2400,"originRate":["fix",0.045],"originTerm":30
                          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
                          ,{"currentBalance":2400
                          ,"currentRate":0.08
                          ,"remainTerm":30
                          ,"status":"current"}]]}
    ,"accounts":{"prinAcc":{"balance":0},"intAcc":{"balance":0}}
    ,"bonds":{"A1":{"balance":800
                 ,"rate":0.07
                 ,"originBalance":800
                 ,"originRate":0.07
                 ,"startDate":"2020-01-03"
                 ,"rateType":{"Fixed":0.08}
                 ,"bondType":{"Sequential":None}}
             ,"B":{"balance":1000
                     ,"rate":0.0
                     ,"originBalance":1000
                     ,"originRate":0.07
                     ,"startDate":"2020-01-03"
                     ,"rateType":{"Fixed":0.00}
                     ,"bondType":{"Equity":None}}}
    ,"fees":{"trusteeFee":{"type":{"fixFee":30}}}
    ,"collect":[["CollectedInterest","intAcc"]
               ,["CollectedPrincipal","prinAcc"]
               ,["CollectedRecoveries","prinAcc"]
               ,["CollectedPrepayment","prinAcc"]]
    ,"waterfall":{"default":[
         ["If",["status", "Defaulted"]
              ,["transfer","intAcc","prinAcc"] ]
         ,["payFee","intAcc",['trusteeFee']]         
         ,["accrueAndPayInt","intAcc",["A1"]]
         ,["payPrin","prinAcc",["A1"]]
         ,["payPrin","prinAcc",["B"]]
         ,["payPrinResidual","prinAcc",["B"]]
     ]}
    ,"status":("PreClosing","Amortizing")
}

from absbox import API, mkDeal
localAPI = API("http://localhost:8081", check=False)

trigger = {
    "AfterCollect":
      {"poolDef":
        {"condition":[("cumPoolDefaultedBalance",),">",20]
        ,"effects":("newStatus","Defaulted")
        ,"status":False
        ,"curable":False}
      }
}

deal = mkDeal(deal_data | {"triggers":trigger} )

r = localAPI.run(deal
                 ,poolAssump = ("Pool"
                                ,("Mortgage"
                                 ,{"CDR":0.02} ,{"CPR":0.02}, None, None)
                                 ,None
                                 ,None)
                 ,runAssump = []
                 ,read=True)

#r['accounts']['intAcc']