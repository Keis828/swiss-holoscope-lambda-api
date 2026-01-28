# 概要:
#   holoscope Python Lambda用Makefile
# 主な仕様:
#   - build: SAMビルド
#   - clean: buildディレクトリ等の削除
#   - invoke/api: SAM CLIによるローカル実行
#   - deploy: 環境変数で与えられたパラメータを用いてSAMデプロイ
# 制限事項:
#   - 固有のAWSプロファイル/バケット名は使用しない（環境変数で供給）

# 一般化された設定（必要に応じて上書き）
PROFILE ?= ametuchi
REGION ?= ap-northeast-1
STACK_NAME ?= ametuchi-holoscope-api-server
S3_BUCKET ?= ametuchi-api-lambda-resource
ENV ?= dev
PARAM_OVERRIDES ?= Env=$(ENV)
ENV_VARS_FILE ?= envs/local.json

clean:
	rm -rf ./build

build: clean
	mkdir -p build
	sam build --use-container

invoke: build
	sam local invoke --env-vars $(ENV_VARS_FILE)

api: build
	sam local start-api --host 0.0.0.0 -p 3001 --profile $(PROFILE) --skip-pull-image --env-vars $(ENV_VARS_FILE) --parameter-overrides $(PARAM_OVERRIDES)

test:
	@if [ -d venv ]; then . venv/bin/activate; fi; pytest -q

deploy_dev: build
	$(MAKE) test
	sam validate --profile $(PROFILE) --region $(REGION) && \
	sam package --template-file .aws-sam/build/template.yaml --s3-bucket $(S3_BUCKET) --output-template-file packaged.yaml --profile $(PROFILE) --region $(REGION) && \
	sam deploy --region $(REGION) --template-file "./packaged.yaml" --stack-name ametuchi-dev-holoscope-api-server --capabilities CAPABILITY_IAM --profile $(PROFILE) --parameter-overrides Env=dev

deploy_prd: build test
	sam validate --profile $(PROFILE) --region $(REGION) && \
	sam package --template-file .aws-sam/build/template.yaml --s3-bucket $(S3_BUCKET) --output-template-file packaged.yaml --profile $(PROFILE) --region $(REGION) && \
	sam deploy --region $(REGION) --template-file "./packaged.yaml" --stack-name ametuchi-holoscope-api-server --capabilities CAPABILITY_IAM --profile $(PROFILE) --parameter-overrides Env=prd