flow = [
  ["2022-10-28",200.0,100]
  ,["2022-11-28",200.0,100]
  ,["2022-12-28",200.0,100]
  ,["2023-01-28",200.0,100]
  ,["2023-02-28",200.0,100]
  ,["2023-03-28",200.0,100]
  ,["2023-04-28",200.0,100]
  ,["2023-05-28",200.0,100]
  ,["2023-06-28",200.0,100]
  ,["2023-07-28",200.0,100]
  ,["2023-08-28",200.0,100]    
]

deal_data = {
    "name":"Default Amount to Schedule Flow"
    ,"dates":{"cutoff":"2021-06-01"
              ,"closing":"2021-07-15"
              ,"firstPay":"2021-08-26"
              ,"payFreq":["DayOfMonth",20]
              ,"poolFreq":"MonthEnd"
              ,"stated":"2030-01-01"}
    ,"pool":{'assets':[
        ["ProjectedCashflow", 2200, "2021-06-01", flow, "MonthEnd"]
    ]}
    ,"accounts":{"acc01":{"balance":0}}
    ,"bonds":{"A1":{"balance":1000
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
                     ,"bondType":{"Equity":None}}}
    ,"fees":{"trusteeFee":{"type":{"fixFee":30}}}
    ,"collect":[["CollectedInterest","acc01"]
              ,["CollectedPrincipal","acc01"]
              ,["CollectedPrepayment","acc01"]
              ,["CollectedRecoveries","acc01"]]
    ,"waterfall":{"Amortizing":[
         ["payFee","acc01",['trusteeFee']]
         ,["calcInt","A1"]
        
         ,["payInt","acc01",["A1"]]
        
         ,["payPrin","acc01",["A1"]]
         ,["payPrin","acc01",["B"]]
         ,["payPrinResidual","acc01",["B"]]
     ]}
    ,"status":("PreClosing","Amortizing")
}

if __name__ == "__main__":
    from absbox import API,mkDeal
    localAPI = API("http://localhost:8081",check=False)

    deal = mkDeal(deal_data)

    r = localAPI.run(deal
                    ,poolAssump = ("Pool",("Mortgage"
                                           ,{"ByAmount":(300,[0.1,0.2,0.6,0.1])}
                                           ,None
                                           ,{"Rate":0.7,"Lag":10}
                                           ,None)
                                   ,None
                                   ,None)
                    ,runAssump = None
                    ,read=True)

    r['pool']['flow']
    
