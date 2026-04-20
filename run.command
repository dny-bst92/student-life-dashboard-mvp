#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

.venv/bin/pip install -r requirements.txt
exec .venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1
