#!/bin/bash

# Define color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define environment variables
ENV=${1:-dev}  # Default to dev environment
DOCKER_DIR="$(dirname "$0")/../docker"

echo -e "${GREEN}Deploying Social Media Crawler System - ${ENV} Environment${NC}"

# Change to Docker directory
cd "$DOCKER_DIR" || exit

# Set compose files and environment paths
COMPOSE_FILES="-f docker-compose.base.yml -f environments/${ENV}/docker-compose.yml"
ENV_FILE="environments/${ENV}/.env"

# Verify that environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: Environment file $ENV_FILE not found${NC}"
    exit 1
fi

# Create volume directories if they don't exist
mkdir -p volumes/postgres
mkdir -p volumes/rabbitmq

# Stop and remove existing containers
echo -e "${GREEN}Stopping existing containers...${NC}"
docker compose --env-file "$ENV_FILE" $COMPOSE_FILES down

# Build new images
echo -e "${GREEN}Building images...${NC}"
export DOCKER_BUILDKIT=1
docker compose --env-file "$ENV_FILE" $COMPOSE_FILES build

# Start services
echo -e "${GREEN}Starting services...${NC}"
docker compose --env-file "$ENV_FILE" $COMPOSE_FILES up -d

# Wait for services to start
echo -e "${GREEN}Waiting for services to start...${NC}"
sleep 5

# Check service status
echo -e "${GREEN}Checking service status:${NC}"
docker compose --env-file "$ENV_FILE" $COMPOSE_FILES ps

echo -e "${GREEN}Deployment complete!${NC}" 