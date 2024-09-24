#!/bin/bash

# Check if an environment argument is provided
if [ $# -eq 0 ]; then
    echo "Please provide an environment (dev or prod)"
    exit 1
fi

# Set the environment variable
export ENVIRONMENT=$1

# Load the appropriate .env file
if [ -f .env.$ENVIRONMENT ]; then
    export $(grep -v '^#' .env.$ENVIRONMENT | xargs)
else
    echo ".env.$ENVIRONMENT file not found"
    exit 1
fi

# Run Alembic migrations
alembic upgrade head