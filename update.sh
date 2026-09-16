#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

git pull origin main

source venv/bin/activate
pip install -r requirements.txt

# Validate the deployment-local database configuration without printing it.
python - <<'PY'
from pathlib import Path
from dotenv import load_dotenv
import os

env_file = Path(".env")
if not env_file.is_file():
    raise SystemExit("Deployment aborted: .env file is missing")
load_dotenv(env_file)
if not os.getenv("DATABASE_URL"):
    raise SystemExit("Deployment aborted: DATABASE_URL is missing or empty in .env")
print("Validated .env and DATABASE_URL configuration")
PY

deactivate

sudo systemctl restart fastapi.service
sudo systemctl is-active --quiet fastapi.service
echo "fastapi.service restarted successfully"
