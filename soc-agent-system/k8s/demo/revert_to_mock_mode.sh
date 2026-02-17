#!/bin/bash

# Script to revert backend to mock mode (no OpenAI API calls)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "=========================================="
echo "  Revert to Mock Mode"
echo "=========================================="
echo -e "${NC}"

echo -e "${BLUE}[1/3] Removing OpenAI API key from deployment...${NC}"

# Remove the OPENAI_API_KEY and set FORCE_MOCK_MODE=1
kubectl set env deployment/soc-agent-backend -n soc-agent-demo \
    OPENAI_API_KEY- \
    FORCE_MOCK_MODE=1

echo -e "${GREEN}✅ Environment variables updated${NC}\n"

echo -e "${BLUE}[2/3] Deleting OpenAI API key secret...${NC}"
kubectl delete secret openai-api-key -n soc-agent-demo --ignore-not-found=true

echo -e "${GREEN}✅ Secret deleted${NC}\n"

echo -e "${BLUE}[3/3] Waiting for backend pods to restart...${NC}"
kubectl rollout status deployment/soc-agent-backend -n soc-agent-demo --timeout=120s

echo -e "${GREEN}✅ Backend pods restarted${NC}\n"

echo -e "${GREEN}=========================================="
echo "  ✅ Reverted to Mock Mode!"
echo "==========================================${NC}\n"

echo -e "The backend is now using mock threat analysis (no API costs).\n"

