from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from .protocol import KnownStateHandler


class AWSS3KnownStateHandler(KnownStateHandler):
    """Known-state handler backed by an AWS S3 bucket."""

    def __init__(self, bucket_name: str, *, client: Any | None = None) -> None:
        self._bucket = bucket_name
        self._client: Any = boto3.client("s3") if client is None else client

    def has_key(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError:
            return False
        return True

    def get_all_keys(self) -> list[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def get_value(self, key: str) -> str:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            raise KeyError(key) from exc
        body: bytes = response["Body"].read()
        return body.decode("utf-8")

    def set_value(self, key: str, value: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=value)
