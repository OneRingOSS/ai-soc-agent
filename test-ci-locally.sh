#!/bin/bash
# Test CI Workflow Locally
# Simulates GitHub Actions CI environment without venv

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Testing CI Workflow Locally (No venv)${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""

# Backup venv if it exists
if [ -d "soc-agent-system/backend/venv" ]; then
    echo -e "${YELLOW}Temporarily moving venv to simulate CI environment...${NC}"
    mv soc-agent-system/backend/venv soc-agent-system/backend/venv.backup
    RESTORE_VENV=true
fi

# Trap to restore venv on exit
cleanup() {
    if [ "$RESTORE_VENV" = true ]; then
        echo ""
        echo -e "${YELLOW}Restoring venv...${NC}"
        mv soc-agent-system/backend/venv.backup soc-agent-system/backend/venv 2>/dev/null || true
    fi
}
trap cleanup EXIT

# Test 1: Make lint (with system ruff)
echo -e "${YELLOW}Test 1: make lint (expects system ruff)${NC}"
cd soc-agent-system
if make -n lint | grep -q "ruff check"; then
    echo -e "${GREEN}✅ Makefile uses system ruff (no venv path)${NC}"
else
    echo -e "${RED}❌ Makefile still references venv${NC}"
    exit 1
fi
echo ""

# Test 2: Make test (with system pytest)
echo -e "${YELLOW}Test 2: make test (expects system pytest)${NC}"
if make -n test | grep -q "pytest tests"; then
    echo -e "${GREEN}✅ Makefile uses system pytest (no venv path)${NC}"
else
    echo -e "${RED}❌ Makefile still references venv${NC}"
    exit 1
fi
echo ""

# Test 3: Verify Makefile variable detection
echo -e "${YELLOW}Test 3: Verify Makefile detects no venv${NC}"
if make -n lint 2>&1 | grep -q "backend/venv"; then
    echo -e "${RED}❌ Makefile incorrectly detecting venv${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Makefile correctly using system binaries${NC}"
fi
echo ""

# Test 4: Check scan-dependencies
echo -e "${YELLOW}Test 4: scan-dependencies (expects system pip-audit)${NC}"
if make -n scan-dependencies | grep -q "pip-audit"; then
    echo -e "${GREEN}✅ Uses system pip-audit${NC}"
else
    echo -e "${RED}❌ Still references venv${NC}"
    exit 1
fi
echo ""

# Test 5: Check scan-workflows
echo -e "${YELLOW}Test 5: scan-workflows (expects system zizmor)${NC}"
if make -n scan-workflows | grep -q "zizmor"; then
    echo -e "${GREEN}✅ Uses system zizmor${NC}"
else
    echo -e "${RED}❌ Still references venv${NC}"
    exit 1
fi
echo ""

cd ..

# Summary
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ All CI Simulation Tests Passed!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Makefile correctly:${NC}"
echo -e "  ✅ Detects absence of venv"
echo -e "  ✅ Falls back to system binaries (ruff, pytest, pip-audit, zizmor)"
echo -e "  ✅ Ready for CI environment"
echo ""
echo -e "${YELLOW}Next: Test with venv present (local dev)${NC}"
echo ""
