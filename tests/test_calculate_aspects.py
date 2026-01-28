import pytest
from src.calculate_aspects import calculate_aspects
from src.holoscope_model import PlanetInfo

def test_calculate_major_aspects_conjunction():
    # 太陽と月が同じ位置 (Conjunction 0度)
    p1 = PlanetInfo(name="太陽", longitude=100.0)
    p2 = PlanetInfo(name="月", longitude=105.0) # 差5度 (Conjunction orb 8度以内)
    
    aspects = calculate_aspects([p1, p2])
    
    assert len(aspects) == 1
    assert aspects[0].type == "Conjunction"
    assert aspects[0].aspect_type == "major"
    assert aspects[0].orb == 5.0

def test_calculate_major_aspects_opposition():
    # 太陽と月が反対 (Opposition 180度)
    p1 = PlanetInfo(name="太陽", longitude=100.0)
    p2 = PlanetInfo(name="月", longitude=285.0) # 差185度 -> 175度 (Opposition orb 8度以内)
    
    aspects = calculate_aspects([p1, p2])
    
    # 285 - 100 = 185 -> 180との差 5度
    
    assert len(aspects) == 1
    assert aspects[0].type == "Opposition"
    assert aspects[0].orb == 5.0

def test_calculate_minor_aspects_quincunx():
    # 水星と木星が150度 (Quincunx)
    # Orb limit for non-luminaries minor aspect is 3.0
    p1 = PlanetInfo(name="水星", longitude=10.0)
    p2 = PlanetInfo(name="木星", longitude=161.0) # 差151度 (誤差1度)
    
    aspects = calculate_aspects([p1, p2])
    
    assert len(aspects) == 1
    assert aspects[0].type == "Quincunx"
    assert aspects[0].aspect_type == "minor"
    assert aspects[0].orb == 1.0

def test_no_aspect():
    # アスペクトなし
    p1 = PlanetInfo(name="太陽", longitude=100.0)
    p2 = PlanetInfo(name="金星", longitude=120.0) # 差20度 (該当アスペクトなし)
    
    aspects = calculate_aspects([p1, p2])
    
    assert len(aspects) == 0

def test_orb_limit():
    # オーブ外
    # Trine (120度) for non-luminaries (orb 6.0)
    p1 = PlanetInfo(name="火星", longitude=0.0)
    p2 = PlanetInfo(name="木星", longitude=127.0) # 差127度 (誤差7度 -> オーブ外)
    
    aspects = calculate_aspects([p1, p2])
    assert len(aspects) == 0
    
    # オーブ内ギリギリ
    p3 = PlanetInfo(name="木星", longitude=126.0) # 差126度 (誤差6度 -> オーブ内)
    aspects = calculate_aspects([p1, p3])
    assert len(aspects) == 1
    assert aspects[0].type == "Trine"

def test_luminary_orb():
    # 太陽(Luminary)の場合、メジャーアスペクトのオーブは8.0
    p1 = PlanetInfo(name="太陽", longitude=0.0)
    p2 = PlanetInfo(name="火星", longitude=127.0) # 差127度 (誤差7度 -> 8度以内なのでOK)
    
    aspects = calculate_aspects([p1, p2])
    assert len(aspects) == 1
    assert aspects[0].type == "Trine"
