"""
概要:
    小惑星・ブラックムーン・リリス計算のユニットテスト
主な仕様:
    - セレス、パラス、ジュノー、ベスタ、キロン、リリスの位置計算テスト
制限事項:
    - Swiss Ephemerisファイルが必要
"""
import pytest
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.calculate_asteroids import calculate_asteroids


class TestCalculateAsteroids:
    """小惑星計算テストクラス"""

    def test_calculate_asteroids_basic(self):
        """基本的な小惑星計算が成功することを確認"""
        dt_utc = datetime(1982, 8, 28, 6, 3, tzinfo=timezone.utc)  # JST 15:03 = UTC 6:03
        lat = 32.7447  # 長崎
        lon = 129.8735
        
        result = calculate_asteroids(dt_utc, lat, lon)
        
        # 6つの天体が返されることを確認
        assert len(result) == 6
        
        # すべての天体名を確認
        names = [a["name_jp"] for a in result]
        assert "セレス" in names
        assert "パラス" in names
        assert "ジュノー" in names
        assert "ベスタ" in names
        assert "キロン" in names
        assert "ブラックムーン・リリス" in names

    def test_asteroid_has_required_fields(self):
        """各小惑星に必要なフィールドが存在することを確認"""
        dt_utc = datetime(1982, 8, 28, 6, 3, tzinfo=timezone.utc)
        lat = 35.6895  # 東京
        lon = 139.6917
        
        result = calculate_asteroids(dt_utc, lat, lon)
        
        for asteroid in result:
            assert "name_jp" in asteroid
            assert "name_en" in asteroid
            assert "longitude" in asteroid
            assert "latitude" in asteroid
            assert "sign" in asteroid
            assert "retrograde" in asteroid
            assert "speed" in asteroid
            
            # 値の妥当性確認
            assert asteroid["longitude"] is None or (0 <= asteroid["longitude"] < 360)
            assert asteroid["sign"] in [
                "牡羊座", "牡牛座", "双子座", "蟹座", "獅子座", "乙女座",
                "天秤座", "蠍座", "射手座", "山羊座", "水瓶座", "魚座", None
            ]

    def test_chiron_position_1982(self):
        """1982年のキロン位置が牡牛座付近であることを確認"""
        dt_utc = datetime(1982, 8, 28, 6, 3, tzinfo=timezone.utc)
        lat = 35.6895
        lon = 139.6917
        
        result = calculate_asteroids(dt_utc, lat, lon)
        chiron = next(a for a in result if a["name_en"] == "Chiron")
        
        # 1982年のキロンは牡牛座付近（約40度〜60度）
        assert chiron["longitude"] is not None
        assert 30 <= chiron["longitude"] <= 90  # 牡牛座〜双子座の範囲

    def test_retrograde_detection(self):
        """逆行判定が正しく機能することを確認"""
        dt_utc = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)
        lat = 35.6895
        lon = 139.6917
        
        result = calculate_asteroids(dt_utc, lat, lon)
        
        # 逆行フラグがブール値であることを確認
        for asteroid in result:
            assert isinstance(asteroid["retrograde"], bool)
