#!/bin/bash
# reset.sh - Reset the development environment
# Useful for cleaning up and starting fresh

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}⚠️  Reset Development Environment${NC}"
echo ""
echo -e "${RED}This will:${NC}"
echo "  • Kill all running servers"
echo "  • Remove staticfiles/"
echo "  • Remove __pycache__ directories"
echo "  • Remove .pyc files"
echo ""
echo -e "${YELLOW}Do you want to continue? (y/n)${NC}"
read -r response

if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Reset cancelled"
    exit 0
fi

echo ""
echo -e "${BLUE}Starting reset process...${NC}"
echo ""

# Kill servers
echo -e "${BLUE}1. Killing running servers...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}✓ Servers stopped${NC}"
echo ""

# Remove staticfiles
echo -e "${BLUE}2. Removing staticfiles...${NC}"
if [ -d "staticfiles" ]; then
    rm -rf staticfiles/
    echo -e "${GREEN}✓ Staticfiles removed${NC}"
else
    echo -e "${YELLOW}⚠ staticfiles/ not found${NC}"
fi
echo ""

# Remove __pycache__ directories
echo -e "${BLUE}3. Removing __pycache__ directories...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ __pycache__ directories removed${NC}"
echo ""

# Remove .pyc files
echo -e "${BLUE}4. Removing .pyc files...${NC}"
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✓ .pyc files removed${NC}"
echo ""

# Remove .pytest_cache
echo -e "${BLUE}5. Removing test cache...${NC}"
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ Test cache removed${NC}"
echo ""

# Ask about database reset
echo -e "${YELLOW}Do you want to reset the database? (y/n)${NC}"
echo -e "${RED}⚠ WARNING: This will DELETE ALL DATA!${NC}"
read -r db_response

if [[ "$db_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${BLUE}6. Resetting database...${NC}"
    if [ -f "db.sqlite3" ]; then
        rm db.sqlite3
        echo -e "${GREEN}✓ Database removed${NC}"

        echo -e "${BLUE}Running migrations...${NC}"
        python manage.py migrate
        echo -e "${GREEN}✓ Fresh database created${NC}"

        echo ""
        echo -e "${YELLOW}Do you want to create a superuser? (y/n)${NC}"
        read -r superuser_response
        if [[ "$superuser_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            python manage.py createsuperuser
        fi
    else
        echo -e "${YELLOW}⚠ db.sqlite3 not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Database reset skipped${NC}"
fi
echo ""

# Collect static files
echo -e "${BLUE}7. Collecting static files...${NC}"
python manage.py collectstatic --no-input
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

# Final message
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Reset complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Start the server: ${GREEN}./scripts/start.sh${NC}"
echo "  2. Run tests: ${GREEN}./scripts/test.sh${NC}"
