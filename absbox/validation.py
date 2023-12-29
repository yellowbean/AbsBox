from schema import Schema,Regex,Or
import re

from urllib.parse import urlparse


def isValidUrl(url: str) -> str:
    try:
        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            return url
    except ValueError:
        print(f"Invalid URL {url}")
        return None

def vList(x, t, msg:str = None) -> list:
    return Schema([t]).validate(x)

def vDict(x, msg:str = None) -> dict:
    pass

def vStr(x, msg:str = None) -> str:
    return Schema(str).validate(x)

def vNum(x, msg:str = None) -> float:
    return Schema(Or(float, int)).validate(x)

def vFloat(x, msg:str = None) -> float:
    return Schema(float).validate(x)

def vInt(x, msg:str = None) -> int:
    return Schema(int).validate(x)

def vBool(x, msg:str = None) -> bool:
    return Schema(bool).validate(x)

def vDate(x, msg:str = None) -> str:
    return Schema(Regex(r"^\d{4}-\d{2}-\d{2}$")).validate(x)

def vCurve(x, msg:str = None):
    return Schema([[Schema(Regex(r"^\d{4}-\d{2}-\d{2}$"))
                    ,Or(int, float)]]).validate(x)

def vTable(x, msg:str = None):
    return Schema([[Or(int, float) ,Or(int, float)]]).validate(x)

def validation(deal):
    errors = []
    warnings = []
    if len(errors) > 0:
        return False,errors,warnings
    else:
        return True,[],warnings