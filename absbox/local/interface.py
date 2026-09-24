from collections import namedtuple
from typing import List, Tuple

from ..exception import AbsboxParseError


def mkTag(x: tuple | str) -> dict:
    match x:
        case (tagName, tagValue):
            return {"tag": tagName, "contents": tagValue}
        case (tagName):
            return {"tag": tagName}

def mkCurve(tag, xs):
    return mkTag((tag, xs))


def preview(x, limit: int = 200) -> str:
    """Truncated repr of a value, for use in parse-error messages.

    Avoids dumping an entire deal/pool into logs and exceptions.
    """
    s = repr(x)
    return s if len(s) <= limit else f"{s[:limit]}...(truncated)"




def readAeson(x):
    match x:
        case None:
            return None
        case n if isinstance(n, (float, int)):
            return n
        case s if isinstance(s, str):
            return s
        case x if isinstance(x, list):
            return [readAeson(_x) for _x in x]
        case {"tag": tag, "contents": contents} if isinstance(contents, list):
            return {tag: [readAeson(c) for c in contents]}
        case {"tag": tag, "contents": {'numerator': n, 'denominator': de}}:
            return {tag: (n / de)}
        case {"tag": tag, "contents": contents} if isinstance(contents, dict):
            return {tag: {k: readAeson(v) for k, v in contents.items()}}
        case {"tag": tag, "contents": contents} if isinstance(contents, str):
            return {tag: contents}
        case {"tag": tag, **kwargs} if len(kwargs) > 1:
            return {k: readAeson(v) for k, v in kwargs.items()} | {"tag": tag}
        case {"tag": tag} if isinstance(tag, str):
            return tag
        case {'numerator': n, 'denominator': de}:
            return (n / de)
        case x if isinstance(x, dict):
            return {k: readAeson(_x) for k, _x in x.items()}
        case _:
            raise AbsboxParseError(f"failed to match {preview(x)}")
