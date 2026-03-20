#!/bin/bash
# Azure App Service startup script
cd /home/site/wwwroot
pip install -r requirements.txt
python migrate.py
gunicorn main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
