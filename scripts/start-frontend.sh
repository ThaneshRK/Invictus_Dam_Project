#!/bin/bash
# start-frontend.sh
set -e

cd frontend
echo "Starting frontend at http://localhost:8080"
python3 -m http.server 8080
