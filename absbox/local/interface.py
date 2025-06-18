from collections import namedtuple
from typing import List, Tuple


def mkTag(x: tuple | str) -> dict:
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}

def readAeson(x:dict):
    match x:
        case {"tag": tag,"contents": contents} if isinstance(contents,list):
            return {tag: [readAeson(c) for c in contents]}
        case {"tag": tag,"contents": {'numerator': n,'denominator': de}} :
            return {tag: (n/de)}
        case {"tag": tag,"contents": contents} if isinstance(contents,dict):
            return {tag: {k: readAeson(v) for k,v in contents.items()} }            
        case {"tag": tag,"contents": contents} if isinstance(contents,str):
            return {tag: contents}   
        case {"tag": tag, **kwargs} if len(kwargs)>1 :
            return {k: readAeson(v) for k,v in kwargs.items()} | {"tag": tag}
        case {"tag": tag} if isinstance(tag,str):
            return tag   
        case {'numerator': n,'denominator': de}:
            return (n/de)
        case x if isinstance(x,dict):
            return {k:readAeson(_x) for k,_x in x.items()}
        case x if isinstance(x,list):
            return [readAeson(_x) for _x in x]
        case n if isinstance(n,float) or isinstance(n,int):
            return n
        case m if isinstance(m, dict):
            return {k: readAeson(v) for k,v in m.items() }
        case s if isinstance(s, str):
            return s
        case None:
            return None
        case {}:
            return {}
        case s if isinstance(s,str):
            return s
        case _:
            raise RuntimeError("failed to match",x)


