from absbox.local.china import SPV

test01 = SPV(
    "ABCD Case"
    ,{"封包日":"2021-03-31","起息日":"2021-06-15","首次兑付日":"2021-07-26"
      ,"法定到期日":"2060-12-01","收款频率":"月末","付款频率":["每月",26]}
    ,{'清单':[["按揭贷款"
        ,{"放款金额":120,"放款利率":["固定",0.07],"初始期限":30
          ,"频率":"每月","类型":"等额本金","放款日":"2021-02-01"}
          ,{"当前余额":130
          ,"当前利率":0.60
          ,"剩余期限":20
          ,"状态":"正常"}]]}
    ,(("账户01",{"余额":0}),("账户02",{"余额":0}))
    ,(("A1",{"当前余额":100
             ,"当前利率":0.07
             ,"初始余额":100
             ,"初始利率":0.07
             ,"起息日":"2020-01-03"
             ,"利率":{"固定":0.08}
             ,"债券类型":{"过手摊还":None}})
      ,("B",{"当前余额":20
             ,"当前利率":0.0
             ,"初始余额":100
             ,"初始利率":0.07
             ,"起息日":"2020-01-03"
             ,"利率":{"固定":0.00}
             ,"债券类型":{"权益":None}
             }))
    ,(("信托费用",{"类型":{"固定费用":2}}),)
    ,{"未违约":[
         ["计提利息","A1"]
         ,["账户转移","账户01","账户02"
           ,{"公式":("excess"
                    ,("合计",("债券待付利息","A1"),("待付费用","信托费用"))
                    ,("账户余额","账户02"))}]
         ,["支付费用","账户02",['信托费用']]
         ,["计提支付利息","账户02",["A1"]]
         ,["transfer",'账户02','账户01',{"ds":("ledgerBalance","Debit","MyLedger")},"book","Credit","MyLedger"]
         ,["支付本金","账户01",["A1"]]
         ,["支付本金","账户01",["B"]]
         ,["支付收益","账户01","B"]
         ,["支付收益","账户02","B"]
     ]
     ,"回款后":[
         ["簿记"
          ,["PDL","Debit",("资产池累计违约余额",),[("MyLedger",("债券余额",))]]]
     ]}
    ,(["利息回款","账户02"]
      ,["本金回款","账户01"]
      ,["早偿回款","账户01"]
      ,["回收回款","账户01"])
    ,None
    ,None
    ,None
    ,None
    ,("设计","摊销")
    ,None
    ,{"MyLedger":{"余额":0,"记录":None}}
)
