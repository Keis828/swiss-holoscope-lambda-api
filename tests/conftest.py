"""
概要:
    pytest 全体で利用する共通フィクスチャ群
主な仕様:
    - SkyfieldのEphemeris/Timescaleを一度だけ初期化して共有
    - /tmp に `de432s.bsp` が無ければプロジェクト直下からコピー
    - テストをSkyfieldエンジン固定（HOUSE_ENGINE=SKYFIELD）で実行
    - サンプルの日時・緯度経度（東京）を提供
制限事項:
    - 実際の天文結果は環境差による微小誤差が生じるため、角度比較は許容誤差で判定
"""

from __future__ import annotations

from typing import Tuple
import os
import sys
import shutil
from datetime import datetime, timezone

import pytest
from skyfield.api import Loader

# 重要: テスト収集前に 'src' を解決できるよう、プロジェクトルートを sys.path に追加
_HERE = os.path.abspath(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture(scope="session", autouse=True)
def ensureSkyfieldEnv() -> None:
    """
    テスト実行時の環境変数を調整する。
    - HOUSE_ENGINE を SKYFIELD に固定（pyswisseph依存を避ける）
    """
    os.environ["HOUSE_ENGINE"] = "SKYFIELD"
    # srcレイアウト対応: プロジェクトルートをsys.pathに追加し、
    # `from src.xxx import ...` をインポート可能にする
    try:
        import sys
        here = os.path.abspath(os.path.dirname(__file__))
        project_root = os.path.abspath(os.path.join(here, os.pardir))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
    except Exception:
        # ここでの例外はテスト本体に影響しないよう握りつぶす
        pass


@pytest.fixture(scope="session")
def ephemerisAndTimescale() -> Tuple[object, object]:
    """
    SkyfieldのEphemerisとTimescaleを初期化して返す。
    優先順:
      1) `/tmp/de432s.bsp` が存在すれば利用
      2) S3 から `EPHEMERIS_S3_BUCKET`/`EPHEMERIS_S3_KEY` でダウンロード
      3) `JPL_BSP_URL`（既定: NAIF de432s）からHTTPダウンロード
      4) 取得不能ならテストをスキップ
    Returns:
        Tuple[Ephemeris, Timescale]
    """
    tmp_path = "/tmp/de432s.bsp"
    if not os.path.exists(tmp_path):
        # S3 からの取得
        bucket = os.environ.get("EPHEMERIS_S3_BUCKET")
        key = os.environ.get("EPHEMERIS_S3_KEY", "de432s.bsp")
        if bucket:
            try:
                import boto3  # type: ignore
                s3 = boto3.client("s3")
                s3.download_file(bucket, key, tmp_path)
            except Exception:
                pass
        # HTTP からの取得
        if not os.path.exists(tmp_path):
            url = os.environ.get(
                "JPL_BSP_URL",
                "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de432s.bsp",
            )
            try:
                import requests  # type: ignore
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                with open(tmp_path, "wb") as f:
                    f.write(resp.content)
            except Exception:
                pytest.skip(
                    "Ephemeris file could not be prepared. Set EPHEMERIS_S3_BUCKET/KEY or JPL_BSP_URL."
                )

    load = Loader(os.path.dirname(tmp_path))
    eph = load(os.path.basename(tmp_path))
    ts = load.timescale()
    return eph, ts


@pytest.fixture(scope="session")
def tokyoCoords() -> Tuple[float, float]:
    """
    東京（東京都庁付近）の緯度・経度を返す。
    Returns:
        Tuple[float, float]: (latitude, longitude)
    """
    return 35.6895, 139.6917


@pytest.fixture(scope="session")
def sampleDatetimeUtc() -> datetime:
    """
    サンプルのUTC日時を返す。
    Returns:
        datetime: タイムゾーン付きUTC日時
    備考:
        テストの再現性のため固定日時（2000-01-01 00:00:00Z）
    """
    return datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def normalizeDegrees(value: float) -> float:
    """
    角度を [0, 360) に正規化する簡便関数。
    Args:
        value (float): 角度（度）
    Returns:
        float: 0以上360未満に正規化した角度
    """
    v = value % 360.0
    return v + 360.0 if v < 0 else v


@pytest.fixture(scope="session")
def deg() -> callable:
    """
    角度正規化ヘルパを提供する。
    Returns:
        callable: normalizeDegrees関数
    """
    return normalizeDegrees


