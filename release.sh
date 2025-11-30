#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 LexiForge Release Script${NC}"
echo ""

# Parse version from manifest.json
VERSION=$(python3 -c "import json; print(json.load(open('manifest.json'))['human_version'])")
TAG="v${VERSION}"

echo -e "${YELLOW}Version: ${VERSION}${NC}"
echo -e "${YELLOW}Tag: ${TAG}${NC}"
echo ""

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo -e "${RED}❌ Tag ${TAG} already exists!${NC}"
    echo "If you want to re-release, delete the tag first:"
    echo "  git tag -d ${TAG}"
    echo "  git push origin :refs/tags/${TAG}"
    exit 1
fi

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}❌ You have uncommitted changes!${NC}"
    echo "Please commit or stash your changes first."
    git status -s
    exit 1
fi

echo -e "${GREEN}✓ No uncommitted changes${NC}"

# Files to include in release
RELEASE_FILES=(
    "__init__.py"
    "ai_client.py"
    "tts_client.py"
    "config.py"
    "language_constants.py"
    "manifest.json"
    "lexiforge_icon.svg"
)

# Build .ankiaddon package
echo ""
echo -e "${GREEN}📦 Building LexiForge.ankiaddon...${NC}"

rm -rf build_temp
mkdir -p build_temp

for file in "${RELEASE_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ File not found: $file${NC}"
        exit 1
    fi
    cp "$file" build_temp/
done

# Remove any __pycache__
find build_temp -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Create .ankiaddon
cd build_temp
zip -q -r ../LexiForge.ankiaddon * -x "*.pyc" -x "__pycache__/*"
cd ..
rm -rf build_temp

echo -e "${GREEN}✓ Created LexiForge.ankiaddon${NC}"

# Create git tag
echo ""
echo -e "${GREEN}🏷️  Creating git tag ${TAG}...${NC}"

# Add only release files to staging
git add "${RELEASE_FILES[@]}"

# Create tag with message
git tag -a "$TAG" -m "Release ${VERSION}

Files included in this release:
$(printf '%s\n' "${RELEASE_FILES[@]}" | sed 's/^/- /')"

echo -e "${GREEN}✓ Created tag ${TAG}${NC}"

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Release prepared successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Push tag to GitHub:"
echo -e "   ${YELLOW}git push origin ${TAG}${NC}"
echo ""
echo "2. Upload LexiForge.ankiaddon to:"
echo -e "   ${YELLOW}https://ankiweb.net/shared/upload${NC}"
echo ""
echo "3. Create GitHub Release:"
echo -e "   ${YELLOW}https://github.com/vpoltora/lexiforge/releases/new?tag=${TAG}${NC}"
echo "   - Attach: LexiForge.ankiaddon"
echo "   - Copy description from README.md"
echo ""
