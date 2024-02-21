deal_data = {
    "name":"Sample with Interest Swap"
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
                          ,"status":"current"}]]
            #,'issuanceStat':{"HistoryDefaults":5}
            }
    ,"accounts":{"acc01":{"balance":0}}
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
    ,"collect":[["CollectedInterest","acc01"]
              ,["CollectedPrincipal","acc01"]
              ,["CollectedRecoveries","acc01"]
              ,["CollectedPrepayment",[0.5,"acc01"]]]
    ,"waterfall":{"Amortizing":[
         ["payFee","acc01",['trusteeFee']]         
         ,["accrueAndPayInt","acc01",["A1"]]
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["bookBy",["formula","myLedger"
                     ,"Credit",("constant",100)]]
         ,["payPrinResidual","acc01",["B"]]
     ]}
    ,"status":("PreClosing","Amortizing")
    ,"ledgers":{"myLedger":{"balance":100}}
}

from absbox import API, mkDeal
localAPI = API("http://localhost:8081",check=False)

deal = mkDeal(deal_data)

r = localAPI.run(deal
                 ,poolAssump = ("Pool"
                                ,("Mortgage"
                                 ,{"CDR":0.02} ,{"CPR":0.02}, None, None)
                                 ,None
                                 ,None)
                 ,runAssump = [("inspect",["MonthEnd",("ledgerBalance","myLedger")])]
                 ,read=True)

r['ledgers']['myLedger']

r['result']['inspect']