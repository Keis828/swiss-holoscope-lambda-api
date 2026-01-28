"""
概要:
    西洋占星術（ホロスコープ）計算用のデータモデル定義
主な仕様:
    - ユーザー情報、惑星情報、ハウス情報、星座情報、エレメント、3区分、ロケーション情報をクラスで定義
制限事項:
    - Goの構造体をPythonクラスに変換
"""
from typing import List

class UserInfo:
    """
    ユーザー情報
    :param name: str ユーザー名
    :param birthdate: str 生年月日 (YYYYMMDDHHMM)
    :param birthplace: str 出生地名
    :param gender: int 性別 (0:不明, 1:男性, 2:女性)
    :param isTimeUnknown: bool 時刻不明かどうか
    :param timeDiff: int 時差（分）
    :param addTimeDiffBirthdate: str 時差修正後の生年月日
    :param age: int 年齢
    """
    def __init__(self, name: str = "", birthdate: str = "", birthplace: str = "", gender: int = 0, isTimeUnknown: bool = False, timeDiff: int = 0, addTimeDiffBirthdate: str = "", age: int = 0):
        self.name = name
        self.birthdate = birthdate
        self.birthplace = birthplace
        self.gender = gender
        self.isTimeUnknown = isTimeUnknown
        self.timeDiff = timeDiff
        self.addTimeDiffBirthdate = addTimeDiffBirthdate
        self.age = age

class PlanetInfo:
    """
    惑星情報
    :param name: str 惑星名 (例: "太陽", "月")
    :param sign: str 星座名 (例: "牡羊座")
    :param longitude: float 黄道座標における経度
    :param house: int 所在ハウス番号
    :param retrograde: bool 逆行しているか
    """
    def __init__(self, name: str = "", sign: str = "", longitude: float = 0.0, house: int = 0, retrograde: bool = False):
        self.name = name
        self.sign = sign
        self.longitude = longitude
        self.house = house
        self.retrograde = retrograde

class HouseInfo:
    """
    ハウス情報
    :param number: int ハウス番号 (1-12)
    :param sign: str カスプの星座名
    :param longitude: float カスプの経度
    """
    def __init__(self, number: int = 0, sign: str = "", longitude: float = 0.0):
        self.number = number
        self.sign = sign
        self.longitude = longitude

class SignInfo:
    """
    星座情報（ASCやMCなど）
    :param sign: str 星座名
    :param longitude: float 経度
    """
    def __init__(self, sign: str = "", longitude: float = 0.0):
        self.sign = sign
        self.longitude = longitude

class ElementsInfo:
    """
    エレメント（火・地・風・水）の集計情報
    :param fire: int 火のエレメント数
    :param earth: int 地のエレメント数
    :param air: int 風のエレメント数
    :param water: int 水のエレメント数
    """
    def __init__(self, fire: int = 0, earth: int = 0, air: int = 0, water: int = 0):
        self.fire = fire
        self.earth = earth
        self.air = air
        self.water = water

class QualitiesInfo:
    """
    3区分（活動・不動・柔軟）の集計情報
    :param cardinal: int 活動宮数
    :param fixed: int 不動宮数
    :param mutable: int 柔軟宮数
    """
    def __init__(self, cardinal: int = 0, fixed: int = 0, mutable: int = 0):
        self.cardinal = cardinal
        self.fixed = fixed
        self.mutable = mutable

class Location:
    """
    出生場所情報
    :param name: str 場所名
    :param latitude: float 緯度
    :param longitude: float 経度
    :param tz: str タイムゾーン
    """
    def __init__(self, name: str = "", latitude: float = 0.0, longitude: float = 0.0, tz: str = ""): 
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.tz = tz

class AspectInfo:
    """
    アスペクト情報
    :param planet1: str 天体1の名前
    :param planet2: str 天体2の名前
    :param type: str アスペクト名（Conjunction, Trine, etc.）
    :param angle: float 定義上の角度（0, 60, 90...）
    :param actual_angle: float 実際の角度差
    :param orb: float 誤差（オーブ）
    :param aspect_type: str 'major' or 'minor'
    :param is_hard: bool ハードアスペクトかどうか
    """
    def __init__(self, planet1: str, planet2: str, type: str, angle: float, actual_angle: float, orb: float, aspect_type: str, is_hard: bool):
        self.planet1 = planet1
        self.planet2 = planet2
        self.type = type
        self.angle = angle
        self.actual_angle = actual_angle
        self.orb = orb
        self.aspect_type = aspect_type
        self.is_hard = is_hard


class AsteroidInfo:
    """
    小惑星・感受点情報
    :param name: str 天体名（日本語）
    :param name_en: str 天体名（英語）
    :param sign: str 星座名 (例: "牡羊座")
    :param longitude: float 黄道座標における経度
    :param house: int 所在ハウス番号
    :param retrograde: bool 逆行しているか
    :param speed: float 移動速度（度/日）
    """
    def __init__(self, name: str = "", name_en: str = "", sign: str = "", longitude: float = 0.0, house: int = 0, retrograde: bool = False, speed: float = 0.0):
        self.name = name
        self.name_en = name_en
        self.sign = sign
        self.longitude = longitude
        self.house = house
        self.retrograde = retrograde
        self.speed = speed


class ResponseHoloscopeCreate:
    """
    ホロスコープ作成APIのレスポンス
    :param userInfo: UserInfo ユーザー情報
    :param planets: List[PlanetInfo] 惑星情報リスト
    :param houses: List[HouseInfo] ハウス情報リスト
    :param ascendant: SignInfo アセンダント情報
    :param descendant: SignInfo ディセンダント情報
    :param mc: SignInfo MC情報
    :param ic: SignInfo IC情報
    :param elements: ElementsInfo エレメント集計
    :param qualities: QualitiesInfo 3区分集計
    :param aspects: List[AspectInfo] アスペクト情報リスト
    :param asteroids: List[AsteroidInfo] 小惑星・感受点情報リスト
    """
    def __init__(self, userInfo: UserInfo, planets: List[PlanetInfo], houses: List[HouseInfo], ascendant: SignInfo, descendant: SignInfo, mc: SignInfo, ic: SignInfo, elements: ElementsInfo, qualities: QualitiesInfo, aspects: List[AspectInfo] = [], asteroids: List[AsteroidInfo] = []):
        self.userInfo = userInfo
        self.planets = planets
        self.houses = houses
        self.ascendant = ascendant
        self.descendant = descendant
        self.mc = mc
        self.ic = ic
        self.elements = elements
        self.qualities = qualities
        self.aspects = aspects
        self.asteroids = asteroids 