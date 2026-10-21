"""Shared response-reading helpers used by both the English (``Generic``) and
Chinese (``SPV``) deal readers.

Only the pieces that are structurally identical between the two locales live
here. The bond statement reader is intentionally *not* shared because the
``BondGroup`` payload shape differs between the two readers.
"""
import collections
import pandas as pd
import toolz as tz
from lenses import lens

from .component import readPoolCf


def readComponentStmts(deal_content: dict, read_paths: dict, date_key: str = "date"
                       , handle_none: bool = False) -> dict:
    """Read the per-component statement maps (fees, accounts, ...) into DataFrames.

    :param deal_content: the ``contents`` map of a raw deal response
    :param read_paths: mapping of ``component name -> (stmt key, columns, label)``
    :param date_key: index column name (``"date"`` for English, ``"日期"`` for Chinese)
    :param handle_none: when true, a ``None`` statement becomes an empty frame
    :return: ordered map of ``component name -> OrderedDict(name -> DataFrame)``
    """
    output: dict = {}
    for comp_name, comp_v in read_paths.items():
        if (comp_name not in deal_content) or (deal_content[comp_name] is None):
            continue
        output[comp_name] = {}
        row_map = comp_v[3] if (len(comp_v) > 3) else None
        for k, x in deal_content[comp_name].items():
            if x[comp_v[0]]:
                ir = list(tz.pluck('contents', x[comp_v[0]]))
                if row_map is not None:
                    ir = [row_map(r) for r in ir]
                output[comp_name][k] = pd.DataFrame(ir, columns=comp_v[1]).set_index(date_key)
            elif handle_none and x[comp_v[0]] is None:
                output[comp_name][k] = pd.DataFrame([], columns=comp_v[1]).set_index(date_key)
        output[comp_name] = collections.OrderedDict(sorted(output[comp_name].items()))
    return output


def ledgerEntryRows(row: list) -> list:
    """Flatten an engine ``EntryTxn`` row ``[date, (dir, balance), (dir, amount), comment]``
    to ``[date, balance, amount, comment]`` (``BookLedgerBy`` direction is dropped)."""
    return [row[0], row[1][1], row[2][1], row[3]]


def readPoolFlows(resp, deal_content: dict) -> tuple:
    """Read pool and outstanding-pool cashflows from a run response.

    :return: ``(pool, pool_outstanding)`` where each is
             ``{"flow": {...}, "breakdown": {...}}``
    """
    outstanding_pool_flow = {k: {"flow": readPoolCf(aggFlow['contents'])
                                 , "breakdown": [readPoolCf(_['contents']) for _ in breakdownFlows] if breakdownFlows else []}
                             for k, (aggFlow, breakdownFlows) in resp[4].items()}
    pool_outstanding = {"flow": {k: v['flow'] for k, v in outstanding_pool_flow.items()}
                        , "breakdown": {k: v['breakdown'] for k, v in outstanding_pool_flow.items()}}

    pool = {}
    poolMap = deal_content['pool']['contents']
    if deal_content['pool']['tag'] == 'MultiPool':
        pool['flow'] = tz.valmap(lambda v: readPoolCf(v['futureCf'][0]['contents']) if (not v['futureCf'] is None) else pd.DataFrame(), poolMap)
        pool['breakdown'] = tz.valmap(lambda v: list(tz.map(readPoolCf, v['futureCf'][1] & lens.Each()['contents'].collect())) if (v['futureCf'] and (not v['futureCf'][1] is None)) else [], poolMap)
    elif deal_content['pool']['tag'] == 'ResecDeal':
        # resec keys are built as "<deal name>:<bond>:<settle date>:<pct>" (see mkPoolType).
        # rsplit keeps deal names that themselves contain ':' intact.
        def resecKey(k: str):
            parts = k.rsplit(":", 3)
            return tuple(parts[1:]) if len(parts) == 4 else k
        pool['flow'] = {resecKey(k): readPoolCf(v['futureCf']['contents']) for (k, v) in poolMap.items()}
    else:
        raise RuntimeError(f"Failed to match deal pool type:{deal_content['pool']['tag']}")

    return pool, pool_outstanding
