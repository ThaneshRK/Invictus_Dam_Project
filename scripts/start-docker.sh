#!/bin/bash
set -e

echo "Starting Flood Simulation Framework Docker Stack..."

# Ensure secrets are not committed but exist for docker
if [ ! -f .env ]; then
    echo "No .env found. Copying .env.example..."
    cp .env.example .env
fi

# Build and start the stack in detached mode
export PATH="$HOME/.local/bin:$PATH"
docker-compose up --build -d

echo "Stack started successfully."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Database: localhost:5432"
