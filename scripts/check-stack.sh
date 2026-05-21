#!/bin/sh
# Smoke-test: hits /health on every running service.
# Exit 0 if all green, 1 on first failure.

set -e

# load .env into shell so port vars are available
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

fail() {
  echo "[FAIL] $1"
  exit 1
}

pass() {
  echo "[PASS] $1"
}

echo "==> checking api at port ${API_PORT}..."
curl -sf "http://localhost:${API_PORT}/health" > /dev/null && pass "api /health" || fail "api /health"

echo "==> checking modelserver at port ${MODELSERVER_PORT}..."
curl -sf "http://localhost:${MODELSERVER_PORT}/health" > /dev/null && pass "modelserver /health" || fail "modelserver /health"

echo "==> checking chatbot (streamlit) at port ${CHATBOT_PORT}..."
curl -sf "http://localhost:${CHATBOT_PORT}/_stcore/health" > /dev/null && pass "chatbot /_stcore/health" || fail "chatbot /_stcore/health"

echo "==> checking widget at port ${WIDGET_PORT}..."
curl -sf "http://localhost:${WIDGET_PORT}/" > /dev/null && pass "widget /" || fail "widget /"

echo "==> checking demo host at port ${HOST_PORT}..."
curl -sf "http://localhost:${HOST_PORT}/" > /dev/null && pass "host /" || fail "host /"

echo "==> checking langfuse at port ${LANGFUSE_PORT}..."
curl -sf "http://localhost:${LANGFUSE_PORT}/api/public/health" > /dev/null && pass "langfuse /api/public/health" || fail "langfuse /api/public/health"

echo "==> checking minio at port ${MINIO_API_PORT}..."
curl -sf "http://localhost:${MINIO_API_PORT}/minio/health/live" > /dev/null && pass "minio /minio/health/live" || fail "minio /minio/health/live"

echo ""
echo "All services healthy."
