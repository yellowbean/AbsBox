"""Offline unit tests for the pure deal-parsing helpers.

These tests do not require an engine server and are meant to run in CI:
they cover the DSL builders in ``absbox.local.component`` and the
response decoder in ``absbox.local.interface``.
"""
import pytest

from absbox.local.interface import mkTag, mkCurve, readAeson
from absbox.local.component import (
    mkDate,
    mkDatePattern,
    mkBnd,
    mkBndComp,
    mkBondType,
    mkPid,
    mkTradeType,
    mkOrder,
    mkCustom,
    mkFee,
    mkAcc,
    mkCollection,
    mkNonPerfAssumps,
    getStartDate,
)
from absbox.local.util import (
    ensure100,
    renameKs,
    subMap,
    subMap2,
    updateKs,
    getValWithKs,
)
from absbox.local.base import china_bondflow_fields_s, english_bondflow_fields_s
from absbox.local.readers import readComponentStmts
from absbox.exception import AbsboxParseError
from absbox.local.interface import preview


def test_mkTag_and_mkCurve():
    assert mkTag("Equity") == {"tag": "Equity"}
    assert mkTag(("Fix", [1.0, "DC_ACT_365F"])) == {
        "tag": "Fix",
        "contents": [1.0, "DC_ACT_365F"],
    }
    assert mkCurve("IRateCurve", [[1, 0.02]]) == {
        "tag": "IRateCurve",
        "contents": [[1, 0.02]],
    }


def test_readAeson_shapes():
    assert readAeson(None) is None
    assert readAeson(1.5) == 1.5
    assert readAeson(True) is True
    assert readAeson("hello") == "hello"
    assert readAeson([{"tag": "X", "contents": [1, 2]}]) == [{"X": [1, 2]}]
    assert readAeson({"tag": "Frac", "contents": {"numerator": 1, "denominator": 2}}) == {"Frac": 0.5}
    assert readAeson({"tag": "Only"}) == "Only"
    assert readAeson({"numerator": 3, "denominator": 4}) == 0.75
    assert readAeson({"a": {"b": [1]}}) == {"a": {"b": [1]}}
    # tag plus several extra keys keeps the tag and recurses into the rest
    assert readAeson({"tag": "Bond", "bndBalance": 5, "bndName": "B1"}) == {
        "bndBalance": 5,
        "bndName": "B1",
        "tag": "Bond",
    }
    with pytest.raises(RuntimeError):
        readAeson(object())


def test_mkDate_last_collect_case():
    d = mkDate(
        {
            "lastCollect": "2024-01-01",
            "lastPay": "2024-01-15",
            "nextPay": "2024-02-15",
            "nextCollect": "2024-02-01",
            "stated": "2030-01-01",
            "poolFreq": "每月",
            "payFreq": "每月",
        }
    )
    assert d["tag"] == "GenericDates"
    assert "LastCollectDate" in d["contents"]


def test_mkDatePattern():
    assert mkDatePattern("月末") == {"tag": "MonthEnd"}
    assert mkDatePattern(["每月", 15]) == {"tag": "DayOfMonth", "contents": 15}
    with pytest.raises(Exception):
        mkDatePattern("not-a-date-pattern")


def test_mkBond_origin_date_is_validated_as_date():
    bnd = mkBnd(
        "A1",
        {
            "balance": 100.0,
            "rate": 0.05,
            "originBalance": 100.0,
            "originRate": 0.05,
            "startDate": "2021-01-01",
            "rateType": ["fix", 0.05],
            "bondType": "Sequential",
        },
    )
    assert bnd["tag"] == "Bond"
    assert bnd["bndOriginInfo"]["originDate"] == "2021-01-01"
    # a non-date origin date must be rejected
    with pytest.raises(Exception):
        mkBnd(
            "A1",
            {
                "balance": 100.0,
                "rate": 0.05,
                "originBalance": 100.0,
                "originRate": 0.05,
                "startDate": 20210101,
                "rateType": ["fix", 0.05],
                "bondType": "Sequential",
            },
        )


def test_mkBndComp_single_and_group():
    single = mkBndComp(
        "A1",
        (
            "bond",
            {
                "balance": 100.0,
                "rate": 0.05,
                "originBalance": 100.0,
                "originRate": 0.05,
                "startDate": "2021-01-01",
                "rateType": ["fix", 0.05],
                "bondType": "Sequential",
            },
        ),
    )
    assert single["tag"] == "Bond"

    group = mkBndComp(
        "Grp",
        (
            "bondGroup",
            {
                "A1": {
                    "balance": 100.0,
                    "rate": 0.05,
                    "originBalance": 100.0,
                    "originRate": 0.05,
                    "startDate": "2021-01-01",
                    "rateType": ["fix", 0.05],
                    "bondType": "Sequential",
                }
            },
        ),
    )
    assert group["tag"] == "BondGroup"


def test_mkBondType_z_tranche():
    # the engine BondType has a nullary Z constructor:
    #   Hastructure src/Liability.hs:  data BondType = ... | Z | Equity ...
    # and its wire shape is ``{"tag": "Z"}`` (see swagger.json BondType).
    assert mkBondType("Z") == {"tag": "Z"}
    assert mkBondType({"Z": None}) == {"tag": "Z"}
    assert mkBondType("Sequential") == {"tag": "Sequential"}

    bnd = mkBnd(
        "Z1",
        {
            "balance": 100.0,
            "rate": 0.05,
            "originBalance": 100.0,
            "originRate": 0.05,
            "startDate": "2021-01-01",
            "rateType": ["fix", 0.05],
            "bondType": "Z",
        },
    )
    assert bnd["bndType"] == {"tag": "Z"}


def test_mkPid_underlying_deal():
    assert mkPid(None) is None
    assert mkPid("PoolA") == {"tag": "PoolName", "contents": "PoolA"}
    # `Deal-` prefix must take precedence over the generic pool-name branch
    assert mkPid("Deal-ABC:BN1") == {
        "tag": "UnderlyingDeal",
        "contents": ["Deal-ABC", "BN1"],
    }


def test_mkTradeType():
    assert mkTradeType(("byCash", 50)) == {"tag": "ByCash", "contents": 50}
    assert mkTradeType(("byBalance", 100)) == {"tag": "ByBalance", "contents": 100}


def test_mkOrder_and_fallbacks():
    assert mkOrder("byName") == {"tag": "ByName"}
    with pytest.raises(RuntimeError):
        mkOrder("bogus")


def test_mkCustom_and_fallback():
    assert mkCustom({"const": 5}) == {"tag": "CustomConstant", "contents": 5}
    with pytest.raises(RuntimeError):
        mkCustom({"unsupported": 1})


def test_mkNonPerfAssumps_fallback_raises():
    assert mkNonPerfAssumps({}, []) == {}
    assert "stopRunBy" in mkNonPerfAssumps({}, [("stop", "2021-01-01")])
    with pytest.raises(RuntimeError):
        mkNonPerfAssumps({}, [("not-a-real-assumption",)])


def test_mkFee_mkAcc_mkCollection():
    fee = mkFee({"name": "svc", "type": ("fixFee", 10), "feeStart": "2021-01-01"})
    assert fee["feeName"] == "svc"

    acc = mkAcc("acc01", {"balance": 0})
    assert acc["accName"] == "acc01"

    coll = mkCollection(["CollectedInterest", "acc01"])
    assert coll["tag"] == "Collect"


def test_util_helpers():
    ensure100([0.1, 0.2, 0.7])  # float rounding must be tolerated
    with pytest.raises(AssertionError):
        ensure100([0.1, 0.2, 0.6])

    assert renameKs({"a": 1, "b": 2}, [("a", "x")]) == {"x": 1, "b": 2}
    assert renameKs({"b": 2}, [("a", "x")], opt_key=True) == {"b": 2}
    assert subMap({"a": 1}, [("a", 0), ("b", 9)]) == {"a": 1, "b": 9}
    assert subMap2({"余额": 1}, [("余额", "balance", 0)]) == {"balance": 1}
    assert updateKs({"x": 1, "y": 2}, {"x": "a"}) == {"a": 1, "y": 2}
    assert getValWithKs({"a": 1}, ["z", "a"], defaultReturn=0) == 1
    assert getValWithKs({}, ["z"], defaultReturn=7) == 7


def test_get_start_date():
    assert getStartDate(
        {
            "cutoff": "2021-01-01",
            "closing": "2021-01-02",
            "firstPay": "2021-02-01",
            "stated": "2030-01-01",
            "poolFreq": "每月",
            "payFreq": "每月",
        }
    ) == ("2021-01-01", "2021-01-02")
    assert getStartDate({"lastCollect": "2021-01-01", "lastPay": "2021-01-05"}) == (
        "2021-01-01",
        "2021-01-05",
    )


def test_bond_header_columns_parity():
    # regression: a missing comma had concatenated two header names
    assert len(china_bondflow_fields_s) == len(english_bondflow_fields_s) == 9
    assert "罚息本金系数" not in china_bondflow_fields_s


def test_read_component_stmts():
    deal_content = {
        "fees": {"f1": {"feeStmt": [{"contents": ["2021-01-01", 1, 2, 3, 4]}]}},
        "accounts": None,
        "liqProvider": {"p1": {"liqStmt": None}},
    }
    read_paths = {
        "fees": ("feeStmt", ["date", "a", "b", "c", "d"], "fee"),
        "accounts": ("accStmt", ["date", "x"], "acc"),
        "liqProvider": ("liqStmt", ["date", "y"], ""),
    }
    # English reader: None statements become empty frames
    out = readComponentStmts(deal_content, read_paths, date_key="date", handle_none=True)
    assert set(out.keys()) == {"fees", "liqProvider"}
    assert out["fees"]["f1"].index.name == "date"
    assert out["fees"]["f1"].shape == (1, 4)
    assert out["liqProvider"]["p1"].empty

    # Chinese reader: Chinese date column, None statements are skipped
    cn_content = {
        "fees": {"f1": {"feeStmt": [{"contents": ["2021-01-01", 1, 2, 3, 4]}]}},
        "liqProvider": {"p1": {"liqStmt": None}},
    }
    cn_paths = {
        "fees": ("feeStmt", ["日期", "a", "b", "c", "d"], "费用"),
        "liqProvider": ("liqStmt", ["日期", "y"], ""),
    }
    out_cn = readComponentStmts(cn_content, cn_paths, date_key="日期", handle_none=False)
    assert set(out_cn.keys()) == {"fees", "liqProvider"}
    assert out_cn["liqProvider"] == {}
    assert out_cn["fees"]["f1"].index.name == "日期"



def test_preview_truncates_large_values():
    assert preview("abc") == "'abc'"
    long = "x" * 5000
    out = preview(long)
    assert len(out) < 300
    assert out.endswith("...(truncated)")


def test_parse_failures_use_absbox_parse_error():
    # AbsboxParseError must stay compatible with existing `except RuntimeError`
    assert issubclass(AbsboxParseError, RuntimeError)

    with pytest.raises(AbsboxParseError):
        mkTradeType(("byCash-nope", 1))
    with pytest.raises(RuntimeError):
        mkOrder("bogus")

    # a huge offending payload must not be dumped in full into the message
    with pytest.raises(AbsboxParseError) as ei:
        mkOrder("z" * 10000)
    assert len(str(ei.value)) < 300
    assert "truncated" in str(ei.value)


def test_modules_do_not_depend_on_star_import_leakage():
    """Guard against names silently arriving through `from .base import *`.

    `readRunSummary` uses `functools.reduce`; it used to resolve only because
    `base.py` re-exported `util.py`'s namespace via a star import.
    """
    import absbox.local.china as china
    import absbox.local.component as component
    import absbox.local.generic as generic

    for mod in (component, generic, china):
        assert hasattr(mod, "reduce"), f"{mod.__name__} cannot resolve 'reduce'"


def test_sample_deal_serializes_to_engine_json():
    """End-to-end offline check of the whole parse/serialize pipeline.

    Exercises mkDate / mkPoolType / identify_deal_type / mkBndComp / mkWaterfall
    / mkFee / mkAcc / mkCollection / mkCustom against a real sample deal,
    without needing an engine server.
    """
    import json as _json

    from absbox.tests.regression.deals import test01

    j = test01.json
    assert isinstance(j["tag"], str) and j["tag"]
    contents = j["contents"]
    for key in ("dates", "pool", "bonds", "waterfall", "fees", "accounts", "collects", "custom"):
        assert key in contents, key
    _json.dumps(j)  # must remain JSON-serialisable for the engine request


def test_comp_result_handles_bond_groups():
    """Regression: comparing results whose bonds contain a group must not crash."""
    import pandas as pd

    from absbox.local.cmp import compResult

    a = pd.DataFrame({"x": [1, 2]}, index=["d1", "d2"])
    b = pd.DataFrame({"x": [1, 3]}, index=["d1", "d2"])

    def mk(bond):
        return {"pool": {"flow": {}}, "fees": {}, "accounts": {}, "bonds": bond}

    r1 = mk({"A": a, "G": {"g1": a}})
    r2 = mk({"A": b, "G": {"g1": b}})
    out = compResult(r1, r2, names=("L", "R"))
    assert "A" in out["bonds"]
    assert "G" in out["bonds"]


def test_build_run_deal_req_defaults_preserve_payload():
    """Regression: switching mutable defaults to None must not change the JSON.

    `rtn` must stay `[]` and deal-level assumptions must stay `{}` (not `null`).
    """
    import json

    from absbox.client import API
    from absbox.tests.regression.deals import test01

    # self is unused by build_run_deal_req, so it can be exercised offline
    req = API.build_run_deal_req(None, "Single", test01, None, None, None)
    payload = json.loads(req)
    assert payload["tag"] == "SingleRunReq"
    rtn, _deal, _perf, nonPerf = payload["contents"]
    assert rtn == []
    assert nonPerf == {}

    req2 = API.build_run_deal_req(None, "Single", test01, None, None, ["AssetLevelFlow"])
    assert json.loads(req2)["contents"][0] == ["AssetLevelFlow"]


def test_read_cf_sets_and_sorts_date_index():
    """Regression for the inplace->assignment refactor in `_read_cf`."""
    from absbox.local.util import _read_cf

    rows = [
        {"tag": "BondFlow", "contents": ["2021-02-01", 10, 1, 2]},
        {"tag": "BondFlow", "contents": ["2021-01-01", 20, 3, 4]},
    ]
    df = _read_cf(rows, "english")
    assert df.index.name == "Date"
    assert list(df.index) == ["2021-01-01", "2021-02-01"]
