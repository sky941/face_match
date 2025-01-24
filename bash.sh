#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Docker build and run process..."

# Step 1: Check if Docker is installed
if ! command -v docker &> /dev/null
then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Step 2: Build the Docker image
echo "Building the Docker image..."
docker build -t fastapi-face-recognition .

# Step 3: Run the Docker container
echo "Running the Docker container..."
docker run -d -p 8000:8000 --name fastapi-app fastapi-face-recognition

# Step 4: Show running containers
echo "Showing running containers..."
docker ps

echo "FastAPI app is now running at http://localhost:8000"
