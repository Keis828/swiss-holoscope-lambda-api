"""
概要:
    Skyfieldを用いた天体位置計算モジュール
主な仕様:
    - 指定日時・緯度・経度から主要10天体の黄経・星座・逆行情報を計算
    - 星座名は日本語で返却
制限事項:
    - DE421等のephemerisファイルが必要
"""
from typing import List, Dict
from skyfield.api import Loader, Topos
from skyfield.framelib import ecliptic_frame
from datetime import datetime, timezone
import os

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


def calculate_planets(
    dt_utc: datetime,
    latitude: float,
    longitude: float,
    ephemeris_path: str = None,
    eph=None,
    ts=None
) -> List[Dict]:
    """
    指定日時・緯度・経度で主要10天体の黄経・星座・逆行情報を計算
    :param dt_utc: datetime UTC日時
    :param latitude: float 緯度
    :param longitude: float 経度
    :param ephemeris_path: str de432s.bsp等のパス（省略時はプロジェクトルートのde432s.bsp）
    :param eph: Skyfield Ephemerisオブジェクト（省略時はファイルからロード）
    :param ts: Skyfield Timescaleオブジェクト（省略時はLoaderから生成）
    :return: List[Dict] 各天体の情報
    """
    # プロジェクトルートのde432s.bspを絶対パスで指定
    if eph is None or ts is None:
        if ephemeris_path is None:
            # Lambda環境では/tmpディレクトリも確認
            tmp_eph_path = '/tmp/de432s.bsp'
            if os.path.exists(tmp_eph_path):
                eph_path = tmp_eph_path
            else:
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                eph_path = os.path.join(root_dir, 'de432s.bsp')
        else:
            eph_path = ephemeris_path
        if not os.path.exists(eph_path):
            raise FileNotFoundError(f"Ephemeris file not found: {eph_path}")
        load = Loader(os.path.dirname(eph_path))
        eph = load(os.path.basename(eph_path))
        ts = load.timescale()

    t = ts.from_datetime(dt_utc)
    observer = Topos(latitude_degrees=latitude, longitude_degrees=longitude)

    # Skyfieldの天体名と日本語名の対応
    planet_map = [
        (10, "太陽"),    # 10 SUN
        (301, "月"),     # 301 MOON
        (199, "水星"),   # 199 MERCURY
        (299, "金星"),   # 299 VENUS
        (4, "火星"),     # 4 MARS BARYCENTER
        (5, "木星"),     # 5 JUPITER BARYCENTER
        (6, "土星"),     # 6 SATURN BARYCENTER
        (7, "天王星"),   # 7 URANUS BARYCENTER
        (8, "海王星"),   # 8 NEPTUNE BARYCENTER
        (9, "冥王星"),   # 9 PLUTO BARYCENTER
    ]
    results = []
    for planet_id, jp_name in planet_map:
        planet = eph[planet_id]
        astrometric = eph["earth"].at(t).observe(planet)
        ecl = astrometric.frame_latlon(ecliptic_frame)
        lon = ecl[1].degrees % 360
        lat = ecl[0].degrees
        # 逆行判定: 1日前との差分で判定（簡易）
        t_prev = ts.from_datetime(dt_utc.replace(day=max(1, dt_utc.day-1)))
        astrometric_prev = eph["earth"].at(t_prev).observe(planet)
        lon_prev = astrometric_prev.frame_latlon(ecliptic_frame)[1].degrees % 360
        # numpy.float64 間の比較になる可能性があるため、Pythonの bool に明示変換
        retrograde = bool(float(lon) < float(lon_prev))
        results.append({
            "name_jp": jp_name,
            "name_en": str(planet_id),
            "longitude": lon,
            "latitude": lat,
            "sign": get_zodiac_sign_jp(lon),
            "retrograde": retrograde
        })
    return results 