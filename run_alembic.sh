#!/bin/bash

# Check if an environment argument is provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 <environment> <alembic_command>"
    exit 1
fi

# Set the environment variable
export ENVIRONMENT=$1
echo "Setting ENVIRONMENT to: $ENVIRONMENT"

# Shift the first argument so we can pass the rest to alembic
shift

# Load the appropriate .env file
if [ "$ENVIRONMENT" = "prod" ]; then
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    else
        echo ".env file not found"
        exit 1
    fi
elif [ "$ENVIRONMENT" = "dev" ]; then
    if [ -f ".env.dev" ]; then
        export $(grep -v '^#' .env.dev | xargs)
    else
        echo ".env.dev file not found"
        exit 1
    fi
else
    echo "Invalid environment. Use 'prod' or 'dev'."
    exit 1
fi

# Run Alembic with the provided arguments
PYTHONPATH=. alembic "$@"