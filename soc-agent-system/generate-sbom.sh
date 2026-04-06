#!/bin/bash
# Generate Software Bill of Materials (SBOM) using Syft
# Produces CycloneDX JSON format for compliance and vulnerability tracking

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Generating SBOM (Software Bill of Materials)${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Check if Syft is installed
echo -e "${YELLOW}Step 1: Checking Syft installation...${NC}"
if command -v syft &>/dev/null; then
    SYFT_VERSION=$(syft version --output json | jq -r '.version' 2>/dev/null || syft version 2>&1 | head -1)
    echo -e "${GREEN}✅ Syft installed: $SYFT_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  Syft not found. Installing...${NC}"
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
    echo -e "${GREEN}✅ Syft installed${NC}"
fi
echo ""

# Generate SBOM for backend source
echo -e "${YELLOW}Step 2: Generating SBOM for backend source code...${NC}"
syft packages dir:backend -o cyclonedx-json > sbom-backend.json
echo -e "${GREEN}✅ sbom-backend.json created ($(wc -l < sbom-backend.json) lines)${NC}"
echo ""

# Generate SBOM for frontend source
echo -e "${YELLOW}Step 3: Generating SBOM for frontend source code...${NC}"
syft packages dir:frontend -o cyclonedx-json > sbom-frontend.json
echo -e "${GREEN}✅ sbom-frontend.json created ($(wc -l < sbom-frontend.json) lines)${NC}"
echo ""

# Generate SBOM for Docker images (if they exist)
echo -e "${YELLOW}Step 4: Generating SBOM for Docker images...${NC}"
if docker image inspect soc-backend:latest &>/dev/null; then
    syft packages docker:soc-backend:latest -o cyclonedx-json > sbom-backend-image.json
    echo -e "${GREEN}✅ sbom-backend-image.json created${NC}"
else
    echo -e "${YELLOW}⚠️  soc-backend:latest image not found. Run 'make build' first.${NC}"
fi

if docker image inspect soc-frontend:latest &>/dev/null; then
    syft packages docker:soc-frontend:latest -o cyclonedx-json > sbom-frontend-image.json
    echo -e "${GREEN}✅ sbom-frontend-image.json created${NC}"
else
    echo -e "${YELLOW}⚠️  soc-frontend:latest image not found. Run 'make build' first.${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ SBOM Generation Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Generated files:${NC}"
ls -lh sbom-*.json 2>/dev/null || echo "No SBOM files generated"
echo ""

# Analyze with jq if available
if command -v jq &>/dev/null && [ -f sbom-backend.json ]; then
    echo -e "${BLUE}📊 Backend SBOM Summary:${NC}"
    BACKEND_COMPONENTS=$(jq '.components | length' sbom-backend.json)
    echo -e "  Total components: ${GREEN}$BACKEND_COMPONENTS${NC}"
    
    echo -e "${BLUE}  Top 5 dependencies:${NC}"
    jq -r '.components[:5] | .[] | "    - \(.name)@\(.version)"' sbom-backend.json
    echo ""
fi

echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Review SBOM files: ${YELLOW}cat sbom-backend.json | jq${NC}"
echo -e "  2. Scan for vulnerabilities: ${YELLOW}grype sbom:sbom-backend.json${NC}"
echo -e "  3. Upload to compliance system"
echo ""
echo -e "${GREEN}Format: CycloneDX 1.5 JSON (OWASP standard)${NC}"
echo -e "${GREEN}Use case: Supply chain security, compliance audits, vulnerability tracking${NC}"
echo ""
