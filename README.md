## swiss-holoscope-lambda-api

AWS SAM 上で動作するホロスコープ計算用の Python Lambda 関数です。Skyfield/JPL BSP を用いた惑星・ハウス計算を提供し、任意で Swiss Ephemeris によるハウス計算へ切り替えることができます。

### 特徴
- API Gateway エンドポイント:
  - POST `/api/v1/holoscope/create`
  - POST `/api/v1/holoscope/houses`
- 設定は環境変数で外部化（CORS 設定、天文歴のS3バケット/キー など）
- 大容量の天文データ（.bsp/.se1）はリポジトリに含めず、必要時にスクリプトで取得
- AGPL-3.0 ライセンス（配布/ホスティング時はソースの提供が必要）

### 前提
- Python 3.12
- AWS SAM CLI

### セットアップ
1) 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

2) 環境変数ファイルの用意（任意）
- `envs/local.json.example` を参考に `envs/local.json` を作成するか、SAM の `--env-vars`/`--parameter-overrides` を使用してください。

3) 天文暦データの取得
```bash
python scripts/fetch_ephemeris.py --download-jpl true \
  --jpl-url https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de432s.bsp
```
- Swiss Ephemeris（`*.se1`）は配布ポリシーの都合により自動取得を行いません。以下のいずれかで `/tmp/ephe` もしくは任意のディレクトリに配置し、`SWISSEPH_PATH` を設定してください。
  - S3 から取得（`EPHEMERIS_S3_BUCKET` と `SWISS_*_KEY` を設定）
  - Swiss Ephemeris の配布に従い入手したファイルを手動配置

### 環境変数
- CORS
  - `CORS_ALLOWED_ORIGINS`: カンマ区切りの許可 Origin（例: `https://example.com,http://localhost:3000`）
- 天文歴
  - `EPHEMERIS_S3_BUCKET`: S3 バケット名
  - `EPHEMERIS_S3_KEY`: JPL BSP ファイルキー（例: `de432s.bsp`）
  - `SWISS_SEPL_KEY` / `SWISS_SEMO_KEY` / `SWISS_SEAS_KEY`: Swiss Ephemeris ファイルキー
  - `SWISSEPH_PATH`: Swiss Ephemeris を配置したディレクトリパス（任意）
- 実行モード
  - `HoloscopeEnv`: `local|dev|prd`
  - `HOUSE_ENGINE`: `SKYFIELD|SWISS`（`/houses` API のハウス計算切替）

### ローカル実行
```bash
make api PROFILE=default ENV=local ENV_VARS_FILE=envs/local.json
```

### デプロイ（例）
```bash
make deploy PROFILE=default S3_BUCKET=your-sam-artifacts-bucket \
  REGION=ap-northeast-1 STACK_NAME=hoshiyomi-holoscope-server \
  PARAM_OVERRIDES="Env=dev EphemerisBucketName=your-ephemeris-bucket CorsAllowedOrigins=https://example.com"
```

### API 例
- POST `/api/v1/holoscope/houses`
```json
{
  "datetime": "2020-12-01T09:42:00Z",
  "latitude": 35.6895,
  "longitude": 139.6917,
  "system": "placidus",
  "engine": "skyfield"
}
```

### ライセンス（AGPL-3.0）
本プロジェクトは GNU Affero General Public License v3.0（AGPL-3.0）に基づき公開しています。ネットワーク越しの利用者に対してもソースコードの提供が必要です。詳細は `LICENSE` を参照してください。

公開/配布時の注意:
- 改変した場合は改変部分のソースも公開してください。
- 本プロジェクトをサービスとして提供する場合も、対応するソースへのアクセス手段を提供してください。
- Swiss Ephemeris ファイルの再配布ポリシーに留意してください（本リポジトリでは同梱しません）。

### 開発メモ
- CORS 設定は `CORS_ALLOWED_ORIGINS` で集中管理
- 大容量データ（`.bsp`, `.se1`）は `.gitignore` 済み
- テストは Skyfield を前提とし、`/tmp/de432s.bsp` が無ければ自動取得/コピーします

