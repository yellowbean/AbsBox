"""Offline unit tests for the pure deal-parsing helpers.

These tests do not require an engine server and are meant to run in CI:
they cover the DSL builders in ``absbox.local.component`` and the
response decoder in ``absbox.local.interface``.
"""
import json

import pytest

from absbox.local.interface import mkTag, mkCurve, readAeson
from absbox.local.component import (
    mkDate,
    mkDatePattern,
    mkDs,
    mkAction,
    mkBnd,
    mkBndComp,
    mkBondType,
    mkPid,
    mkRateSwap,
    mkRateCap,
    mkTradeType,
    mkOrder,
    mkCustom,
    mkFee,
    mkAcc,
    mkCollection,
    mkNonPerfAssumps,
    getStartDate,
    mkBondRate,
    mkCallOptionsLegacy,
    mkAsset,
    mkAssetUnion,
    mkPool,
    mkPoolType,
    identify_deal_type,
)
from absbox.local.util import (
    ensure100,
    renameKs,
    subMap,
    subMap2,
    updateKs,
    getValWithKs,
    isMixedDeal,
    isMixedPoolSpec,
    inferPoolTypeFromAst,
    unifyTs,
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
    assert mkDatePattern("2021-01-01") == {
        "tag": "SingletonDate",
        "contents": "2021-01-01",
    }
    with pytest.raises(Exception):
        mkDatePattern("not-a-date-pattern")
    # an unrecognised-but-stringly value must surface as AbsboxParseError,
    # not as a raw schema.SchemaError from vDate
    with pytest.raises(AbsboxParseError):
        mkDatePattern("not-a-date-pattern")


def test_mkAction_trigger_update_chinese_alias():
    # regression: `["更新事件", name]` used to bind a scalar and crash vList
    assert mkAction(["更新事件", "T1"]) == {
        "tag": "RunTrigger",
        "contents": ["InWF", ["T1"]],
    }
    assert mkAction(["runTrigger", "T1"]) == {
        "tag": "RunTrigger",
        "contents": ["InWF", ["T1"]],
    }
    assert mkAction(["runTriggers", "T1", "T2"]) == {
        "tag": "RunTrigger",
        "contents": ["InWF", ["T1", "T2"]],
    }


def test_mkAction_pay_int_and_book_normalizes_direction():
    # regression: PayIntAndBook used to emit the raw direction ("借方")
    r = mkAction(
        ["支付利息", "acc", ["A"], {"limit": ("balPct", 0.5)}, "簿记", "借方", "L1"]
    )
    assert r["tag"] == "PayIntAndBook"
    assert r["contents"][-1] == ["Debit", "L1"]


def test_mkDs_dealstat_unknown_type_raises():
    # regression: an unknown dealStat type silently returned None
    with pytest.raises(AbsboxParseError):
        mkDs(("dealStat", "not-a-type", "x"))


def test_mkDs_account_balance_tuple():
    # regression: a missing comma made the bare string "accountBalance" match
    assert mkDs(("accountBalance", "acc01")) == {
        "tag": "AccBalance",
        "contents": ["acc01"],
    }


def test_mkFee_chinese_last_paid_date_field():
    # regression: Chinese fee mapped to `feeLastPaidDay` (Day) not `...Date`
    fee = mkFee(
        {
            "名称": "f1",
            "类型": {"固定费用": 100},
            "起始日": "2020-01-01",
            "上次缴付日期": "2020-02-01",
        }
    )
    assert fee["feeLastPaidDay"] == "2020-02-01"
    assert "feeLastPaidDate" not in fee


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
    # engine PoolId only supports PoolName | PoolConsol | DealBondFlow
    with pytest.raises(AbsboxParseError):
        mkPid("Deal-ABC:BN1")
    assert mkPid(("DealBondFlow", "ABC", "BN1", "2021-06-15", 0.05)) == {
        "tag": "DealBondFlow",
        "contents": ["ABC", "BN1", "2021-06-15", 0.05],
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

    # all documented fix-reserve forms build the same wire
    for rt in [("fix", 1000), ("fixReserve", 1000), {"fixReserve": 1000}]:
        assert mkAcc("R", {"balance": 0, "type": rt})["accType"] == {
            "tag": "FixReserve", "contents": 1000}

    coll = mkCollection(["CollectedInterest", "acc01"])
    assert coll["tag"] == "Collect"


def test_mkRateSwap_settleDates_must_be_tuple():
    swap = {"updateDates": "MonthEnd", "pair": [0.04, ("SOFR1M", 0.0)],
            "base": {"fix": 100}, "start": "2021-06-15", "balance": 100}
    with pytest.raises(AbsboxParseError):
        mkRateSwap(swap | {"settleDates": "MonthEnd"})
    w = mkRateSwap(swap | {"settleDates": ("MonthEnd", "DC_ACT_365F")})
    assert w["rsSettleDates"] == ({"tag": "MonthEnd"}, "DC_ACT_365F")


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


def test_read_bond_stmt_group_and_multi_int_bond_locale_parity():
    """Regression: the Chinese bond reader must accept the same wire shapes
    as the English one (BondGroup contents is ``[bndMap, pt]``; MultiIntBond
    must be supported)."""
    from absbox.local import china, generic

    stmt = [
        {"contents": ["2021-01-01", 100, 1, 2, 0.05, 3, 4, 5, 1.0, "m"]}
    ]
    grp = {"tag": "BondGroup", "contents": [{"A1": {"bndStmt": stmt}}, None]}
    cn_grp = china.readBondStmt(grp)
    en_grp = generic.readBondStmt(grp)
    assert set(cn_grp) == set(en_grp) == {"A1"}
    assert cn_grp["A1"].index.name == "date"

    multi = {"tag": "MultiIntBond", "bndStmt": stmt}
    cn_multi = china.readBondStmt(multi)
    en_multi = generic.readBondStmt(multi)
    assert cn_multi.shape == en_multi.shape == (1, 9)
    assert cn_multi.index.name == "date"


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


ASSET_LOAN = ["Loan", {"originBalance": 100, "originRate": {"fix": 0.05}, "originTerm": 24,
                       "freq": "Monthly", "type": "Level", "originDate": "2021-01-01"},
              {"currentBalance": 100, "currentRate": 0.05, "remainTerm": 24, "status": "Current"}]

ASSET_MORTGAGE = ["Mortgage", {"originBalance": 2000, "originRate": {"fix": 0.045},
                               "originTerm": 240, "freq": "Monthly", "type": "Level",
                               "originDate": "2021-01-01"},
                  {"currentBalance": 2000, "currentRate": 0.045, "remainTerm": 240,
                   "status": "Current"}]


def _generic(pool):
    from absbox.local.generic import Generic

    dates = {"cutoff": "2021-03-01", "closing": "2021-04-01", "firstPay": "2021-06-20",
             "payFreq": ["DayOfMonth", 20], "poolFreq": "MonthFirst", "stated": "2030-01-01"}
    bonds = (("A1", {"balance": 1000, "rate": 0.07, "originBalance": 1000, "originRate": 0.07,
                     "startDate": "2020-01-03", "rateType": {"Fixed": 0.08},
                     "bondType": {"Sequential": None}}),)
    return Generic("T", dates, pool, (("acc01", {"balance": 0}),), bonds, tuple(), {}, [], {})


def test_mkBondRate_none_is_serializable():
    # InterestInfo = Fix IRate DayCount: [rate, dayCount], same order as the explicit fix arms
    r = mkBondRate(None)
    assert r == {"tag": "Fix", "contents": [0, "DC_ACT_365F"]}
    assert mkBondRate({"fix": 0.06}) == {"tag": "Fix", "contents": [0.06, "DC_ACT_365F"]}
    json.dumps(r)


def test_mkDs_pool_collection_stats_matches_engine_tag():
    r = mkDs(("curPoolCollectionStats", ["P1"], 0, "Interest"))
    assert r["tag"] == "PoolCollectionStats"
    assert r["contents"] == [0, ["CollectedInterest"], [{"tag": "PoolName", "contents": "P1"}]]


def test_mkCallOptions_legacy_and_alias():
    r = mkCallOptionsLegacy(("and", ("poolBalance", 10), ("bondBalance", 5)))
    assert r["tag"] == "And"
    assert [x["tag"] for x in r["contents"]] == ["PoolBalance", "BondBalance"]
    assert mkCallOptionsLegacy(("all", ("poolBalance", 10)))["tag"] == "And"


def test_mkAssetUnion_projected_cashflow_and_invoice_alias():
    assert mkAssetUnion(["ProjectedByFactor", [], "MonthEnd", 0.05, []])["tag"] == "PF"
    assert mkAssetUnion(["应收账款", {"start": "2021-01-01", "originBalance": 100,
                                    "originAdvance": 0, "dueDate": "2021-06-01",
                                    "feeType": ("Fixed", 0)},
                         {"status": "Current"}])["tag"] == "RE"


def test_mkAsset_invoice_chinese_aliases():
    for alias in ("应收账款", "应收帐款"):
        r = mkAsset([alias, {"start": "2021-01-01", "originBalance": 100, "originAdvance": 0,
                             "dueDate": "2021-06-01", "feeType": ("Fixed", 0)},
                     {"status": "Current"}])
        assert r["tag"] == "Invoice"


def test_mkAsset_invoice_spellings_normalize_to_Invoice():
    # 应收账款 (账) is the canonical Chinese tag; 帐 and 賬 variants normalize to
    # the same "/"Invoice" engine asset.
    spec = {"start": "2021-01-01", "originBalance": 100.0, "originAdvance": 0.0
             , "dueDate": "2021-06-01"}
    status = {"status": "Current"}
    for tag in ["Invoice", "应收账款", "应收帐款", "应收賬款"]:
        r = mkAsset([tag, spec, status])
        assert r["tag"] == "Invoice"
        info, st = r["contents"][0], r["contents"][1]
        assert info["originBalance"] == 100.0
        assert info["obligor"] is None
        assert info["feeType"] is None
    r = mkAsset(["应收賬款", dict(spec, feeType=("Fixed", 200.0)), status])
    assert r["contents"][0]["feeType"] == {"tag": "FixedFee", "contents": 200.0}


def test_mkAssetUnion_invoice_all_spellings():
    spec = {"start": "2021-01-01", "originBalance": 100.0, "originAdvance": 0.0
             , "dueDate": "2021-06-01"}
    for tag in ["Invoice", "应收账款", "应收帐款", "应收賬款"]:
        r = mkAssetUnion([tag, spec, {"status": "Current"}])
        assert r["tag"] == "RE"
        assert r["contents"]["tag"] == "Invoice"


def test_invoice_pool_type_all_spellings_and_mixed():
    from absbox.local.util import inferPoolTypeFromAst, isMixedPoolSpec

    spec = {"start": "2021-01-01", "originBalance": 100.0, "originAdvance": 0.0
             , "dueDate": "2021-06-01"}
    for tag in ["Invoice", "应收账款", "应收帐款", "应收賬款"]:
        assert inferPoolTypeFromAst({"assets": [[tag, spec, {"status": "Current"}]]}) == "VPool"
        assert isMixedPoolSpec({"assets": [[tag, spec, {"status": "Current"}]]}) is False
    mixed = {"assets": [["应收賬款", spec, {"status": "Current"}], ASSET_MORTGAGE]}
    assert isMixedPoolSpec(mixed) is True
    with pytest.raises((RuntimeError, AbsboxParseError)):
        inferPoolTypeFromAst(mixed)


def test_mkPool_locales_and_mixed():
    assert mkPool({"assets": [ASSET_LOAN], "cutoffDate": "2021-01-01"})["tag"] == "LPool"
    assert mkPool({"清单": [ASSET_LOAN], "封包日": "2021-01-01"})["tag"] == "LPool"

    mixed = mkPool({"assets": [ASSET_MORTGAGE, ASSET_LOAN], "cutoffDate": "2021-01-01"})
    assert mixed["tag"] == "UPool"
    assert [a["tag"] for a in mixed["contents"]["assets"]] == ["MO", "LO"]

    with pytest.raises(AbsboxParseError):
        mkPool({"other": 1})


def test_mixed_single_pool_detection_and_tagging():
    mixed = {"assets": [ASSET_MORTGAGE, ASSET_LOAN], "cutoffDate": "2021-01-01"}
    assert isMixedPoolSpec(mixed)
    assert isMixedDeal(mixed)
    with pytest.raises(RuntimeError):
        inferPoolTypeFromAst(mixed)
    # Mortgage and AdjustRateMortgage are constructors of the same engine pool.
    same_family = {"assets": [ASSET_MORTGAGE, ["AdjustRateMortgage", {}, {}]]}
    assert not isMixedPoolSpec(same_family)

    from absbox.client import API

    r = json.loads(API.__new__(API).build_pool_req(mixed, None, None))
    assert r["contents"][1]["tag"] == "UPool"
    inner = r["contents"][1]["contents"]["contents"]["PoolConsol"]["assets"]
    assert [a["tag"] for a in inner] == ["MO", "LO"]


def test_tagged_pool_passthrough():
    from absbox.client import API

    p = mkPool({"assets": [ASSET_LOAN], "cutoffDate": "2021-01-01"})
    assert not isMixedDeal(p)
    r = json.loads(API.__new__(API).build_pool_req(p, None, None))
    assert r["contents"][1] == p
    assert identify_deal_type({"pool": mkPoolType("2021-01-01", p, False)}) == "LDeal"


def test_generic_accepts_mixed_and_tagged_pools():
    assert _generic({"assets": [ASSET_MORTGAGE, ASSET_LOAN]}).json["tag"] == "UDeal"
    tagged = mkPool({"assets": [ASSET_LOAN], "cutoffDate": "2021-01-01"})
    assert _generic(tagged).json["tag"] == "LDeal"


def test_mkDeal_requires_pool():
    from absbox.deal import mkDeal
    from absbox.exception import AbsboxError

    with pytest.raises(AbsboxError):
        mkDeal({"dates": {}, "accounts": {}})


def test_readPoolFlows_resec_keys_with_colons(monkeypatch):
    import absbox.local.readers as readers

    monkeypatch.setattr(readers, "readPoolCf", lambda contents: contents)
    deal_content = {"pool": {"tag": "ResecDeal", "contents": {
        "A1:BN1:2021-03-01:0.5": {"futureCf": {"contents": "flow1"}},
        "Deal:A:BN2:2021-03-01:1.0": {"futureCf": {"contents": "flow2"}},
    }}}
    pool, outstanding = readers.readPoolFlows([None, None, None, None, {}], deal_content)
    assert pool["flow"] == {("BN1", "2021-03-01", "0.5"): "flow1",
                            ("BN2", "2021-03-01", "1.0"): "flow2"}
    assert outstanding == {"flow": {}, "breakdown": {}}


def test_pool_issuance_balance_maps_to_original_pool_balance():
    assert mkDs(("poolIssuanceBalance", ["P1"])) == mkDs(("originalPoolBalance", ["P1"]))
    assert mkDs(("poolIssuanceBalance",)) == {"tag": "OriginalPoolBalance", "contents": None}


def test_calcIntBy_passes_scalar_bond_name():
    assert mkAction(["calcIntBy", (None, None), "A1"]) == \
        {"tag": "CalcBondIntBy", "contents": ["A1", None, None]}


def test_buyAsset_wants_single_pool_target():
    liq = ["Current|Defaulted", 1.0, 0]
    r = mkAction(["buyAsset", liq, "acc01", None, "P1"])
    assert r["tag"] == "BuyAsset"
    assert r["contents"][3] == {"tag": "PoolName", "contents": "P1"}
    with pytest.raises(AbsboxParseError):
        mkAction(["buyAsset", liq, "acc01", None, ["P1", "P2"]])


def test_writeOff_books_direction():
    assert mkAction(["writeOff", "A1", None, "book", "借方", "L1"]) == \
        {"tag": "WriteOffAndBook", "contents": [None, "A1", ["Debit", "L1"]]}
    r = mkAction(["writeOff", ["A1", "A2"], None, "book", "贷方", "L2"])
    assert r["tag"] == "WriteOffBySeqAndBook"
    assert r["contents"][1] == ["A1", "A2"]
    assert r["contents"][2] == ["Credit", "L2"]


def test_placeholder_has_null_payload():
    assert mkAction(None) == {"tag": "Placeholder", "contents": None}


def test_payIntByIndex_sends_built_support():
    r = mkAction(["payIntByIndex", "acc01", ["A1"], 3, {"support": ["account", "acc02"]}])
    assert r["tag"] == "PayIntByRateIndex"
    assert r["contents"][0] is None
    assert r["contents"][3] == 3
    assert r["contents"][4] == {"tag": "SupportAccount", "contents": ["acc02", None]}
    assert mkAction(["payIntByIndex", "acc01", ["A1"], 3])["contents"][4] is None


def test_ledger_rows_flatten_book_pairs():
    from absbox.local.readers import ledgerEntryRows, readComponentStmts

    deal_content = {"ledgers": {"L1": {"ledgStmt": [
        {"tag": "EntryTxn", "contents": ["2021-01-01", ["Debit", 100], ["Credit", 200], "c1"]},
        {"tag": "EntryTxn", "contents": ["2021-01-02", ["Credit", 300], ["Debit", 400], "c2"]},
    ]}}}
    paths = {"ledgers": ("ledgStmt", ["date", "balance", "amount", "comment"], "", ledgerEntryRows)}
    df = readComponentStmts(deal_content, paths)["ledgers"]["L1"]
    assert df.loc["2021-01-01", "balance"] == 100
    assert df.loc["2021-01-02", "amount"] == 400


def test_unifyTs_empty_returns_empty_dataframe():
    assert unifyTs([]).empty


def test_readInspect_handles_empty_inspect_map():
    from absbox.local.cf import readInspect

    assert readInspect({"inspect": {}}).empty
    assert readInspect({}).empty


def test_readInspect_single_series_still_joins():
    from absbox.local.cf import readInspect
    import pandas as pd

    df = pd.DataFrame([1], columns=["Bal"], index=["2021-01-01"])
    df.index.name = "Date"
    out = readInspect({"inspect": {"Bal": df}})
    assert list(out.columns) == ["Bal"]


def test_readInspect_empty_inspect_with_empty_waterfall_inspect():
    from absbox.local.cf import readInspect
    import pandas as pd

    ws = pd.DataFrame(columns=["Date", "Comment", "DealStats", "Value"]).set_index("Date")
    out = readInspect({"inspect": {}, "waterfallInspect": ws})
    assert out.empty


def test_API_version_endpoint_rejects_non_json(monkeypatch):
    from absbox import client as client_mod
    from absbox.exception import AbsboxError

    class FakeResp:
        def __init__(self, text):
            self.text = text

    for payload in ["<html><body>502 Bad Gateway</body></html>", "", "42", '[1,2]']:
        monkeypatch.setattr(client_mod.requests, "get", lambda *a, **kw: FakeResp(payload))
        with pytest.raises(AbsboxError) as exc:
            client_mod.API("http://localhost:1", check=False)
        assert "invalid JSON response" in str(exc.value) or "not a JSON object" in str(exc.value)


def test_API_version_endpoint_object_payload_still_checked(monkeypatch):
    from absbox import client as client_mod
    from absbox.exception import AbsboxError

    class FakeResp:
        def __init__(self):
            self.text = json.dumps({"_version": "not a version"})

    monkeypatch.setattr(client_mod.requests, "get", lambda *a, **kw: FakeResp())
    with pytest.raises(AbsboxError):
        client_mod.API("http://localhost:1", check=False)


def test_boolLikeFormula_set_has_all_tokens():
    from absbox.local.base import boolLikeFormula

    for token in ["trigger", "事件", "isMostSenior", "最优先", "isPaidOff", "清偿完毕"
                  , "rateTest", "allTest", "anyTest", "比率测试", "任一测试", "所有测试"
                  , "isOutstanding", "isAnyOutstanding", "always"]:
        assert token in boolLikeFormula, token
    assert "所有测试isOutstanding" not in boolLikeFormula


def test_viz_payResidual_with_limit_as_first_action():
    """viz() must not raise UnboundLocalError when the limited payResidual branch
    runs before any branch that binds `_limit` (issue #104)."""
    from absbox.local.chart import viz

    deal_like = {"waterfall": {"Close": [["payResidual", "acc01", "B", 10]]}
                 ,"collection": [("pool", "acc01")]
                 ,"name": "issue104"}
    src = viz(deal_like).source
    assert "payResidual:acc01 -> 10 -> B" in src


def test_viz_payResidual_limit_not_stolen_from_earlier_branch():
    """After another `_limit`-binding branch rendered first, the payResidual edge
    label must use its own limit, not the earlier branch's value."""
    from absbox.local.chart import viz

    actions = [["payFeeResidual", "acc01", "B", 7]
               ,["payResidual", "acc01", "C", 9]]
    deal_like = {"waterfall": {"Close": actions}
                 ,"collection": [("pool", "acc01")]
                 ,"name": "issue104b"}
    src = viz(deal_like).source
    assert "payFeeResidual:acc01 -> 7 -> B" in src
    assert "payResidual:acc01 -> 9 -> C" in src
    assert "payResidual:acc01 -> 7 -> C" not in src


def test_viz_payResidual_chinese_alias_with_limit():
    from absbox.local.chart import viz

    actions = [["支付收益", "账户01", "B", 3]]
    deal_like = {"waterfall": {"正常": actions}
                 ,"collection": [("资金池", "账户01")]
                 ,"name": "issue104c"}
    src = viz(deal_like).source
    assert "支付收益:账户01 -> 3 -> B" in src


def test_mkPre_unknown_operator_raises_parse_error():
    """Unknown operator tokens raise AbsboxParseError (message includes the token),
    not a raw KeyError — covers the op_map[op] sites in mkPre and the rateTest arm
    of mkDs (issue #108)."""
    from absbox.local.component import mkPre, mkDs

    probes = [["date", "==", "2025-01-01"]
              ,["period", "!=", 5]
              ,[("cumPoolDefaultedRate",), "==", ("bondBalance",)]
              ,[("cumPoolDefaultedRate",), "<<", 10000]
              ,[">!", "2025-01-01"]]
    for p in probes:
        with pytest.raises(AbsboxParseError, match=r"Unknown operator"):
            mkPre(p)

    with pytest.raises(AbsboxParseError, match=r"Unknown operator '<>'"):
        mkDs(("rateTest", ("cumPoolDefaultedRate",), "<>", 0.05))


def test_pre_operator_map_valid_tokens_passthrough():
    """Valid operators still map to the same engine enum values (E/G/GE/L/LE)."""
    from absbox.local.component import mkPre, mkDs

    assert mkPre(["date", ">=", "2025-01-01"])["contents"][0] == "GE"
    assert mkPre(["date", "=", "2025-01-01"])["contents"][0] == "E"
    assert mkPre([("cumPoolDefaultedRate",), "<", 10000])["contents"][0] == "L"
    assert mkDs(("rateTest", ("cumPoolDefaultedRate",), ">=", 0.05))["contents"][1] == "GE"


MINI_RUN_RESP = [{"tag": "MDeal", "contents": {
                      "name": "parity",
                      "fees": {"f1": {"feeStmt": None}},
                      "accounts": {"a1": {"accStmt": None}},
                      "bonds": {"B": {"tag": "Bond", "bndStmt": None}},
                      "pool": {"tag": "MultiPool", "contents": {"PoolConsol": {"futureCf": None}}}}}
                 , None, None, None, {}]


def test_read_stores_deal_shape_parity():
    """Generic.read and SPV.read must store `_deal` as the same raw engine
    payload, so shape-sensitive consumers (positionFlow, reports) work for
    both locales (issue #95)."""
    from absbox.local.generic import Generic
    from absbox.local.china import SPV

    g = Generic.read(list(MINI_RUN_RESP))
    s = SPV.read(list(MINI_RUN_RESP))
    assert g["_deal"] is MINI_RUN_RESP[0]
    assert s["_deal"] is MINI_RUN_RESP[0]
    assert "contents" in g["_deal"] and "contents" in s["_deal"]


def test_dealContents_normalizes_shapes():
    from absbox.local.util import dealContents

    raw = {"tag": "MDeal", "contents": {"name": "d"}}
    decoded = {"MDeal": {"name": "d"}}
    assert dealContents({"_deal": raw}) == {"name": "d"}
    assert dealContents({"_deal": decoded}) == {"name": "d"}
    assert dealContents(raw) == {"name": "d"}
    with pytest.raises(AbsboxParseError):
        dealContents({"_deal": {"junk": 1}})


def test_positionFlow_works_for_both_deal_shapes():
    """positionFlow reads origin balances through both _deal storage shapes,
    scaling balance/interest/principal/cash by position/face-per-paper and
    leaving the rate column alone (issue #95)."""
    import pandas as pd
    from absbox.local.util import positionFlow
    from absbox.local.base import english_bondflow_fields

    cols = english_bondflow_fields[1:]
    df = pd.DataFrame([[1000.0, 10.0, 200.0, 0.05, 210.0, 0, 0, 1.0, ""]]
                      , index=["2021-06-01"], columns=cols)

    raw = {"_deal": {"tag": "MDeal", "contents": {"bonds": {"B": {"bndOriginInfo": {"originBalance": 1000.0}}}}}
           ,"bonds": {"B": df}}
    decoded = {"_deal": {"MDeal": {"bonds": {"B": {"bndOriginInfo": {"originBalance": 1000.0}}}}}
               ,"bonds": {"B": df}}

    r = positionFlow(raw, {"B": 5}, facePerPaper=100)
    d = positionFlow(decoded, {"B": 5}, facePerPaper=100)
    for out in (r["B"], d["B"]):
        assert list(out["balance"]) == [500.0]
        assert list(out["interest"]) == [5.0]
        assert list(out["principal"]) == [100.0]
        assert list(out["cash"]) == [105.0]
        assert list(out["rate"]) == [0.05]


def test_report_deal_name_reads_both_shapes():
    from absbox import report as report_mod

    class _Cell:
        children = ()
        attrs = {}

    # dealContents path (the lens extraction used by report only ever worked
    # on the decoded shape; raw shape raised TypeError)
    assert report_mod.dealContents({"_deal": {"tag": "MDeal", "contents": {"name": "cn-deal"}}}).get("name") \
        == "cn-deal"
    assert report_mod.dealContents({"_deal": {"MDeal": {"name": "en-deal"}}}).get("name") == "en-deal"


def test_mkDs_single_contents_formulas():
    # engine constructors with a Maybe argument still need a "contents" key
    assert mkDs(("borrowerNumber",)) == {
        "tag": "CurrentPoolBorrowerNum", "contents": None}
    assert mkDs(("cumPoolDefaultedRate", 3)) == {
        "tag": "CumulativePoolDefaultedRateTill", "contents": [3, None]}
    assert mkDs(("cumPoolDefaultedRate", "P"))["tag"] == "CumulativePoolDefaultedRate"
    with pytest.raises(AbsboxParseError):
        mkPid(3)


def test_mkDs_ledgerTxnAmount_and_floorCap():
    # LedgerTxnAmt takes [String] (Maybe TxnComment)
    assert mkDs(("ledgerTxnAmount", "g")) == {
        "tag": "LedgerTxnAmt", "contents": [["g"], None]}
    assert mkDs(("ledgerTxnAmount", ["g1", "g2"]))["contents"][0] == ["g1", "g2"]
    # FloorAndCap takes three DealStats
    w = mkDs(("floorCap", 0.5, 0.1, ("poolBalance",)))
    assert w["tag"] == "FloorAndCap"
    assert w["contents"][0] == {"tag": "Constant", "contents": 0.5}
    assert w["contents"][1] == {"tag": "Constant", "contents": 0.1}
    assert w["contents"][2]["tag"] == "CurrentPoolBalance"


def test_mkDs_lastFeePaid_maps_to_engine_ctor():
    assert mkDs(("lastFeePaid", "f"))["tag"] == "LastFeePaid"
    assert mkDs(("feePaidAmt", "f"))["tag"] == "FeePaidAmt"


def test_mkAsset_projectedByFactor_validates_portions():
    base = ["ProjectedByFactor", [["2024-09-01", 100]], "MonthEnd"]
    w = mkAsset(base + [(0.5, 0.08), None])
    assert w["contents"][3] == []
    w = mkAsset(base + [(0.5, 0.08), [(0.5, 0.02, 0.01, "LIBOR1M")]])
    assert list(w["contents"][3][0]) == [0.5, 0.02, 0.01, "LIBOR1M"]
    with pytest.raises(AbsboxParseError):
        mkAsset(base + [(0.5, 0.08), [(0.5, 0.02, "LIBOR1M")]])
    with pytest.raises(AbsboxParseError):
        mkAsset(base + [None, []])


def test_mkRateSwap_rateCap_statements_are_auto_tagged():
    swap = {"updateDates": "MonthEnd", "pair": [0.04, ("SOFR1M", 0.0)],
            "base": {"fix": 100}, "start": "2021-06-15", "balance": 100,
            "stmt": [["2021-07-01", 0, 0, 0, 0, 0, ""]]}
    w = mkRateSwap(swap)
    assert w["rsStmt"] == [{"tag": "IrsTxn",
                            "contents": ["2021-07-01", 0, 0, 0, 0, 0, ""]}]
    tagged = [{"tag": "IrsTxn", "contents": ["2021-07-01", 0, 0, 0, 0, 0, ""]}]
    assert mkRateSwap(swap | {"stmt": tagged})["rsStmt"] == tagged
    cap = {"index": "LIBOR6M", "strike": [["2023-01-01", 0.03]], "base": {"fix": 1},
           "start": "2022-01-01", "end": "2025-01-01", "settleDates": "QuarterEnd",
           "rate": 0.03, "stmt": [["2021-07-01", 0, 0, 0, 0, 0, ""]]}
    assert mkRateCap(cap)["rcStmt"][0]["tag"] == "IrsTxn"


def test_read_cf_empty_returns_dataframe():
    from absbox.local.util import _read_cf
    import pandas as pd
    assert isinstance(_read_cf([], "english"), pd.DataFrame)
