#!/bin/bash
set -e
echo "=== startup.sh begin ==="

mkdir -p /home/data
cd /home/site/wwwroot

# Install dependencies into a persistent venv (survives restarts)
VENV_DIR="/home/site/wwwroot/antenv"
if [ ! -f "$VENV_DIR/bin/gunicorn" ]; then
    echo "Installing dependencies..."
    python3 -m venv "$VENV_DIR" --system-site-packages
    source "$VENV_DIR/bin/activate"
    pip install --no-cache-dir -r requirements.txt
else
    echo "Using existing venv..."
    source "$VENV_DIR/bin/activate"
fi

echo "Running migrations..."
python migrate.py || true

echo "Starting gunicorn..."
exec gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120
