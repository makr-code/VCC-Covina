#!/bin/bash
# VCC-Covina Docker Build Script
# Phase 1: Foundation Enhancement

set -e

# Configuration
REGISTRY="${REGISTRY:-registry.local}"
VERSION="${VERSION:-3.4.11}"
PUSH="${PUSH:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== VCC-Covina Docker Build ===${NC}"
echo "Registry: $REGISTRY"
echo "Version: $VERSION"
echo ""

# Navigate to project root
cd "$(dirname "$0")/../.."

# Build Main Backend
echo -e "${YELLOW}Building Main Backend...${NC}"
docker build \
    -f deploy/docker/Dockerfile.main-backend \
    -t ${REGISTRY}/covina/main-backend:${VERSION} \
    -t ${REGISTRY}/covina/main-backend:latest \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Main Backend built successfully${NC}"
else
    echo -e "${RED}✗ Main Backend build failed${NC}"
    exit 1
fi

# Build Ingestion Backend
echo -e "${YELLOW}Building Ingestion Backend...${NC}"
docker build \
    -f deploy/docker/Dockerfile.ingestion-backend \
    -t ${REGISTRY}/covina/ingestion-backend:${VERSION} \
    -t ${REGISTRY}/covina/ingestion-backend:latest \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Ingestion Backend built successfully${NC}"
else
    echo -e "${RED}✗ Ingestion Backend build failed${NC}"
    exit 1
fi

# Push images if requested
if [ "$PUSH" = "true" ]; then
    echo -e "${YELLOW}Pushing images to registry...${NC}"
    
    docker push ${REGISTRY}/covina/main-backend:${VERSION}
    docker push ${REGISTRY}/covina/main-backend:latest
    docker push ${REGISTRY}/covina/ingestion-backend:${VERSION}
    docker push ${REGISTRY}/covina/ingestion-backend:latest
    
    echo -e "${GREEN}✓ Images pushed successfully${NC}"
fi

echo ""
echo -e "${GREEN}=== Build Complete ===${NC}"
echo "Images:"
echo "  - ${REGISTRY}/covina/main-backend:${VERSION}"
echo "  - ${REGISTRY}/covina/ingestion-backend:${VERSION}"
echo ""
echo "To push to registry: PUSH=true ./deploy/docker/build.sh"
