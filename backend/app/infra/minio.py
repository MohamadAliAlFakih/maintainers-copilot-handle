"""MinIO blob adapter — thin wrapper around the official minio client."""

from minio import Minio


def build_minio_client(
    endpoint: str, access_key: str, secret_key: str, secure: bool = False
) -> Minio:
    """Builds a configured MinIO client. Called once at startup, attached to app.state."""
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


REQUIRED_BUCKETS = ("models", "dataset", "corpus", "evals", "conversations")


def assert_buckets_exist(client: Minio) -> list[str]:
    """Returns list of missing buckets; empty list means all present."""
    missing = []
    for name in REQUIRED_BUCKETS:
        if not client.bucket_exists(name):
            missing.append(name)
    return missing
