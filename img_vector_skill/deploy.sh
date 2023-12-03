#!/bin/bash

# Load environment variables from .env file
export $(grep -v '^#' ../.env | xargs)

# Check the command line argument
if [ "$1" == "build" ]; then
    # Build the Docker image
    docker build -t myskill .
elif [ "$1" == "run" ]; then
    # Run the Docker container, mapping port 8000 to 8000 and setting environment variables
    docker run -p 8000:8000 -e AZURE_AI_KEY=$AZURE_AI_KEY -e STORAGE_CONNNECTION_STRING="$STORAGE_CONNNECTION_STRING" -e OPENAI_API_KEY=$OPENAI_API_KEY myskill
elif [ "$1" == "up" ]; then
    az containerapp up -n myskill --ingress external --target-port 8000 \
        --env-vars AZURE_AI_KEY=$AZURE_AI_KEY STORAGE_CONNNECTION_STRING="$STORAGE_CONNNECTION_STRING" OPENAI_API_KEY=$OPENAI_API_KEY \
        --source .
else
    echo "Usage: $0 {build|run|up}"
fi