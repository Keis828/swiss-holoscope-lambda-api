"""
概要:
    JPL BSP（例: de432s.bsp）などの天文歴データを取得するユーティリティスクリプト。
主な仕様:
    - HTTP経由で JPL BSP をダウンロードし、指定パスへ保存
    - オプションで S3 へアップロード（再配布用）
制限事項:
    - Swiss Ephemeris（*.se1）の自動取得は行わない（配布条件に配慮）
    - ネットワーク未接続環境では利用不可
使用例:
    python scripts/fetch_ephemeris.py --download-jpl true \
        --jpl-url https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de432s.bsp \
        --output /tmp/de432s.bsp \
        --upload-s3 false --s3-bucket your-bucket --s3-key de432s.bsp
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional


def download_file(url: str, output_path: str) -> None:
    """
    指定URLからファイルをダウンロードして保存する。
    Args:
        url (str): 取得元URL
        output_path (str): 保存先パス
    例外:
        RuntimeError: ダウンロードに失敗した場合
    """
    try:
        import requests  # type: ignore
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(resp.content)
    except Exception as e:
        raise RuntimeError(f"download_file: url='{url}', output='{output_path}', error='{e}'")


def upload_to_s3(file_path: str, bucket: str, key: str) -> None:
    """
    S3へファイルをアップロードする。
    Args:
        file_path (str): アップロード対象ファイル
        bucket (str): バケット名
        key (str): オブジェクトキー
    例外:
        RuntimeError: アップロードに失敗した場合
    """
    try:
        import boto3  # type: ignore
        s3 = boto3.client("s3")
        s3.upload_file(file_path, bucket, key)
    except Exception as e:
        raise RuntimeError(
            f"upload_to_s3: file='{file_path}', s3://{bucket}/{key}, error='{e}'"
        )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Ephemeris downloader")
    parser.add_argument("--download-jpl", type=str, default="true", help="JPL BSPをダウンロードするか (true/false)")
    parser.add_argument(
        "--jpl-url",
        type=str,
        default="https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de432s.bsp",
        help="JPL BSPのURL",
    )
    parser.add_argument("--output", type=str, default="/tmp/de432s.bsp", help="保存先パス")
    parser.add_argument("--upload-s3", type=str, default="false", help="S3へアップロードするか (true/false)")
    parser.add_argument("--s3-bucket", type=str, default="", help="S3バケット名")
    parser.add_argument("--s3-key", type=str, default="de432s.bsp", help="S3オブジェクトキー")

    args = parser.parse_args(argv)

    try:
        if args.download_jpl.lower() == "true":
            download_file(args.jpl_url, args.output)
            print(f"downloaded: {args.jpl_url} -> {args.output}")
        if args.upload_s3.lower() == "true":
            if not args.s3_bucket:
                raise RuntimeError("S3バケット名が指定されていません (--s3-bucket)")
            upload_to_s3(args.output, args.s3_bucket, args.s3_key)
            print(f"uploaded: {args.output} -> s3://{args.s3_bucket}/{args.s3_key}")
        return 0
    except Exception as e:
        print(
            f"fetch_ephemeris.main: エラー url='{args.jpl_url}', output='{args.output}', "
            f"upload_s3='{args.upload_s3}', bucket='{args.s3_bucket}', key='{args.s3_key}', error='{e}'",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


