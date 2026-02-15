#!/bin/bash
#
# Integration Test Runner for Redis Pub/Sub Cross-Pod Broadcasting
#
# This script:
# 1. Checks if Redis is running
# 2. Starts Redis if needed (using Docker)
# 3. Runs the integration tests
# 4. Provides clear output and error messages
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Redis Pub/Sub Integration Test Runner${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if Redis is running
echo -e "${YELLOW}[1/4] Checking Redis connection...${NC}"
if redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is running on localhost:6379${NC}\n"
    REDIS_STARTED_BY_SCRIPT=false
else
    echo -e "${YELLOW}⚠️  Redis not running. Attempting to start with Docker...${NC}"
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found. Please install Docker or start Redis manually.${NC}"
        echo -e "${YELLOW}To start Redis manually:${NC}"
        echo -e "  docker run -d -p 6379:6379 --name redis-test redis:7-alpine"
        exit 1
    fi
    
    # Check if redis-test container already exists
    if docker ps -a --format '{{.Names}}' | grep -q '^redis-test$'; then
        echo -e "${YELLOW}Starting existing redis-test container...${NC}"
        docker start redis-test > /dev/null
    else
        echo -e "${YELLOW}Creating new redis-test container...${NC}"
        docker run -d -p 6379:6379 --name redis-test redis:7-alpine > /dev/null
    fi
    
    # Wait for Redis to be ready
    echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
    for i in {1..10}; do
        if redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Redis started successfully${NC}\n"
            REDIS_STARTED_BY_SCRIPT=true
            break
        fi
        sleep 1
    done
    
    if ! redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
        echo -e "${RED}❌ Failed to start Redis${NC}"
        exit 1
    fi
fi

# Check Python environment
echo -e "${YELLOW}[2/4] Checking Python environment...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Please run:${NC}"
    echo -e "  python3 -m venv venv"
    echo -e "  source venv/bin/activate"
    echo -e "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment if not already activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

echo -e "${GREEN}✅ Python environment ready${NC}\n"

# Run integration tests
echo -e "${YELLOW}[3/4] Running integration tests...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py -v -m integration -s

TEST_EXIT_CODE=$?

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Summary
echo -e "${YELLOW}[4/4] Test Summary${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All integration tests passed!${NC}\n"
    
    echo -e "${BLUE}What was tested:${NC}"
    echo -e "  ✅ Redis storage and retrieval"
    echo -e "  ✅ Single subscriber Pub/Sub"
    echo -e "  ✅ Multiple subscribers on same pod"
    echo -e "  ✅ Cross-pod broadcasting (3 pods, 3 clients)"
    echo -e "  ✅ Multiple threats ordering"
    echo -e ""
    echo -e "${GREEN}🚀 Your SOC Agent System is ready for Kubernetes deployment!${NC}"
else
    echo -e "${RED}❌ Some integration tests failed${NC}"
    echo -e "${YELLOW}Check the output above for details${NC}"
fi

# Cleanup prompt
if [ "$REDIS_STARTED_BY_SCRIPT" = true ]; then
    echo -e "\n${YELLOW}Redis was started by this script.${NC}"
    echo -e "${YELLOW}To stop Redis:${NC} docker stop redis-test"
    echo -e "${YELLOW}To remove Redis:${NC} docker rm redis-test"
fi

echo -e "\n${BLUE}========================================${NC}"

exit $TEST_EXIT_CODE

