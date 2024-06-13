import re
import dateparser
import toolz as tz
from lenses import lens

def rmDigitsInLine(x):
    return re.sub("\n\d+\n","",x)

def rmHeader(x):
    h1 = "归集日期 期初剩余本金 回收本金 回收利息 期末剩余本金"
    return re.sub(h1,"",x)

def removeComma(x):
    return x.replace(",","")

def hyphenToZero(x):
    return x.replace("-","0")

def removeEmpty(x):
    return [ _ for _ in x if _]

def removePg(xs):
    return [ x for x in xs if not re.match(r"^\d+$",x)]


def splitSpace(xs:list):
    return [ _.split(" ") for _ in xs]

def normalizedDate(x:str):
    return dateparser.parse(x).strftime("%Y-%m-%d")

def removeIfAllinSet(xs:list,s:set):
    return [ x for x in xs if not set(x) == s]