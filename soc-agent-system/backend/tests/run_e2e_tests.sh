#!/bin/bash
# E2E Test Runner - Verifies SOC Agent functionality end-to-end
# Tests Wazuh threat processing → analysis → detection

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SOC Agent E2E Test Suite${NC}"
echo -e "${BLUE}  Verifies: Wazuh → Analysis → Dashboard Pipeline${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"

# Navigate to backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

# Check Python environment
echo -e "${YELLOW}[1/4] Checking Python environment...${NC}"
if [ ! -d "venv" ] && [ -z "$VIRTUAL_ENV" ] && [ -z "$CI" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo -e "${YELLOW}Please run:${NC}"
    echo -e "  cd soc-agent-system/backend"
    echo -e "  python3 -m venv venv"
    echo -e "  source venv/bin/activate"
    echo -e "  pip install -r requirements.txt"
    exit 1
fi

# Activate venv if not already
if [ -z "$VIRTUAL_ENV" ] && [ -z "$CI" ]; then
    source venv/bin/activate
fi
echo -e "${GREEN}✅ Python environment ready${NC}\n"

# Check Redis
echo -e "${YELLOW}[2/4] Checking Redis connection...${NC}"
if python3 -c "import socket; s = socket.socket(); s.settimeout(1); s.connect(('localhost', 6379)); s.close()" 2>/dev/null; then
    echo -e "${GREEN}✅ Redis available on localhost:6379${NC}\n"
else
    echo -e "${YELLOW}⚠️  Redis not running. Starting with Docker...${NC}"
    if docker ps -a --format '{{.Names}}' | grep -q '^redis-test$'; then
        docker start redis-test > /dev/null 2>&1
    else
        docker run -d -p 6379:6379 --name redis-test redis:7-alpine > /dev/null 2>&1
    fi
    sleep 2
    echo -e "${GREEN}✅ Redis started${NC}\n"
fi

# Run E2E tests
echo -e "${YELLOW}[3/4] Running E2E Tests...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Set PYTHONPATH
export PYTHONPATH=src

# Run all E2E tests with pytest
pytest tests/test_e2e_*.py -v -m e2e --tb=short

TEST_EXIT_CODE=$?

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Summary
echo -e "${YELLOW}[4/4] Test Summary${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ ALL E2E TESTS PASSED!${NC}\n"
    
    echo -e "${BLUE}What was tested:${NC}"
    echo -e "  ✅ Note poisoning detection (mass fabrication)"
    echo -e "  ✅ Coordinated attack detection (context + historical)"
    echo -e "  ✅ Context manipulation detection (geo-IP mismatch)"
    echo -e "  ✅ Historical attack detection (fake analyst notes)"
    echo -e "  ✅ AdversarialDetector infrastructure contradiction"
    echo -e "  ✅ Multi-agent coordination"
    echo -e ""
    echo -e "${GREEN}🎉 SOC Agent core functionality verified!${NC}"
    echo -e "${GREEN}🚀 No regressions detected - safe to deploy!${NC}"
else
    echo -e "${RED}❌ SOME E2E TESTS FAILED${NC}"
    echo -e "${YELLOW}Check the output above for details${NC}"
    echo -e "${YELLOW}This indicates a regression in core SOC agent functionality${NC}"
fi

echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"

exit $TEST_EXIT_CODE
