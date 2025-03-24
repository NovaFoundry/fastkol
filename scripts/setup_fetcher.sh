#!/bin/bash

# Define color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project root directory
PROJECT_ROOT="$(dirname "$0")/.."
cd "$PROJECT_ROOT" || exit

echo -e "${GREEN}Setting up Python virtual environment for GraphWeaver Fetcher...${NC}"

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo -e "${YELLOW}Please install Python 3.8 or higher first${NC}"
    exit 1
fi

# Check Python version
if ! python3 -c "import sys; assert sys.version_info >= (3, 8), f'Python version must be 3.8 or higher (found {sys.version_info.major}.{sys.version_info.minor})'"; then
    echo -e "${RED}Error: Python version must be 3.8 or higher${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "graph-weaver-fetcher" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv graph-weaver-fetcher
else
    echo -e "${YELLOW}Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source graph-weaver-fetcher/bin/activate || {
    echo -e "${RED}Failed to activate virtual environment${NC}"
    exit 1
}

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Get the Fetcher directory path relative to the script
FETCHER_DIR="$(dirname "$0")/../Fetcher"

# Install requirements
echo -e "${GREEN}Installing requirements...${NC}"
pip install -r "${FETCHER_DIR}/requirements.txt" || {
    echo -e "${RED}Failed to install requirements${NC}"
    exit 1
}

# Install Playwright browsers
echo -e "${GREEN}Installing Playwright browsers...${NC}"
playwright install chromium

# Verify installation
echo -e "${GREEN}Verifying installation...${NC}"
python -c "import aiohttp, celery, playwright, asyncio" || {
    echo -e "${RED}Some packages failed to install correctly${NC}"
    exit 1
}

echo -e "${GREEN}Virtual environment setup complete!${NC}"
echo -e "${YELLOW}To activate the virtual environment, run:${NC}"
echo -e "source graph-weaver-fetcher/bin/activate" 