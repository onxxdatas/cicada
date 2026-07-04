#!/usr/bin/env bash
# Creates .env from .env.example and fills in HOST_PROJECT_DIR automatically,
# since the backend needs the absolute HOST path to this folder (it asks the
# host docker daemon to mount ./data into the k6 containers it spawns).
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo ".env already exists — leaving it alone. Delete it first if you want to regenerate."
  exit 0
fi

cp .env.example .env
HOST_DIR="$(pwd)"

if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' "s#HOST_PROJECT_DIR=.*#HOST_PROJECT_DIR=${HOST_DIR}#" .env
else
  sed -i "s#HOST_PROJECT_DIR=.*#HOST_PROJECT_DIR=${HOST_DIR}#" .env
fi

echo "Wrote .env with HOST_PROJECT_DIR=${HOST_DIR}"
