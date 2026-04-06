#!/bin/bash
# Development Environment Setup Script
# Creates virtual environment and installs all dependencies

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Setting Up Development Environment${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""

# Check if we're in the correct directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: requirements.txt not found${NC}"
    echo -e "${YELLOW}Please run this script from soc-agent-system/backend directory${NC}"
    exit 1
fi

# Check Python version - prefer 3.11 to match Docker image
echo -e "${YELLOW}Step 1: Checking Python version...${NC}"

# Try to find Python 3.11 (matches Docker image)
if command -v python3.11 &>/dev/null; then
    PYTHON_CMD="python3.11"
    PYTHON_VERSION=$(python3.11 --version)
    echo -e "${GREEN}✅ Found Python 3.11: $PYTHON_VERSION${NC}"
    echo -e "${GREEN}   (Matches Docker image - recommended!)${NC}"
# Fall back to Python 3.9 or 3.10 (compatible with dependencies)
elif command -v python3.10 &>/dev/null; then
    PYTHON_CMD="python3.10"
    PYTHON_VERSION=$(python3.10 --version)
    echo -e "${GREEN}✅ Found Python 3.10: $PYTHON_VERSION${NC}"
elif command -v python3.9 &>/dev/null; then
    PYTHON_CMD="python3.9"
    PYTHON_VERSION=$(python3.9 --version)
    echo -e "${GREEN}✅ Found Python 3.9: $PYTHON_VERSION${NC}"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version)
    # Check if it's 3.13+ (incompatible)
    if [[ "$PYTHON_VERSION" =~ 3\.13 ]] || [[ "$PYTHON_VERSION" =~ 3\.14 ]]; then
        echo -e "${RED}❌ Error: $PYTHON_VERSION is too new!${NC}"
        echo -e "${YELLOW}pydantic-core 2.14.6 doesn't support Python 3.13+${NC}"
        echo ""
        echo -e "${YELLOW}Please install Python 3.11:${NC}"
        echo -e "${YELLOW}  brew install python@3.11${NC}"
        echo -e "${YELLOW}Then run this script again.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Error: python3 not found${NC}"
    echo -e "${YELLOW}Please install Python 3.9, 3.10, or 3.11${NC}"
    echo -e "${YELLOW}Recommended: brew install python@3.11${NC}"
    exit 1
fi
echo ""

# Create virtual environment
echo -e "${YELLOW}Step 2: Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  venv directory already exists${NC}"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo -e "${GREEN}✅ Virtual environment recreated${NC}"
    else
        echo -e "${YELLOW}Using existing venv${NC}"
    fi
else
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✅ Virtual environment created with $PYTHON_CMD${NC}"
fi
echo ""

# Activate virtual environment
echo -e "${YELLOW}Step 3: Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"
echo ""

# Upgrade pip
echo -e "${YELLOW}Step 4: Upgrading pip...${NC}"
pip install --upgrade pip==24.0
echo -e "${GREEN}✅ pip upgraded to 24.0${NC}"
echo ""

# Install requirements
echo -e "${YELLOW}Step 5: Installing dependencies from requirements.txt...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Install development tools
echo -e "${YELLOW}Step 6: Installing development tools...${NC}"
pip install ruff==0.1.14 pytest==7.4.4 pytest-cov==4.1.0 pytest-asyncio==0.23.3
echo -e "${GREEN}✅ Development tools installed${NC}"
echo ""

# Verify installation
echo -e "${YELLOW}Step 7: Verifying installation...${NC}"
echo -n "  ruff: "
ruff --version
echo -n "  pytest: "
pytest --version
echo -n "  python: "
python --version
echo -e "${GREEN}✅ All tools verified${NC}"
echo ""

# Success message
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Development Environment Ready!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "To activate the virtual environment in the future:"
echo -e "  ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo -e "To run quality checks:"
echo -e "  ${YELLOW}cd ../.. && make quality-gate${NC}"
echo ""
echo -e "To run tests:"
echo -e "  ${YELLOW}pytest tests/${NC}"
echo ""
echo -e "To deactivate when done:"
echo -e "  ${YELLOW}deactivate${NC}"
echo ""
