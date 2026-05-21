#!/bin/sh
# Creates the required MinIO buckets on first boot.
# Runs once via a one-shot init container that waits for MinIO then exits.

set -e

echo "[minio-init] waiting for MinIO to be ready..."
until mc alias set local http://minio:9000 "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" 2>/dev/null; do
  sleep 2
done

echo "[minio-init] creating buckets..."
mc mb --ignore-existing local/models
mc mb --ignore-existing local/dataset
mc mb --ignore-existing local/corpus
mc mb --ignore-existing local/evals
mc mb --ignore-existing local/conversations

echo "[minio-init] done."
