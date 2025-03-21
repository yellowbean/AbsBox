import toolz as tz
from lenses import lens
import pandas as pd
import json, enum, os, pathlib, re
from htpy import body, h1, head, html, li, title, ul, div, span, h3, h2, a, h4,h5, h6
from markupsafe import Markup
from .local.cf import readInspect
from .local.cf import readBondsCf,readFeesCf,readAccsCf,readPoolsCf,readLedgers,readTriggers

class OutputType(int, enum.Enum):
    """Internal
    """
    Plain = 0 # print cashflow to html tables 
    Anchor = 1 # print cashflow with book mark
    Tabbed = 2 # TBD


def mapToList(m:dict, title_=h3, anchor=False):
    m2 = {}
    if not anchor:
        m2 = {title_[k]:div[Markup(v.to_html())] for k,v in m.items() }
    else:
        m2 = {title_(id=f"anchor-{anchor}-{k}")[k]:div[Markup(v.to_html())]
                for k,v in m.items() }

    return list(m2.items())

def buildSection(lst:list, title_=(h2,h3), anchor=False):
    return [ div[ title_[0](id=f"anchor-{_t}")[_t], mapToList(x, anchor=_t)] 
            for (_t, x) in lst]

def buildSectionFlat(lst:list, title_=h2, anchor=False):
    return [ div[ title_(id=f"anchor-{_t}")[_t],Markup(x.to_html())] 
            for (_t, x) in lst if x is not None]


def consolResp(r:dict):
    bondDf = ("Bond", tz.valfilter(lambda x: isinstance(x, pd.DataFrame), r['bonds']))
    bondGrpDf = ("BondGroup", 
                  tz.pipe(tz.valfilter(lambda x: not isinstance(x, pd.DataFrame), r['bonds'])
                          ,lambda x : {f"{k}-{k2}":v2 for k,v in x.items()
                                         for k2,v2 in v.items()}))
    poolDf = ("Pool", r['pool']['flow'])
    accDf = ("Accounts", r['accounts'])
    feeDf = ("Fee", r['fees'])

    reportDf = ("Finanical Reports", r['result'].get('report', {}))
    
    results = dict([("Status",r['result']['status'])
                    ,("Pricing",r["pricing"])
                    ,("Bond Summary",r['result']['bonds'])
                    ,("Log",r['result']['logs'])
                    ,("Waterfall",r['result']['waterfall'])
                    ,("Inspect",readInspect(r['result']))])
    

    jointDfs =[("MultiFee",readFeesCf(feeDf[1]))
               ,("MultiBond",readBondsCf(bondDf[1],popColumns=[]))
               ,("MultiAccounts",readAccsCf(accDf[1]))
               ,("MultiPools", readPoolsCf(poolDf[1]))
               ,("MultiLedger", readLedgers(r.get("ledgers",{})))
               ,("MultiTrigger", readTriggers(r.get("triggers",{})))]
    return dict(
        [bondDf]+[bondGrpDf]+[poolDf]+[accDf]+[feeDf]\
        +[reportDf]+[("result",results)]+[ (x[0],{x[0]:x[1]}) for x in jointDfs ]
    )

def toHtml(r:dict, p:str, style=OutputType.Plain, debug=False):
    """
    r : must be a result from "read=True"
    """

    bondDf = ("Bond", tz.valfilter(lambda x: isinstance(x, pd.DataFrame), r['bonds']))
    bondGrpDf = ("BondGroup", 
                 tz.pipe(tz.valfilter(lambda x: not isinstance(x, pd.DataFrame), r['bonds'])
                         ,lambda x : {f"{k}-{k2}":v2 for k,v in x.items()
                                        for k2,v2 in v.items()}
                         )
                )

    section0 = buildSection([bondDf,bondGrpDf])

    # section 1
    poolDf = ("Pool", r['pool']['flow'])
    accDf = ("Accounts", r['accounts'])
    feeDf = ("Fee", r['fees'])
    section1 = buildSection([poolDf, feeDf, accDf])

    # section 2
    section2 = buildSectionFlat([("Status",r['result']['status'])
                               ,("Pricing",r["pricing"])
                               ,("Bond Summary",r['result']['bonds'])
                               ,("Log",r['result']['logs'])
                               ,("Waterfall",r['result']['waterfall'])
                               ,("Inspect",readInspect(r['result']))])
    # section 3
    #section3 = [div[h2(id=f"anchor-{_t}")[_t], mapToList(x)]
    #            for (_t, x) in [("Finanical Reports", r['result'].get('report', {}))]]
    section3 = buildSection([("Finanical Reports", r['result'].get('report', {}))])

    # read joint cashflows 
    # section 4
    ledgerDf = ("Ledger", r.get("ledgers",{}))
    section4 = buildSectionFlat([("MultiFee",readFeesCf(feeDf[1]))
                               ,("MultiBond",readBondsCf(bondDf[1],popColumns=[]))
                               ,("MultiAccounts",readAccsCf(accDf[1]))
                               ,("MultiPools", readPoolsCf(poolDf[1]))
                               ,("MultiLedger", readLedgers(ledgerDf[1]))
                               ,("MultiTrigger", readTriggers(r.get("triggers",{})))
                               ])


    dealName = r['_deal']['contents']['name']
    c = html[
        head[title[dealName]],
        body[section0, section1, section2, section3 ,section4],
    ]

    if debug:
        return c

    if style == OutputType.Anchor:
        links = c & lens._children[1]._children.Each().Each()._children[0]._attrs.Regex(r'(?<=id=").*(?=")').collect()
        c &= lens._children[1]._children.Each().Each()._children[0]._children.modify(lambda x:[x,a(href="#toc")["  ^Top"] ])

        linksStr = [ l.lstrip("anchor-")  for l in links ]
        hrefs = ul[ [li[a(href=f"#{l}")[f" < {lstr} > "]] for (lstr,l) in zip(linksStr,links) ]]


        c &= lens._children[1]._children.modify(lambda xs: tuple([div(id="toc")[div["Table Of Content"],hrefs]])+xs)

    absPath = None
    with open(p, 'wb') as f:
        f.write(c.encode())
        absPath = os.path.abspath(os.path.join(os.getcwd(),p))

    return absPath


def toExcel(r:dict, p:str,exlude=[],headerFormat={'bold': True, 'bg_color': '#9fdd92','align':'center'}):
    x = consolResp(r)

    #filter out empty in m

    def annotateLoc(m:dict, skip=3):
        assert isinstance(m, dict),"annotateLoc must be a dict"
        if not m:
            return {}
        _r = {}
        beginRow = skip
        for k,v in m.items():
            if (v is None) or v.empty:
                continue
            _r[k] = beginRow
            beginRow += v.index.size + skip
        return _r

    locMap = tz.valmap(annotateLoc, x)

    with pd.ExcelWriter(p, mode='w', engine='xlsxwriter') as writer: 
        workbook = writer.book
        hFormat = workbook.add_format(headerFormat)
        for cat, m in x.items():
            if cat in exlude:
                continue
            workbook.add_worksheet(cat)
            currentSheet = writer.sheets[cat]
            for k,v in m.items():
                if v is None:
                    continue
                if v.empty:
                    continue
                currentSheet.write(locMap[cat][k]-1, 0, k, hFormat)
                v.to_excel(writer, sheet_name=cat, startrow=locMap[cat][k])
            currentSheet.autofit()

    return os.path.abspath(os.path.join(os.getcwd(),p))



