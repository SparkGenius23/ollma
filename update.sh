#!/usr/bin/env bash
set -euo pipefail

git pull origin main

source venv/bin/activate
pip install -r requirements.txt


deactivate

sudo systemctl restart fastapi.service
sudo systemctl is-active --quiet fastapi.service
echo "fastapi.service restarted successfully"
