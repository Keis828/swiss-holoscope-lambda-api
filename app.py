"""
概要:
    holoscope用Lambda関数のエントリポイント
主な仕様:
    - API GatewayのPOSTリクエストを受け付ける
    - リクエストボディをパースし、holoscope_serviceの計算結果を返す
    - レスポンスはOpenAPI仕様に近い構造で返却
制限事項:
    - 実際の占星術ロジックはholoscope_service.pyに委譲
"""
import sys
import os
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


sys.path.append('./src')
print("=== Lambda sys.path ===")
for p in sys.path:
    print(p)

print("=== Lambda CWD files ===")
for f in os.listdir('.'):
    print(f)
try:
    import skyfield
    print("skyfield import OK")
except Exception as e:
    print("skyfield import error:", e)

try:
    import numpy
    print("numpy import OK")
except Exception as e:
    print("numpy import error:", e)

from typing import Any, Dict
import json
from src.holoscope_service import HoloscopeService
import numpy as np
from src.calculate_houses import calculate_houses
from datetime import datetime, timezone

def get_cors_headers(origin: str) -> dict:
    """
    許可されたOriginのみCORSヘッダーを返す
    - 設定は環境変数 `CORS_ALLOWED_ORIGINS` でカンマ区切り指定
      例: "https://example.com,https://foo.bar,http://localhost:8080"
    - `HoloscopeEnv` が `local` の場合、`CORS_ALLOWED_ORIGINS` 未設定なら localhost と 127.0.0.1 を暫定許可
    Args:
        origin (str): リクエスト元Origin
    Returns:
        dict: CORSヘッダー（許可されない場合は空dict）
    """
    env = os.environ.get("HoloscopeEnv", "dev").strip().lower()
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    allowed_origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not allowed_origins and env == "local":
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    if origin in allowed_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    return {}

def to_dict(obj):
    """
    オブジェクトを再帰的にdictへ変換。NumPy型もPython標準型に変換。
    """
    if hasattr(obj, '__dict__'):
        return {k: to_dict(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [to_dict(i) for i in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    else:
        return obj

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda関数のエントリポイント
    Args:
        event (dict): API Gatewayからのイベント
        context (Any): Lambda実行コンテキスト
    Returns:
        dict: API Gateway Proxy形式のレスポンス
    """
    try:
        logger.debug(f"[app.py] event: {event}")
        # Originヘッダーを厳密に取得（大文字・小文字対応）
        origin = None
        headers = event.get('headers', {})
        for key in headers:
            if key.lower() == 'origin':
                origin = headers[key]
                break
        logger.debug(f"[app.py] origin: {origin}")
        cors_headers = get_cors_headers(origin) if origin else {}
        logger.debug(f"[app.py] cors_headers: {cors_headers}")
        # CORSプリフライト対応
        if event.get('httpMethod', '').upper() == 'OPTIONS':
            return {
                "statusCode": 200,
                "headers": cors_headers,
                "body": json.dumps({"message": "CORS preflight OK"}, ensure_ascii=False)
            }
        body = json.loads(event.get('body', '{}'))
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        if path == '/api/v1/holoscope/create' and method == 'POST':
            # ハウスシステム指定（将来拡張用、現状はplacidus固定）
            system = body.get('system', 'placidus')
            engine = (body.get('engine') or os.environ.get('HOUSE_ENGINE') or 'skyfield').lower()
            # エンジン切替（Swissの場合のみ環境変数をSWISSへ）
            if engine == 'swiss':
                os.environ['HOUSE_ENGINE'] = 'SWISS'
            else:
                os.environ['HOUSE_ENGINE'] = 'SKYFIELD'
            service = HoloscopeService()
            result = service.create(body)
            response_body = {
                "userInfo": to_dict(result.userInfo),
                "planets": [to_dict(p) for p in result.planets],
                "houses": {
                    "system": system,
                    "cusps": [to_dict(h) for h in result.houses]
                },
                "ascendant": to_dict(result.ascendant),
                "descendant": to_dict(result.descendant),
                "mc": to_dict(result.mc),
                "ic": to_dict(result.ic),
                "elements": to_dict(result.elements),
                "qualities": to_dict(result.qualities)
            }
            return {
                "statusCode": 200,
                "headers": {**{"Content-Type": "application/json"}, **cors_headers},
                "body": json.dumps(response_body, ensure_ascii=False)
            }
        elif path == '/api/v1/holoscope/houses' and method == 'POST':
            # ハウス分割API
            # 必須パラメータ取得
            dt_str = body.get('datetime')
            latitude = body.get('latitude')
            longitude = body.get('longitude')
            system = body.get('system', 'placidus')
            engine = (body.get('engine') or os.environ.get('HOUSE_ENGINE') or 'skyfield').lower()
            if not (dt_str and latitude is not None and longitude is not None):
                return {
                    "statusCode": 400,
                    "headers": {**{"Content-Type": "application/json"}, **cors_headers},
                    "body": json.dumps({"error": {"message": "datetime, latitude, longitudeは必須です", "type": "BadRequest"}}, ensure_ascii=False)
                }
            try:
                # ISO8601を解析（Zは+00:00に置換）
                dt_parsed = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                # タイムゾーンが無い場合はJST（Asia/Tokyo）として解釈しUTCへ変換
                if dt_parsed.tzinfo is None:
                    import pytz
                    jst = pytz.timezone('Asia/Tokyo')
                    dt_parsed = jst.localize(dt_parsed)
                # UTCへ統一
                dt_utc = dt_parsed.astimezone(timezone.utc)
                logger.debug(f"[app.py] houses: datetime parsed={dt_parsed}, utc={dt_utc}")
            except Exception as e:
                return {
                    "statusCode": 400,
                    "headers": {**{"Content-Type": "application/json"}, **cors_headers},
                    "body": json.dumps({"error": {"message": f"datetimeパースエラー: {e}", "type": "BadRequest"}}, ensure_ascii=False)
                }
            # ハウス計算
            # エンジン切替: 'skyfield' or 'swiss'
            use_swiss = (engine == 'swiss')
            if use_swiss:
                # Swissを使いたいケースでは環境変数で指示
                os.environ['HOUSE_ENGINE'] = 'SWISS'
            else:
                os.environ['HOUSE_ENGINE'] = 'SKYFIELD'
            result = calculate_houses(dt_utc, latitude, longitude, system=system)
            # houses.system を含む形に整形
            response_body = {
                "ascendant": result.get("ascendant"),
                "descendant": result.get("descendant"),
                "mc": result.get("mc"),
                "ic": result.get("ic"),
                "houses": {
                    "system": system,
                    "cusps": result.get("houses", [])
                }
            }
            return {
                "statusCode": 200,
                "headers": {**{"Content-Type": "application/json"}, **cors_headers},
                "body": json.dumps(response_body, ensure_ascii=False)
            }
        else:
            return {
                "statusCode": 404,
                "headers": {**{"Content-Type": "application/json"}, **cors_headers},
                "body": json.dumps({"error": {"message": "Not Found", "type": "NotFoundError"}}, ensure_ascii=False)
            }
    except Exception as e:
        # エラー時は詳細なエラーメッセージを返す（OpenAPI風）
        return {
            "statusCode": 500,
            "headers": {**{"Content-Type": "application/json"}, **cors_headers},
            "body": json.dumps({
                "error": {
                    "message": str(e),
                    "type": "InternalServerError",
                    "function": "lambda_handler",
                    "event": event
                }
            }, ensure_ascii=False)
        } 