from __future__ import annotations

from azure.core.credentials import TokenCredential
from azure.storage.blob import BlobServiceClient

from .protocol import KnownStateHandler


class AzureStorageKnownStateHandler(KnownStateHandler):
    """Known-state handler backed by Azure Blob Storage."""

    def __init__(self, account_url: str, credential: TokenCredential, container_name: str) -> None:
        self._container = BlobServiceClient(
            account_url, credential=credential
        ).get_container_client(container_name)

    def has_key(self, key: str) -> bool:
        return self._container.get_blob_client(key).exists()

    def get_all_keys(self) -> list[str]:
        return list(self._container.list_blob_names())

    def get_value(self, key: str) -> str:
        blob = self._container.get_blob_client(key)
        if not blob.exists():
            raise KeyError(key)
        return blob.download_blob(encoding="utf-8").readall()

    def set_value(self, key: str, value: str) -> None:
        self._container.get_blob_client(key).upload_blob(value, overwrite=True)
