#!/bin/bash
# start-backend.sh
set -e

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

cd backend
export PYTHONPATH=$PYTHONPATH:$(pwd)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
