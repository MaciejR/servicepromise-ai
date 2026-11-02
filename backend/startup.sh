#!/bin/sh
set -eu
# /home is the persistent App Service filesystem. Keep one worker/instance
# while this demo uses SQLite; move to PostgreSQL before scaling out.
mkdir -p /home/servicepromise
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
