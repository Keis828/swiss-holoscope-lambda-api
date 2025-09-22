"""
概要:
    holoscope_serviceの天体計算ロジックの単体テスト
主な仕様:
    - 主要な入力パターンで天体計算が正しく動作するか確認
制限事項:
    - ハウス計算等はダミーのまま
"""
import pytest
from src.holoscope_service import HoloscopeService

def test_holoscope_create_basic():
    """
    基本的な天体計算が正しく動作するかテスト
    """
    req = {
        "name": "テスト太郎",
        "date": "199001011200",
        "location": {
            "name": "東京",
            "latitude": 35.6895,
            "longitude": 139.6917,
            "tz": "Asia/Tokyo"
        },
        "gender": 1,
        "isTimeUnknown": False
    }
    service = HoloscopeService()
    result = service.create(req)
    # 惑星が10個返ること
    assert len(result.planets) == 10
    # 惑星名が日本語であること
    for p in result.planets:
        assert p.name in ["太陽", "月", "水星", "金星", "火星", "木星", "土星", "天王星", "海王星", "冥王星"]
    # 星座名が日本語であること
    for p in result.planets:
        assert p.sign in [
            "牡羊座", "牡牛座", "双子座", "蟹座", "獅子座", "乙女座",
            "天秤座", "蠍座", "射手座", "山羊座", "水瓶座", "魚座"
        ]

def test_holoscope_house_assignment():
    """
    惑星のハウス割り当てが正しく行われているかテスト
    """
    req = {
        "name": "テスト太郎",
        "date": "199001011200",
        "location": {
            "name": "東京",
            "latitude": 35.6895,
            "longitude": 139.6917,
            "tz": "Asia/Tokyo"
        },
        "gender": 1,
        "isTimeUnknown": False
    }
    service = HoloscopeService()
    result = service.create(req)
    # 各惑星のhouseが1〜12のいずれかであること
    for p in result.planets:
        assert 1 <= p.house <= 12

def test_holoscope_elements_qualities():
    """
    エレメント・3区分の集計が正しく行われているかテスト
    """
    req = {
        "name": "テスト太郎",
        "date": "199001011200",
        "location": {
            "name": "東京",
            "latitude": 35.6895,
            "longitude": 139.6917,
            "tz": "Asia/Tokyo"
        },
        "gender": 1,
        "isTimeUnknown": False
    }
    service = HoloscopeService()
    result = service.create(req)
    # エレメント合計が10（惑星数）
    total_elements = result.elements.fire + result.elements.earth + result.elements.air + result.elements.water
    assert total_elements == 10
    # 3区分合計も10
    total_qualities = result.qualities.cardinal + result.qualities.fixed + result.qualities.mutable
    assert total_qualities == 10 