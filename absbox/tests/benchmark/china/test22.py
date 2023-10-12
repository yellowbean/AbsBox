from absbox import API

localAPI = API("https://absbox.org/api/latest",'chinese')

mypool = {"清单":[["租赁",{"初始租金":100,"初始期限":12,"频率":"月末","起始日":"2021-01-31","计提周期":"季度末", "涨幅":0.085}]
                #,["租赁",{"初始租金":100,"初始期限":12,"频率":"月末","起始日":"2021-02-01","计提周期":"季度末", "涨幅":[0.05,0.06,0.0]}]
                #,["租赁",{"固定租金":100,"初始期限":12,"频率":["每月",20],"起始日":"2021-02-01"}]
                ]
         ,"封包日":"2021-01-04"}

from absbox.local.util import aggCFby
p = localAPI.runPool(mypool
                    ,assumptions=[{"租赁截止日":"2023-02-01"}]
                    ,read=True)
# 对租金按月份进行归集     
aggCFby(p,"M",["租金"]).plot.bar(rot=45,ylabel="租金合计")


p = localAPI.runPool(mypool
                     ,assumptions=[{"租赁截止日":"2023-02-01"}
                                   ,{"租赁间隔":25}]
                     ,read=True)
aggCFby(p,"M",["租金"]).plot.bar(rot=45,ylabel="租金合计")



p = localAPI.runPool(mypool,assumptions=[{"租赁截止日":"2023-02-01"}
                                        ,{"租赁间隔":25}
                                        ,{"租赁年涨幅":0.15}],read=True)
aggCFby(p,"M",["租金"]).plot.bar(rot=45,ylabel="租金合计")


increase_curve_assump = [{"租赁年涨幅":[["2021-01-01",0.05]
                          ,["2022-01-01",0.15]
                          ,["2023-01-01",0.35]]}
                         ,{"租赁截止日":"2023-02-01"}
                         ,{"租赁间隔":25}]
p = localAPI.runPool(mypool
                     ,assumptions=increase_curve_assump
                     ,read=True)
aggCFby(p,"M",["租金"]).plot.bar(rot=45,ylabel="租金合计")


from absbox.local.util import npv
npv(p,rate=0.07,init=("2021-01-04",0))


deal_data = ["租金类ABS案例"
    ,{"封包日":"2021-03-31","起息日":"2021-06-15","首次兑付日":"2021-07-26"
      ,"法定到期日":"2060-12-01","收款频率":"月末","付款频率":["每月",26]}
    ,mypool
    ,(("账户01",{"余额":0}),)
    ,(("A1",{"当前余额":80_000
             ,"当前利率":0.07
             ,"初始余额":80_000
             ,"初始利率":0.07
             ,"起息日":"2021-06-15"
             ,"利率":{"固定":0.08}
             ,"债券类型":{"锁定摊还":"2022-10-26"}
            })
      ,("B",{"当前余额":30_000
             ,"当前利率":0.00
             ,"初始余额":30_000
             ,"初始利率":0.00
             ,"起息日":"2021-06-15"
             ,"利率":{"期间收益":0.02}
             ,"债券类型":{"权益":None}
             }))
    ,(("日常费用",{"类型":{"周期费用":[["每月",1],500]}}),)
    ,{"未违约":[
         ["支付费用","账户01",['日常费用']]
         ,["计提支付利息","账户01",["A1"]]
         ,["支付期间收益","账户01",["B"]]
         ,["支付本金","账户01",["A1"]]
         ,[[('债券余额','A1') ,"=",0]
          ,["支付本金","账户01",["B"]]
          ,["支付收益","账户01","B"]
          ]
     ]}
    ,(["租金回款","账户01"],)
    ,None
    ,None
    ,None
    ,None
    ,("设计","摊销")
    ]


from absbox.local.china import SPV
from absbox.local.util import bondView
r = localAPI.run(SPV(*deal_data),assumptions=increase_curve_assump,read=True)

# 获取 A1 B 的现金流.
r['bonds']['A1']
r['bonds']['B']

# 将两个债券现金流一并展示 
bondView(r).drop([("A1","备注"),("B","备注")],axis=1)


from absbox.local.util import irr
irr(r['bonds']['B'],init=('2021-06-15',-30_000.00))
# 返回值: 1.152 -> 在2021年6月投入 10000元下, B的年化回报率 ->  15 % 
irr(r['bonds']['A1'],init=('2021-06-15',-80_000.00))
# 返回值: 1.152 -> 在2021年6月投入 60000.00元下, A1的年化回报率 -> 7.2 %

# 多融资方案比较 
## 总融资规模 
total_issuance = 110_000

## 债务融资方案  
financing_plans = [(80_000,0.075,"2022-10-26"),(50_000,0.05,"2022-12-26")] 

## 资本结构方案 
liability_plans = [ (('A1',  {'当前余额': b, '当前利率': r,   '初始余额': b,   '初始利率': r,   '起息日': '2021-06-15',
   '利率': {'固定': 0.08}, '债券类型': {'锁定摊还': t}}),
  ('B',  {'当前余额': total_issuance - b,   '当前利率': 0.0,   '初始余额': total_issuance - b,   '初始利率': 0.0,   '起息日': '2021-06-15',
   '利率': {'期间收益': 0.02}, '债券类型': {'权益': None}}))
    for b,r,t in financing_plans ]

from absbox.local.util import update_deal


## 产品方案 
SPVs = [ SPV(*update_deal(deal_data,4,p)) for p in liability_plans ]

## 相同资产池表现下的结果 
rs = [ localAPI.run(s,assumptions=increase_curve_assump,read=True) for s in SPVs ]

## 确定权益投资金额 
equity_balance = [ -p[1][1]['当前余额'] for p in liability_plans]

# 计算权益投资回报 
[ irr(r['bonds']['B'],init=('2021-06-15',i)) for r,i in zip(rs,equity_balance) ]
