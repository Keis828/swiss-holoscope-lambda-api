"""
概要:
    HoloscopeService.create の結合テスト
主な仕様:
    - 最低限の入力で、想定するレスポンス構造のオブジェクトが生成されること
    - 惑星10件、ハウス12件、ASC/DC/MC/IC、エレメント・3区分が揃っていること
制限事項:
    - 数値の完全一致は検証しない（環境差の許容）
"""

from __future__ import annotations

from typing import Dict
from datetime import datetime

import os
import pytest

from src.holoscope_service import HoloscopeService


def test_holoscope_service_create_basic(sampleDatetimeUtc: datetime, tokyoCoords, ephemerisAndTimescale):
    """
    HoloscopeService.create が基本的なレスポンス構造を返すことを確認する。
    """
    eph, ts = ephemerisAndTimescale
    lat, lon = tokyoCoords

    # 入力をサービス仕様に合わせて用意
    req = {
        "name": "テストユーザー",
        "date": sampleDatetimeUtc.strftime("%Y%m%d%H%M"),
        "location": {
            "name": "東京都",
            "latitude": lat,
            "longitude": lon,
            "tz": "Asia/Tokyo",
        },
        "system": "placidus",
        "gender": 0,
        "isTimeUnknown": False,
    }

    # 依存リソースを先行初期化済みのインスタンスを渡す
    service = HoloscopeService()
    service.eph = eph
    service.ts = ts

    result = service.create(req)

    # userInfo
    assert result.userInfo is not None
    assert result.userInfo.birthdate == req["date"]

    # planets
    assert result.planets and len(result.planets) == 10
    for p in result.planets:
        assert p.name and isinstance(p.longitude, float)
        assert 0.0 <= (p.longitude % 360.0) < 360.0

    # houses
    assert result.houses and len(result.houses) == 12
    nums = [h.number for h in result.houses]
    assert nums == list(range(1, 13))

    # angles
    assert result.ascendant and result.descendant and result.mc and result.ic

    # elements / qualities
    assert result.elements is not None
    assert result.qualities is not None


def testNagasaki19820828_1503Signs(ephemerisAndTimescale):
    """
    概要:
        1982/08/28 15:03（JST）長崎生まれのホロスコープで、
        太陽星座=乙女座、月星座=射手座であることを検証する。
    主な仕様:
        - 入力: date="198208281503", location=長崎県(緯度32.7503, 経度129.8777, tz=Asia/Tokyo)
        - 検証: 惑星リストから太陽と月を取り出し sign を確認
    制限事項:
        - 実装の天文計算はBSP/アルゴリズム差で微小差があり得るが、星座境界の判定は期待に一致する想定
    失敗時のエラーメッセージ:
        - 関数名・入力値・実際の星座名を詳細に出力
    """
    eph, ts = ephemerisAndTimescale

    # 入力をサービス仕様に合わせて用意（長崎県）
    req = {
        "name": "検証ユーザー",
        "date": "198208281503",
        "location": {
            "name": "長崎県",
            "latitude": 32.7503,
            "longitude": 129.8777,
            "tz": "Asia/Tokyo",
        },
        "system": "placidus",
        "gender": 0,
        "isTimeUnknown": False,
    }

    service = HoloscopeService()
    # 事前に初期化済みのeph/tsを差し替えて、テストの再現性と速度を確保
    service.eph = eph
    service.ts = ts

    result = service.create(req)

    # 太陽と月を抽出
    sun = next((p for p in result.planets if p.name == "太陽"), None)
    moon = next((p for p in result.planets if p.name == "月"), None)
    
    assert sun is not None, "testNagasaki19820828_1503Signs: 惑星'太陽'が結果に存在しません req={}".format(req)
    assert moon is not None, "testNagasaki19820828_1503Signs: 惑星'月'が結果に存在しません req={}".format(req)

    # 期待する星座
    expected_sun_sign = "乙女座"
    expected_moon_sign = "射手座"

    assert (
        sun.sign == expected_sun_sign
    ), "testNagasaki19820828_1503Signs: 太陽星座が一致しません expected='{}' actual='{}' req={}".format(
        expected_sun_sign, sun.sign, req
    )
    assert (
        moon.sign == expected_moon_sign
    ), "testNagasaki19820828_1503Signs: 月星座が一致しません expected='{}' actual='{}' req={}".format(
        expected_moon_sign, moon.sign, req
    )


