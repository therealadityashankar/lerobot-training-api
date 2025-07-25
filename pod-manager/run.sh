#!/bin/bash

# Setup database if it doesn't exist
if [ ! -f "pod_manager.db" ]; then
    echo "Setting up database..."
    mkdir -p db
    export $(grep -v '^#' .env.dbmate | xargs)
    dbmate up
fi

# Run the API server
echo "Starting pod manager API..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
