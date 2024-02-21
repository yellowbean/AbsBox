from absbox import API,mkDeal,setDealsBy,prodDealsBy,Generic,SPV
from lenses import lens

name = "TEST01"
dates = {"cutoff":"2021-03-01","closing":"2021-06-15","firstPay":"2021-07-26"
    ,"payFreq":["DayOfMonth",20],"poolFreq":"MonthEnd","stated":"2030-01-01"}
pool = {'assets':[["Mortgage"
        ,{"originBalance":2200,"originRate":["fix",0.045],"originTerm":30
          ,"freq":"Monthly","type":"Level","originDate":"2021-02-01"}
          ,{"currentBalance":2200
          ,"currentRate":0.08
          ,"remainTerm":20
          ,"status":"current"}]]}
accounts = {"acc01":{"balance":0}}
bonds = {"A1":{"balance":1000
            ,"rate":0.07
            ,"originBalance":1000
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
            ,"bondType":{"Equity":None}
            }}

waterfall = {"amortizing":[
                ["accrueAndPayInt","acc01",["A1"]]
                ,["payPrin","acc01",["A1"]]
                ,["payPrin","acc01",["B"]]
                ,["payPrinResidual","acc01",["B"]]
            ]}
collects = [["CollectedInterest","acc01"]
            ,["CollectedPrincipal","acc01"]
            ,["CollectedPrepayment","acc01"]
            ,["CollectedRecoveries","acc01"]]

deal_data = {
    "name":name
    ,"dates":dates
    ,"pool":pool
    ,"accounts":accounts
    ,"bonds":bonds
    ,"waterfall":waterfall
    ,"collect":collects
    ,"status":"Revolving"
}

d = mkDeal(deal_data)

## build combination of closing dates and bond A rates..
prodDealsBy(d
            ,(lens.dates['closing'],["2021-06-15","2021-08-15"])
            ,(lens.bonds[0][1]["rate"],[0.06,0.075])
           )

## use init to avoid duplicate key typing
prodDealsBy(d
            ,(lens['closing'],["2021-06-15","2021-08-15"])
            ,(lens['firstPay'],["2021-07-15","2021-09-15"])
            ,init=lens.dates
           )