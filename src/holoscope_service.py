"""
概要:
    西洋占星術（ホロスコープ）計算サービス
主な仕様:
    - ユーザー情報、天体位置、ハウス、エレメント、3区分を計算しレスポンスを生成
    - 天体・ハウス計算は今後専用モジュールに委譲可能な構造
    - 出生地名のみの場合、hoshiyomi-api-serverのAPIから都市情報を取得
制限事項:
    - 一部ロジックはダミー実装
"""
from typing import Any, Dict
from .holoscope_model import UserInfo, PlanetInfo, HouseInfo, SignInfo, ElementsInfo, QualitiesInfo, Location, ResponseHoloscopeCreate
import math
from datetime import datetime, timezone, timedelta
from .calculate_planets import calculate_planets
from .calculate_houses import calculate_houses
import os
import requests
from skyfield.api import Loader
import pytz
import sys
import platform

# --- 日本の都道府県DB（県庁所在地の緯度経度・時差付き） ---
city_db = [
    {"name": "北海道", "lat": 43.0642, "lon": 141.3469, "timezone": "Asia/Tokyo", "timediff": 25},
    {"name": "青森県", "lat": 40.8244, "lon": 140.74, "timezone": "Asia/Tokyo", "timediff": 23},
    {"name": "岩手県", "lat": 39.7036, "lon": 141.1525, "timezone": "Asia/Tokyo", "timediff": 25},
    {"name": "宮城県", "lat": 38.2688, "lon": 140.8721, "timezone": "Asia/Tokyo", "timediff": 23},
    {"name": "秋田県", "lat": 39.7186, "lon": 140.1024, "timezone": "Asia/Tokyo", "timediff": 20},
    {"name": "山形県", "lat": 38.2404, "lon": 140.3633, "timezone": "Asia/Tokyo", "timediff": 21},
    {"name": "福島県", "lat": 37.7503, "lon": 140.4675, "timezone": "Asia/Tokyo", "timediff": 22},
    {"name": "茨城県", "lat": 36.3418, "lon": 140.4468, "timezone": "Asia/Tokyo", "timediff": 22},
    {"name": "栃木県", "lat": 36.5658, "lon": 139.8836, "timezone": "Asia/Tokyo", "timediff": 20},
    {"name": "群馬県", "lat": 36.3911, "lon": 139.0608, "timezone": "Asia/Tokyo", "timediff": 16},
    {"name": "埼玉県", "lat": 35.8569, "lon": 139.6489, "timezone": "Asia/Tokyo", "timediff": 19},
    {"name": "千葉県", "lat": 35.6046, "lon": 140.1233, "timezone": "Asia/Tokyo", "timediff": 20},
    {"name": "東京都", "lat": 35.6895, "lon": 139.6917, "timezone": "Asia/Tokyo", "timediff": 19},
    {"name": "神奈川", "lat": 35.4478, "lon": 139.6425, "timezone": "Asia/Tokyo", "timediff": 19},
    {"name": "新潟県", "lat": 37.9026, "lon": 139.0236, "timezone": "Asia/Tokyo", "timediff": 16},
    {"name": "富山県", "lat": 36.6953, "lon": 137.2113, "timezone": "Asia/Tokyo", "timediff": 9},
    {"name": "石川県", "lat": 36.5947, "lon": 136.6256, "timezone": "Asia/Tokyo", "timediff": 5},
    {"name": "福井県", "lat": 36.0652, "lon": 136.2216, "timezone": "Asia/Tokyo", "timediff": 5},
    {"name": "山梨県", "lat": 35.6639, "lon": 138.5684, "timezone": "Asia/Tokyo", "timediff": 6},
    {"name": "長野県", "lat": 36.6513, "lon": 138.1811, "timezone": "Asia/Tokyo", "timediff": 13},
    {"name": "岐阜県", "lat": 35.3912, "lon": 136.7223, "timezone": "Asia/Tokyo", "timediff": 7},
    {"name": "静岡県", "lat": 34.9769, "lon": 138.3831, "timezone": "Asia/Tokyo", "timediff": 14},
    {"name": "愛知県", "lat": 35.1802, "lon": 136.9066, "timezone": "Asia/Tokyo", "timediff": 8},
    {"name": "三重県", "lat": 34.7303, "lon": 136.5086, "timezone": "Asia/Tokyo", "timediff": 6},
    {"name": "滋賀県", "lat": 35.0045, "lon": 135.8686, "timezone": "Asia/Tokyo", "timediff": 4},
    {"name": "京都府", "lat": 35.0214, "lon": 135.7556, "timezone": "Asia/Tokyo", "timediff": 3},
    {"name": "大阪府", "lat": 34.6937, "lon": 135.5023, "timezone": "Asia/Tokyo", "timediff": 2},
    {"name": "兵庫県", "lat": 34.6913, "lon": 135.1830, "timezone": "Asia/Tokyo", "timediff": 1},
    {"name": "奈良県", "lat": 34.6851, "lon": 135.8048, "timezone": "Asia/Tokyo", "timediff": 3},
    {"name": "和歌山", "lat": 34.2260, "lon": 135.1675, "timezone": "Asia/Tokyo", "timediff": 1},
    {"name": "鳥取県", "lat": 35.5011, "lon": 134.2351, "timezone": "Asia/Tokyo", "timediff": -3},
    {"name": "島根県", "lat": 35.4723, "lon": 133.0505, "timezone": "Asia/Tokyo", "timediff": -8},
    {"name": "岡山県", "lat": 34.6618, "lon": 133.9344, "timezone": "Asia/Tokyo", "timediff": -4},
    {"name": "広島県", "lat": 34.3963, "lon": 132.4596, "timezone": "Asia/Tokyo", "timediff": -10},
    {"name": "山口県", "lat": 34.1859, "lon": 131.4714, "timezone": "Asia/Tokyo", "timediff": -14},
    {"name": "徳島県", "lat": 34.0658, "lon": 134.5593, "timezone": "Asia/Tokyo", "timediff": -2},
    {"name": "香川県", "lat": 34.3401, "lon": 134.0434, "timezone": "Asia/Tokyo", "timediff": -4},
    {"name": "愛媛県", "lat": 33.8416, "lon": 132.7657, "timezone": "Asia/Tokyo", "timediff": -9},
    {"name": "高知県", "lat": 33.5597, "lon": 133.5311, "timezone": "Asia/Tokyo", "timediff": -6},
    {"name": "福岡県", "lat": 33.5902, "lon": 130.4017, "timezone": "Asia/Tokyo", "timediff": -18},
    {"name": "佐賀県", "lat": 33.2635, "lon": 130.3009, "timezone": "Asia/Tokyo", "timediff": -19},
    {"name": "長崎県", "lat": 32.7503, "lon": 129.8777, "timezone": "Asia/Tokyo", "timediff": -21},
    {"name": "五島列島", "lat": 32.6956, "lon": 128.8419, "timezone": "Asia/Tokyo", "timediff": -24},
    {"name": "熊本県", "lat": 32.7898, "lon": 130.7417, "timezone": "Asia/Tokyo", "timediff": -18},
    {"name": "大分県", "lat": 33.2382, "lon": 131.6126, "timezone": "Asia/Tokyo", "timediff": -14},
    {"name": "宮崎県", "lat": 31.9111, "lon": 131.4239, "timezone": "Asia/Tokyo", "timediff": -14},
    {"name": "鹿児島", "lat": 31.5602, "lon": 130.5581, "timezone": "Asia/Tokyo", "timediff": -18},
    {"name": "沖縄県", "lat": 26.2124, "lon": 127.6809, "timezone": "Asia/Tokyo", "timediff": -29},
    {"name": "石垣", "lat": 24.3400, "lon": 124.1550, "timezone": "Asia/Tokyo", "timediff": -43},
    {"name": "海外", "lat": 0.0, "lon": 0.0, "timezone": "Asia/Tokyo", "timediff": 0},
    {"name": "不明", "lat": 0.0, "lon": 0.0, "timezone": "Asia/Tokyo", "timediff": 0},
]

class HoloscopeService:
    """
    ホロスコープ計算サービスクラス
    """
    def __init__(self, ephemeris_path: str = None):
        """
        サービス初期化時に天体歴ファイルを一度だけロード
        Lambda環境での互換性を考慮した初期化処理
        :param ephemeris_path: str 天体歴ファイルのパス（省略時はde432s.bsp）
        """
        try:
            # 必要なモジュールを最初にインポート
            import os
            import sys
            import platform
            import tempfile
            import shutil
            
            print(f"HoloscopeService.__init__: Starting initialization")
            print(f"Python version: {sys.version}")
            print(f"Platform: {platform.platform()}")
            
            # Lambda環境の確認
            print(f"Environment variables: AWS_LAMBDA_FUNCTION_NAME={os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'None')}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Python path: {sys.path}")
            
            # skyfieldのインポートテスト
            try:
                from skyfield.api import Loader
                print("skyfield.api.Loader imported successfully")
            except ImportError as e:
                print(f"Failed to import skyfield.api.Loader: {e}")
                raise
            
            # numpyのインポートテスト  
            try:
                import numpy as np
                print(f"numpy imported successfully, version: {np.__version__}")
            except ImportError as e:
                print(f"Failed to import numpy: {e}")
                raise
                
            # jplephem のインポートテスト
            try:
                import jplephem
                print(f"jplephem imported successfully")
            except ImportError as e:
                print(f"Failed to import jplephem: {e}")
                raise

            # Lambda環境対応: 書き込み可能な/tmpディレクトリを使用
            if ephemeris_path is None:
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                eph_path = os.path.join(root_dir, 'de432s.bsp')
            else:
                eph_path = ephemeris_path

            tmp_dir = '/tmp'
            if not os.path.exists(tmp_dir):
                tmp_dir = tempfile.gettempdir()
            
            print(f"Using temporary directory: {tmp_dir}")
            
            # まずS3から/tmpへダウンロードを試行（存在しない場合のみ）
            tmp_eph_path = os.path.join(tmp_dir, 'de432s.bsp')
            if not os.path.exists(tmp_eph_path):
                bucket = os.environ.get('EPHEMERIS_S3_BUCKET', 'hoshiyomi-ephemeris-bucket')
                key = os.environ.get('EPHEMERIS_S3_KEY', 'de432s.bsp')
                try:
                    import boto3
                    print(f"Attempting to download ephemeris from s3://{bucket}/{key} to {tmp_eph_path}")
                    s3 = boto3.client('s3')
                    s3.download_file(bucket, key, tmp_eph_path)
                    print(f"S3 download completed. File size: {os.path.getsize(tmp_eph_path)} bytes")
                except Exception as s3e:
                    print(f"S3 download failed: {s3e}")
                    # フォールバック: リポジトリ直下のファイルからコピー
                    if os.path.exists(eph_path):
                        try:
                            print(f"Copying ephemeris file from {eph_path} to {tmp_eph_path}")
                            shutil.copy2(eph_path, tmp_eph_path)
                            print(f"Copy completed. File size: {os.path.getsize(tmp_eph_path)} bytes")
                        except Exception as copye:
                            print(f"Copy failed: {copye}")
                    else:
                        print(f"Local ephemeris not found at {eph_path}")
            else:
                print(f"Ephemeris file already exists at: {tmp_eph_path}")

            # 最終チェック: /tmpにファイルが無ければエラー
            if not os.path.exists(tmp_eph_path):
                raise FileNotFoundError(f"Ephemeris file not available at {tmp_eph_path}. Provide s3://{os.environ.get('EPHEMERIS_S3_BUCKET', 'hoshiyomi-ephemeris-bucket')}/{os.environ.get('EPHEMERIS_S3_KEY', 'de432s.bsp')} or bundle de432s.bsp.")
            
            # Swiss Ephemeris 標準ファイルもS3から取得（/tmp/ephe に配置）
            try:
                swiss_dir = os.path.join(tmp_dir, 'ephe')
                if not os.path.isdir(swiss_dir):
                    os.makedirs(swiss_dir, exist_ok=True)
                bucket = os.environ.get('EPHEMERIS_S3_BUCKET', 'hoshiyomi-ephemeris-bucket')
                se_keys = {
                    'sepl_18.se1': os.environ.get('SWISS_SEPL_KEY', 'sepl_18.se1'),
                    'semo_18.se1': os.environ.get('SWISS_SEMO_KEY', 'semo_18.se1'),
                    'seas_18.se1': os.environ.get('SWISS_SEAS_KEY', 'seas_18.se1'),
                }
                try:
                    import boto3
                    s3 = boto3.client('s3')
                    for fname, key in se_keys.items():
                        local_path = os.path.join(swiss_dir, fname)
                        if os.path.exists(local_path):
                            print(f"Swiss ephe already exists: {local_path}")
                            continue
                        try:
                            print(f"Downloading Swiss ephe {fname} from s3://{bucket}/{key} -> {local_path}")
                            s3.download_file(bucket, key, local_path)
                            print(f"Downloaded {fname}, size={os.path.getsize(local_path)} bytes")
                        except Exception as dlerr:
                            print(f"Swiss ephe download skipped/failed for {fname}: {dlerr}")
                except Exception as be:
                    print(f"Swiss ephe S3 client init failed: {be}")
            except Exception as anyse:
                print(f"Swiss ephe setup error: {anyse}")

            # Loaderを/tmpディレクトリで初期化（章動ファイル等の自動ダウンロード対応）
            print(f"Initializing Skyfield Loader with directory: {tmp_dir}")
            self.loader = Loader(tmp_dir)
            
            print("Loading ephemeris file...")
            self.eph = self.loader('de432s.bsp')
            print("Ephemeris loaded successfully")
            
            print("Creating timescale...")
            self.ts = self.loader.timescale()
            print("Timescale created successfully")
            
            print(f"HoloscopeService initialization completed successfully")
            
        except Exception as e:
            print(f"Error in HoloscopeService.__init__: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            
            # Lambda環境での詳細デバッグ情報
            print("=== Lambda Environment Debug Info ===")
            try:
                import sys
                import os
                print(f"sys.path: {sys.path}")
                print(f"Environment variables:")
                for key, value in os.environ.items():
                    if 'AWS' in key or 'LAMBDA' in key:
                        print(f"  {key}={value}")
                
                # インストール済みパッケージの確認
                try:
                    import pkg_resources
                    installed_packages = [d.project_name for d in pkg_resources.working_set]
                    print(f"Installed packages: {sorted(installed_packages)}")
                except:
                    print("Could not list installed packages")
            except:
                print("Could not show debug info")
            
            raise


    def _fetch_city_info(self, city_name: str, country: str = "日本") -> dict:
        """
        内部DBから都市情報を取得
        :param city_name: str 都市名
        :param country: str 国名（未使用、将来拡張用）
        :return: dict 都市情報（見つからなければNone）
        """
        target = city_name.strip().lower()
        for city in city_db:
            if city["name"].strip().lower() == target:
                return city
        return None

    def _calculate_elements(self, planets, ascendant=None, descendant=None, mc=None, ic=None):
        """
        エレメント（火・地・風・水）の集計（惑星のみ）
        :param planets: List[PlanetInfo] 惑星情報リスト
        :param ascendant: SignInfo アセンダント情報
        :param descendant: SignInfo ディセンダント情報
        :param mc: SignInfo MC情報
        :param ic: SignInfo IC情報
        :return: ElementsInfo
        """
        fire = earth = air = water = 0
        fire_signs = ["牡羊座", "獅子座", "射手座"]
        earth_signs = ["牡牛座", "乙女座", "山羊座"]
        air_signs = ["双子座", "天秤座", "水瓶座"]
        water_signs = ["蟹座", "蠍座", "魚座"]
        
        # 惑星のエレメント集計（AC/DC/MC/ICは含めない）
        for p in planets:
            if p.sign in fire_signs:
                fire += 1
            elif p.sign in earth_signs:
                earth += 1
            elif p.sign in air_signs:
                air += 1
            elif p.sign in water_signs:
                water += 1
                    
        return ElementsInfo(fire=fire, earth=earth, air=air, water=water)

    def _calculate_qualities(self, planets, ascendant=None, descendant=None, mc=None, ic=None):
        """
        3区分（活動・不動・柔軟）の集計（惑星のみ）
        :param planets: List[PlanetInfo] 惑星情報リスト
        :param ascendant: SignInfo アセンダント情報
        :param descendant: SignInfo ディセンダント情報
        :param mc: SignInfo MC情報
        :param ic: SignInfo IC情報
        :return: QualitiesInfo
        """
        cardinal = fixed = mutable = 0
        cardinal_signs = ["牡羊座", "蟹座", "天秤座", "山羊座"]
        fixed_signs = ["牡牛座", "獅子座", "蠍座", "水瓶座"]
        mutable_signs = ["双子座", "乙女座", "射手座", "魚座"]
        
        # 惑星の3区分集計（AC/DC/MC/ICは含めない）
        for p in planets:
            if p.sign in cardinal_signs:
                cardinal += 1
            elif p.sign in fixed_signs:
                fixed += 1
            elif p.sign in mutable_signs:
                mutable += 1
                    
        return QualitiesInfo(cardinal=cardinal, fixed=fixed, mutable=mutable)

    def _assign_planets_to_houses(self, planets, houses):
        """
        惑星の黄経からハウス番号を割り当てる
        :param planets: List[PlanetInfo]
        :param houses: List[HouseInfo]
        :return: None（planetsのhouseフィールドを直接更新）
        """
        # ハウスカスプの黄経リスト（1室〜12室、360度循環）
        cusps = [h.longitude for h in houses]
        for p in planets:
            lon = p.longitude % 360
            # 12室分ループ
            for i in range(12):
                start = cusps[i]
                end = cusps[(i+1)%12]
                # 360度循環を考慮
                if start < end:
                    in_house = start <= lon < end
                else:
                    in_house = lon >= start or lon < end
                if in_house:
                    p.house = i+1
                    break

    def create(self, req: Dict[str, Any]) -> ResponseHoloscopeCreate:
        """
        ホロスコープ作成リクエストを受けて計算結果を返す
        :param req: リクエスト辞書
        :return: ResponseHoloscopeCreate
        """
        try:
            print(f"create: Starting holoscope calculation")
            print(f"create: Request data: {req}")
            # ハウスシステム（placidus/equal/koch）
            system = req.get("system", "placidus")
            
            # 柔軟なフィールド対応
            date_str = req.get("date") or req.get("birthdate") or ""
            location = req.get("location") or req.get("birthplace") or {}
            name = location.get("name", "")
            latitude = location.get("latitude") or location.get("lat")
            longitude = location.get("longitude") or location.get("lon")
            tz = location.get("tz") or location.get("timezone")
            
            print(f"create: Parsed data - date_str={date_str}, name={name}, lat={latitude}, lon={longitude}, tz={tz}")
            
            # 天文暦のファイル
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            eph_path = os.path.join(root_dir, 'de442s.bsp')

            # --- 追加: 地名のみの場合APIで詳細取得し、locationに明示的にセット ---
            if (not latitude or not longitude or not tz) and name:
                print(f"create: Fetching city info for {name}")
                city_info = self._fetch_city_info(name)
                if city_info is None:
                    raise ValueError(f"create: 都市情報が見つかりません name={name}")
                latitude = city_info.get("lat")
                longitude = city_info.get("lon")
                tz = city_info.get("timezone")
                # location辞書に明示的にセット
                location["latitude"] = latitude
                location["longitude"] = longitude
                location["tz"] = tz
                print(f"create: Updated location from city_info - lat={latitude}, lon={longitude}, tz={tz}")

            # 緯度・経度が必ずセットされている前提で計算
            userInfo = UserInfo(
                name=req.get("name", ""),
                birthdate=date_str,
                birthplace=name,
                gender=req.get("gender", 0),
                isTimeUnknown=req.get("isTimeUnknown", False),
                # 以下はダミー
                timeDiff=0,
                addTimeDiffBirthdate=date_str,
                age=0
            )
            print(f"create: Created userInfo")

            # 天体位置計算（Skyfield本実装）
            print(f"create: Starting planet calculation")
            
            # 時刻をタイムゾーン考慮して正しく変換
            # date_strを解析（例: "198208281503"）
            dt_naive = datetime.strptime(date_str, "%Y%m%d%H%M")
            
            # タイムゾーンを適用
            if tz and tz != "UTC":
                # 指定されたタイムゾーンで解析
                local_tz = pytz.timezone(tz)
                dt_local = local_tz.localize(dt_naive)
                dt_utc = dt_local.astimezone(timezone.utc)
            else:
                # UTCとして扱う
                dt_utc = dt_naive.replace(tzinfo=timezone.utc)
                
            print(f"create: Parsed datetime - local: {dt_naive}, timezone: {tz}, UTC: {dt_utc}")
            
            planet_dicts = calculate_planets(dt_utc, float(location["latitude"]), float(location["longitude"]), eph=self.eph, ts=self.ts)
            print(f"create: Planet calculation completed, got {len(planet_dicts)} planets")
            
            planets = [
                PlanetInfo(
                    name=p["name_jp"],
                    sign=p["sign"],
                    longitude=p["longitude"],
                    house=0,  # ハウス割り当ては後で
                    retrograde=p["retrograde"]
                ) for p in planet_dicts
            ]
            print(f"create: Created planet objects")

            # ハウス計算（Skyfield本実装）
            print(f"create: Starting house calculation")
            house_result = calculate_houses(
                dt_utc,
                float(location["latitude"]),
                float(location["longitude"]),
                eph=self.eph,
                ts=self.ts,
                system=system
            )
            print(f"create: House calculation completed")
            
            houses = [
                HouseInfo(number=h["number"], sign=h["sign"], longitude=h["longitude"]) for h in house_result["houses"]
            ]
            ascendant = SignInfo(sign=house_result["ascendant"]["sign"], longitude=house_result["ascendant"]["longitude"])
            descendant = SignInfo(sign=house_result["descendant"]["sign"], longitude=house_result["descendant"]["longitude"])
            mc = SignInfo(sign=house_result["mc"]["sign"], longitude=house_result["mc"]["longitude"])
            ic = SignInfo(sign=house_result["ic"]["sign"], longitude=house_result["ic"]["longitude"])
            print(f"create: Created house objects")

            # 惑星のハウス割り当て
            print(f"create: Assigning planets to houses")
            self._assign_planets_to_houses(planets, houses)

            # エレメント・3区分の本集計
            print(f"create: Calculating elements and qualities")
            elements = self._calculate_elements(planets, ascendant, descendant, mc, ic)
            qualities = self._calculate_qualities(planets, ascendant, descendant, mc, ic)

            print(f"create: Holoscope calculation completed successfully")
            return ResponseHoloscopeCreate(
                userInfo=userInfo,
                planets=planets,
                houses=houses,
                ascendant=ascendant,
                descendant=descendant,
                mc=mc,
                ic=ic,
                elements=elements,
                qualities=qualities
            )
        except Exception as e:
            print(f"create: Error occurred: {str(e)}")
            print(f"create: Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise 