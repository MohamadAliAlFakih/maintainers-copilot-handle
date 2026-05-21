"""MinIO client for modelserver — used to pull model weights at startup."""

from minio import Minio


def build_minio_client(
    endpoint: str, access_key: str, secret_key: str, secure: bool = False
) -> Minio:
    """Builds a MinIO client. Same shape as backend's adapter."""
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def fetch_object_bytes(client: Minio, bucket: str, key: str) -> bytes:
    """Pulls an object's full bytes into memory."""
    resp = client.get_object(bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()
