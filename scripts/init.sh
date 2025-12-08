#!/bin/bash
# init.sh - Initial setup script for Construction Dispatch System
# Run this script once when setting up the project for the first time

set -e  # Exit on error

echo "🚀 Initializing Construction Dispatch System..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the project root
if [ ! -f "manage.py" ]; then
    echo "❌ Error: manage.py not found. Please run this script from the project root."
    exit 1
fi

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"
echo ""

# Install dependencies
echo -e "${BLUE}Installing dependencies from requirements.txt...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠ requirements.txt not found, skipping...${NC}"
fi
echo ""

# Create necessary directories
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p media/avatars
mkdir -p media/invoices
mkdir -p media/project_files
mkdir -p media/purchase_orders
mkdir -p staticfiles
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Run migrations
echo -e "${BLUE}Running database migrations...${NC}"
python manage.py migrate
echo -e "${GREEN}✓ Migrations completed${NC}"
echo ""

# Collect static files
echo -e "${BLUE}Collecting static files...${NC}"
python manage.py collectstatic --no-input
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

# Ask if user wants to create superuser
echo -e "${YELLOW}Do you want to create a superuser? (y/n)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${BLUE}Creating superuser...${NC}"
    python manage.py createsuperuser
    echo -e "${GREEN}✓ Superuser created${NC}"
else
    echo "Skipping superuser creation"
fi
echo ""

# Show next steps
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Initialization complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Start the development server:"
echo "     ${BLUE}./scripts/start.sh${NC}"
echo ""
echo "  2. Run tests:"
echo "     ${BLUE}./scripts/test.sh${NC}"
echo ""
echo "  3. Access the application:"
echo "     ${BLUE}http://localhost:8000/${NC}"
echo ""
echo "  4. Access Django admin:"
echo "     ${BLUE}http://localhost:8000/admin/${NC}"
echo ""
