"""
概要:
    天体間のアスペクト（座相）を計算するモジュール
主な仕様:
    - メジャーアスペクト: 0, 60, 90, 120, 180度
    - マイナーアスペクト: 30, 45, 72, 135, 144, 150度
    - オーブ（許容度数）の判定:
        - 太陽・月: メジャー ±8度, マイナー ±4度
        - その他: メジャー ±6度, マイナー ±3度
"""
from typing import List, Dict, Optional
from .holoscope_model import PlanetInfo, AspectInfo

# アスペクト定義
ASPECTS = [
    {"name": "Conjunction", "angle": 0, "type": "major", "hard": True},    # 合
    {"name": "Opposition", "angle": 180, "type": "major", "hard": True},   # 衝
    {"name": "Trine", "angle": 120, "type": "major", "hard": False},       # 三分
    {"name": "Square", "angle": 90, "type": "major", "hard": True},        # 四分
    {"name": "Sextile", "angle": 60, "type": "major", "hard": False},      # 六分
    {"name": "Quincunx", "angle": 150, "type": "minor", "hard": True},     # インコンジャンクト
    {"name": "Semi-Sextile", "angle": 30, "type": "minor", "hard": False}, # セミセクスタイル
    {"name": "Semi-Square", "angle": 45, "type": "minor", "hard": True},   # セミスクエア
    {"name": "Sesquiquadrate", "angle": 135, "type": "minor", "hard": True}, # セスキコードレイト
    {"name": "Quintile", "angle": 72, "type": "minor", "hard": False},     # クインタイル
    {"name": "Bi-Quintile", "angle": 144, "type": "minor", "hard": False}, # ビクインタイル
]

def get_orb(planet_name: str, aspect_type: str) -> float:
    """
    天体とアスペクト種類に応じたオーブを取得
    :param planet_name: 天体名（日本語）
    :param aspect_type: 'major' or 'minor'
    :return: float オーブ
    """
    is_luminary = planet_name in ["太陽", "月"]
    if is_luminary:
        return 8.0 if aspect_type == "major" else 4.0
    else:
        return 6.0 if aspect_type == "major" else 3.0

def calculate_aspects(planets: List[PlanetInfo]) -> List[AspectInfo]:
    """
    天体リストからアスペクトを計算・抽出する
    :param planets: List[PlanetInfo]
    :return: List[AspectInfo]
    """
    aspects = []
    n = len(planets)
    
    # 全組み合わせをチェック
    for i in range(n):
        for j in range(i + 1, n):
            p1 = planets[i]
            p2 = planets[j]
            
            # 角度差の計算 (0-180度に正規化)
            diff = abs(p1.longitude - p2.longitude)
            if diff > 180:
                diff = 360 - diff
            
            # 各アスペクトとの一致確認
            for aspect_def in ASPECTS:
                angle = aspect_def["angle"]
                aspect_type = aspect_def["type"]
                
                # 双方向で大きい方のオーブを採用（一般的解釈の一つ）
                orb1 = get_orb(p1.name, aspect_type)
                orb2 = get_orb(p2.name, aspect_type)
                orb_limit = max(orb1, orb2)
                
                current_orb = abs(diff - angle)
                
                if current_orb <= orb_limit:
                    aspects.append(AspectInfo(
                        planet1=p1.name,
                        planet2=p2.name,
                        type=aspect_def["name"],
                        angle=angle,
                        actual_angle=diff,
                        orb=current_orb,
                        aspect_type=aspect_type,
                        is_hard=aspect_def["hard"]
                    ))
                    # 1つのペアに対して最も近いアスペクト1つだけを採用する場合はここでbreakしてもよいが、
                    # オーブが重なるケースは稀かつ厳密には複数該当もあり得なくはないため、
                    # ここでは全ての可能性を拾う（通常は重ならない）
                    
    return aspects
