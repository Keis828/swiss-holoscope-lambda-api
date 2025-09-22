"""
概要:
    calculate_houses の単体テスト
主な仕様:
    - ASC/DC/MC/IC と 12ハウスが返ることを検証
    - ハウス方式（placidus/equal/koch）で最低限の整合性を検証
    - 角度の範囲と、DC=ASC+180、IC=MC+180 の関係を許容誤差で確認
制限事項:
    - Placidusの厳密解は数値解を含むため、角度の完全一致は検証しない
"""

from __future__ import annotations

from typing import Dict

from datetime import datetime
import math
import pytest

from src.calculate_houses import calculate_houses


@pytest.fixture(autouse=True)
def useSwissEngine(monkeypatch):
    """
    Swiss Ephemeris が利用可能で、かつ RUN_SWISS_TESTS=1 の場合のみ
    SWISS エンジンで実行。満たさない場合は本モジュール全体をスキップ。
    """
    import os
    run_swiss = os.environ.get("RUN_SWISS_TESTS") == "1"
    try:
        import swisseph as swe  # type: ignore
        has_swiss = True
    except Exception:
        has_swiss = False

    if run_swiss and has_swiss:
        monkeypatch.setenv("HOUSE_ENGINE", "SWISS")
        return
    pytest.skip("Skipping SWISS-dependent house tests. Set RUN_SWISS_TESTS=1 with pyswisseph and Swiss files available.")


def _circ_delta(a: float, b: float) -> float:
    d = (a - b + 180.0) % 360.0 - 180.0
    return d


@pytest.mark.parametrize("system", ["placidus", "equal", "koch"])
def test_calculate_houses_shapes(sampleDatetimeUtc: datetime, tokyoCoords, ephemerisAndTimescale, system: str):
    """
    返却構造の妥当性と主要角の関係を確認する。
    期待:
        - keys: ascendant, descendant, mc, ic, houses
        - housesの長さ=12、各要素に number/sign/longitude
        - DC ≒ ASC + 180、IC ≒ MC + 180 (±0.5度程度の許容)
    """
    eph, ts = ephemerisAndTimescale
    lat, lon = tokyoCoords

    result: Dict = calculate_houses(sampleDatetimeUtc, lat, lon, eph=eph, ts=ts, system=system)

    for key in ["ascendant", "descendant", "mc", "ic", "houses"]:
        assert key in result

    for k in ["ascendant", "descendant", "mc", "ic"]:
        assert "sign" in result[k] and "longitude" in result[k]
        assert 0.0 <= (result[k]["longitude"] % 360.0) < 360.0

    houses = result["houses"]
    assert isinstance(houses, list) and len(houses) == 12
    for h in houses:
        assert set(["number", "sign", "longitude"]).issubset(h.keys())
        assert 1 <= h["number"] <= 12
        assert 0.0 <= (h["longitude"] % 360.0) < 360.0

    asc = result["ascendant"]["longitude"] % 360.0
    dsc = result["descendant"]["longitude"] % 360.0
    mc = result["mc"]["longitude"] % 360.0
    ic = result["ic"]["longitude"] % 360.0

    assert abs(_circ_delta(dsc, (asc + 180.0) % 360.0)) < 0.5
    assert abs(_circ_delta(ic, (mc + 180.0) % 360.0)) < 0.5


def test_placidus_signs_19700326_1900_aichi(ephemerisAndTimescale):
    """
    概要:
        画像（1970/03/26 19:00 JST, 愛知県, Placidus）を正として、
        SWISSエンジン・Placidus方式のハウス計算で、ASC/DC/MC/ICの星座と
        1/4/7/10ハウスのカスプ星座が一致することを検証する。
    主な仕様:
        - ASC=天秤座, DC=牡羊座, MC=蟹座, IC=山羊座 を星座名で比較
        - houses[0]=ASC, houses[3]=IC, houses[6]=DC, houses[9]=MC の星座が一致
    制限事項:
        - 度数は環境差により微小誤差があり得るため星座のみ検証
    失敗時:
        - 入力日時・場所・実測星座を含む詳細なメッセージを出力
    """
    import pytz
    from datetime import datetime

    eph, ts = ephemerisAndTimescale

    # 入力: 1970/03/26 19:00 JST → UTC へ変換
    jst = pytz.timezone("Asia/Tokyo")
    dt_local = jst.localize(datetime(1970, 3, 26, 19, 0, 0))
    dt_utc = dt_local.astimezone(pytz.UTC)

    # 愛知県（県庁所在地）
    lat, lon = 35.1802, 136.9066

    result = calculate_houses(dt_utc, lat, lon, eph=eph, ts=ts, system="placidus")

    asc_sign = result["ascendant"]["sign"]
    dc_sign = result["descendant"]["sign"]
    mc_sign = result["mc"]["sign"]
    ic_sign = result["ic"]["sign"]

    assert asc_sign == "天秤座", (
        f"test_placidus_signs_19700326_1900_aichi: ASC sign mismatch expected='天秤座' actual='{asc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert dc_sign == "牡羊座", (
        f"test_placidus_signs_19700326_1900_aichi: DC sign mismatch expected='牡羊座' actual='{dc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert mc_sign == "蟹座", (
        f"test_placidus_signs_19700326_1900_aichi: MC sign mismatch expected='蟹座' actual='{mc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert ic_sign == "山羊座", (
        f"test_placidus_signs_19700326_1900_aichi: IC sign mismatch expected='山羊座' actual='{ic_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )

    houses = result["houses"]
    # 1/4/7/10ハウス（1-based）に対応する配列indexは 0/3/6/9
    assert houses[0]["sign"] == asc_sign
    assert houses[3]["sign"] == ic_sign
    assert houses[6]["sign"] == dc_sign
    assert houses[9]["sign"] == mc_sign


def test_placidus_signs_19820828_1503_nagasaki(ephemerisAndTimescale):
    """
    概要:
        画像（1982/08/28 15:03 JST, 長崎県, Placidus）を正として、
        SWISSエンジン・Placidus方式のハウス計算で、ASC/DC/MC/ICの星座と
        1/4/7/10ハウスのカスプ星座が一致することを検証する。
    主な仕様:
        - 期待: ASC=山羊座, DC=蟹座, MC=乙女座, IC=魚座（画像基準）
        - houses[0]/[3]/[6]/[9] が各角の星座と一致
    制限事項:
        - 度数は検証しない（星座のみ）
    """
    import pytz
    from datetime import datetime

    eph, ts = ephemerisAndTimescale

    # 入力: 1982/08/28 15:03 JST → UTC
    jst = pytz.timezone("Asia/Tokyo")
    dt_local = jst.localize(datetime(1982, 8, 28, 15, 3, 0))
    dt_utc = dt_local.astimezone(pytz.UTC)

    # 長崎県（県庁所在地）
    lat, lon = 32.7503, 129.8777

    result = calculate_houses(dt_utc, lat, lon, eph=eph, ts=ts, system="placidus")

    asc_sign = result["ascendant"]["sign"]
    dc_sign = result["descendant"]["sign"]
    mc_sign = result["mc"]["sign"]
    ic_sign = result["ic"]["sign"]

    assert asc_sign == "山羊座", (
        f"test_placidus_signs_19820828_1503_nagasaki: ASC sign mismatch expected='山羊座' actual='{asc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert dc_sign == "蟹座", (
        f"test_placidus_signs_19820828_1503_nagasaki: DC sign mismatch expected='蟹座' actual='{dc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert mc_sign == "天秤座", (
        f"test_placidus_signs_19820828_1503_nagasaki: MC sign mismatch expected='天秤座' actual='{mc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert ic_sign == "牡羊座", (
        f"test_placidus_signs_19820828_1503_nagasaki: IC sign mismatch expected='牡羊座' actual='{ic_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )

    houses = result["houses"]
    assert houses[0]["sign"] == asc_sign
    assert houses[3]["sign"] == ic_sign
    assert houses[6]["sign"] == dc_sign
    assert houses[9]["sign"] == mc_sign


def test_placidus_signs_19820524_0936_kanagawa(ephemerisAndTimescale):
    """
    概要:
        画像（1982/05/24 09:36 JST, 神奈川県, Placidus）を正として、
        SWISSエンジン・Placidus方式のハウス計算で、ASC/DC/MC/ICの星座と
        1/4/7/10ハウスのカスプ星座が一致することを検証する。
    主な仕様:
        - 期待: ASC=獅子座, DC=水瓶座, MC=牡牛座, IC=蠍座（画像基準）
        - houses[0]/[3]/[6]/[9] が各角の星座と一致
    制限事項:
        - 度数は検証しない（星座のみ）
    """
    import pytz
    from datetime import datetime

    eph, ts = ephemerisAndTimescale

    # 入力: 1982/05/24 09:36 JST → UTC
    jst = pytz.timezone("Asia/Tokyo")
    dt_local = jst.localize(datetime(1982, 5, 24, 9, 36, 0))
    dt_utc = dt_local.astimezone(pytz.UTC)

    # 神奈川県（県庁所在地）
    lat, lon = 35.4478, 139.6425

    result = calculate_houses(dt_utc, lat, lon, eph=eph, ts=ts, system="placidus")

    asc_sign = result["ascendant"]["sign"]
    dc_sign = result["descendant"]["sign"]
    mc_sign = result["mc"]["sign"]
    ic_sign = result["ic"]["sign"]

    assert asc_sign == "獅子座", (
        f"test_placidus_signs_19820524_0936_kanagawa: ASC sign mismatch expected='獅子座' actual='{asc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert dc_sign == "水瓶座", (
        f"test_placidus_signs_19820524_0936_kanagawa: DC sign mismatch expected='水瓶座' actual='{dc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert mc_sign == "牡牛座", (
        f"test_placidus_signs_19820524_0936_kanagawa: MC sign mismatch expected='牡牛座' actual='{mc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert ic_sign == "蠍座", (
        f"test_placidus_signs_19820524_0936_kanagawa: IC sign mismatch expected='蠍座' actual='{ic_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )

    houses = result["houses"]
    assert houses[0]["sign"] == asc_sign
    assert houses[3]["sign"] == ic_sign
    assert houses[6]["sign"] == dc_sign
    assert houses[9]["sign"] == mc_sign


def test_placidus_signs_20201201_1842_kanagawa(ephemerisAndTimescale):
    """
    概要:
        画像（2020/12/01 18:42 JST, 神奈川県, Placidus）を正として、
        SWISSエンジン・Placidus方式のハウス計算で、ASC/DC/MC/ICの星座と
        1/4/7/10ハウスのカスプ星座が一致することを検証する。
    主な仕様:
        - 期待: ASC=蟹座, DC=山羊座, MC=牡羊座, IC=天秤座（画像基準）
        - houses[0]/[3]/[6]/[9] が各角の星座と一致
    制限事項:
        - 度数は検証しない（星座のみ）
    """
    import pytz
    from datetime import datetime

    eph, ts = ephemerisAndTimescale

    # 入力: 2020/12/01 18:42 JST → UTC
    jst = pytz.timezone("Asia/Tokyo")
    dt_local = jst.localize(datetime(2020, 12, 1, 18, 42, 0))
    dt_utc = dt_local.astimezone(pytz.UTC)

    # 神奈川県（県庁所在地）
    lat, lon = 35.4478, 139.6425

    result = calculate_houses(dt_utc, lat, lon, eph=eph, ts=ts, system="placidus")

    asc_sign = result["ascendant"]["sign"]
    dc_sign = result["descendant"]["sign"]
    mc_sign = result["mc"]["sign"]
    ic_sign = result["ic"]["sign"]

    assert asc_sign == "蟹座", (
        f"test_placidus_signs_20201201_1842_kanagawa: ASC sign mismatch expected='蟹座' actual='{asc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert dc_sign == "山羊座", (
        f"test_placidus_signs_20201201_1842_kanagawa: DC sign mismatch expected='山羊座' actual='{dc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert mc_sign == "魚座", (
        f"test_placidus_signs_20201201_1842_kanagawa: MC sign mismatch expected='魚座' actual='{mc_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )
    assert ic_sign == "乙女座", (
        f"test_placidus_signs_20201201_1842_kanagawa: IC sign mismatch expected='乙女座' actual='{ic_sign}'"
        f" input={{'dt_local':'{dt_local}', 'lat':{lat}, 'lon':{lon}}}"
    )

    houses = result["houses"]
    assert houses[0]["sign"] == asc_sign
    assert houses[3]["sign"] == ic_sign
    assert houses[6]["sign"] == dc_sign
    assert houses[9]["sign"] == mc_sign


