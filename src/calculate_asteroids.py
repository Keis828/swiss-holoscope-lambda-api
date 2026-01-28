"""
概要:
    Swiss Ephemerisを用いた小惑星・ブラックムーン・リリス計算モジュール
主な仕様:
    - セレス、パラス、ジュノー、ベスタ、キロンの位置計算
    - ブラックムーン・リリス（平均リリス）の位置計算
    - 黄経・星座・逆行情報を返却
制限事項:
    - Swiss Ephemerisファイル（sepl_18.se1等）が必要
"""
from typing import List, Dict
from datetime import datetime, timezone, timedelta
import os

try:
    import swisseph as swe
except ImportError:
    swe = None

# 黄経から日本語星座名を返す
zodiac_signs_jp = [
    "牡羊座", "牡牛座", "双子座", "蟹座", "獅子座", "乙女座",
    "天秤座", "蠍座", "射手座", "山羊座", "水瓶座", "魚座"
]


def get_zodiac_sign_jp(longitude_deg: float) -> str:
    """
    黄経 (度数) から日本語の星座名を返す
    :param longitude_deg: float 黄経
    :return: str 星座名
    """
    index = int(longitude_deg // 30) % 12
    return zodiac_signs_jp[index]


def datetime_to_jd(dt_utc: datetime) -> float:
    """
    UTC日時をユリウス日に変換
    :param dt_utc: datetime UTC日時
    :return: float ユリウス日
    """
    # swisseph.julday(year, month, day, hour)
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)
    return jd


def calculate_asteroids(
    dt_utc: datetime,
    latitude: float,
    longitude: float,
    ephemeris_path: str = None
) -> List[Dict]:
    """
    小惑星（セレス、パラス、ジュノー、ベスタ、キロン）と
    ブラックムーン・リリスの位置を計算
    :param dt_utc: datetime UTC日時
    :param latitude: float 緯度
    :param longitude: float 経度
    :param ephemeris_path: str Swiss Ephemerisファイルのディレクトリパス
    :return: List[Dict] 各天体の情報
    """
    if swe is None:
        raise ImportError("pyswisseph is not installed. Run: pip install pyswisseph")

    # Swiss Ephemerisファイルのパス設定
    if ephemeris_path is None:
        # Lambda環境では/tmpディレクトリも確認
        tmp_path = '/tmp'
        if os.path.exists(os.path.join(tmp_path, 'sepl_18.se1')):
            eph_path = tmp_path
        else:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            eph_path = root_dir
    else:
        eph_path = ephemeris_path

    # Swiss Ephemerisパスを設定
    swe.set_ephe_path(eph_path)

    # ユリウス日に変換
    jd = datetime_to_jd(dt_utc)
    jd_prev = datetime_to_jd(dt_utc - timedelta(days=1))

    # 小惑星・感受点のマッピング
    # Swiss Ephemeris天体番号:
    # - セレス: swe.CERES (1)
    # - パラス: swe.PALLAS (2)
    # - ジュノー: swe.JUNO (3)
    # - ベスタ: swe.VESTA (4)
    # - キロン: swe.CHIRON (15)
    # - 平均リリス (Mean Lunar Apogee): swe.MEAN_APOG (12)
    # - 真リリス (True Lunar Apogee): swe.OSCU_APOG (13)
    asteroid_map = [
        (swe.CERES, "セレス", "Ceres"),
        (swe.PALLAS, "パラス", "Pallas"),
        (swe.JUNO, "ジュノー", "Juno"),
        (swe.VESTA, "ベスタ", "Vesta"),
        (swe.CHIRON, "キロン", "Chiron"),
        (swe.MEAN_APOG, "ブラックムーン・リリス", "Black Moon Lilith"),
    ]

    results = []
    for body_id, jp_name, en_name in asteroid_map:
        try:
            # 現在位置の計算
            # swe.calc_ut returns ((longitude, latitude, distance, speed_lon, speed_lat, speed_dist), flags)
            result, flags = swe.calc_ut(jd, body_id)
            lon = result[0] % 360
            lat = result[1]
            speed = result[3]  # 黄経の速度（度/日）

            # 逆行判定: 速度が負なら逆行
            retrograde = bool(speed < 0)

            results.append({
                "name_jp": jp_name,
                "name_en": en_name,
                "longitude": float(lon),
                "latitude": float(lat),
                "sign": get_zodiac_sign_jp(lon),
                "retrograde": retrograde,
                "speed": float(speed)
            })
        except Exception as e:
            print(f"calculate_asteroids: Error calculating {jp_name}: {e}")
            # エラー時はスキップせず、Noneを含むエントリを追加
            results.append({
                "name_jp": jp_name,
                "name_en": en_name,
                "longitude": None,
                "latitude": None,
                "sign": None,
                "retrograde": None,
                "speed": None,
                "error": str(e)
            })

    return results
