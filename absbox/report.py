import toolz as tz
from lenses import lens
import pandas as pd
import json, enum, os, pathlib, re
from htpy import body, h1, head, html, li, title, ul, div, span, h3, h2, a
from markupsafe import Markup
from absbox import readInspect
from absbox import readBondsCf,readFeesCf,readAccsCf,readPoolsCf


class OutputType(int, enum.Enum):
    """Internal
    """
    Plain = 0 # print cashflow to html tables 
    Anchor = 1 # print cashflow with book mark
    Tabbed = 2 # TBD


def singleToMap(x,defaultName = "Consol")->dict:
    if isinstance(x, dict):
        return x
    else:
        return {defaultName: x}

def mapToList(m:dict,anchor=False):
    m2 = {}
    if not anchor:
        m2 = {h3[k]:div[Markup(v.to_html())] for k,v in m.items() }
    else:
        m2 = {h3(id=f"anchor-{anchor}-{k}")[k]:div[Markup(v.to_html())]
                for k,v in m.items() }

    return list(m2.items())

def toHtml(r:dict, p:str, style=OutputType.Plain, debug=False):
    """
    r : must be a result from "read=True"
    """
    dealName = r['_deal']['contents']['name']

    poolDf = singleToMap(r['pool']['flow'])
    accDf = r['accounts']
    feeDf = r['fees']
    bondDf = r['bonds']

    section1 = [ div[ h2(id=f"anchor-{_t}")[_t],mapToList(x,anchor=_t) ]
                for (_t,x) in [("Pool",poolDf),("Fee",feeDf),("Bond",bondDf),("Accounts",accDf)]
                ]

    section2 = [ div[ h2(id=f"anchor-{_t}")[_t],Markup(x.to_html()) ]
                for (_t,x) in [("Status",r['result']['status'])
                               ,("Pricing",r['pricing'])
                               ,("Bond Summary",r['result']['bonds'])
                               ,("Log",r['result']['logs'])
                               ,("Waterfall",r['result']['waterfall'])
                               ,("Inspect",readInspect(r['result']))]
                if x is not None]

    section3 = [ div[ h2(id=f"anchor-{_t}")[_t],mapToList(x) ]
                for (_t,x) in [("Finanical Reports",r['result']['report'])]]
    
    # read joint cashflows 
    seciont4 = [ div[ h2(id=f"anchor-{_t}")[_t],Markup(x.to_html()) ]
                for (_t,x) in [("MultiFee",readFeesCf(feeDf)),("MultiBond",readBondsCf(bondDf,popColumns=[])),("MultiAccounts",readAccsCf(accDf)),("MultiPools", readPoolsCf(poolDf))]
            ]

    c = html[
        head[ title[dealName]],
        body[ section1 ,section2 ,section3, seciont4 ],
    ]

    if debug:
        return c

    if style == OutputType.Anchor:
        links = c & lens._children[1]._children.Each().Each()._children[0]._attrs.Regex(r'(?<=id=").*(?=")').collect()
        c &= lens._children[1]._children.Each().Each()._children[0]._children.modify(lambda x:[x,a(href="#toc")["  ^Top"] ])
        
        linksStr = [ l.lstrip("anchor-")  for l in links ]
        hrefs = ul[ [li[a(href=f"#{l}")[f" < {lstr} > "]] for (lstr,l) in zip(linksStr,links) ]]


        c &= lens._children[1]._children.modify(lambda xs: tuple([div(id="toc")[div["Table Of Content"],hrefs]])+xs)

    with open(p, 'wb') as f:
        f.write(c.encode())
