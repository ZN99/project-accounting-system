#!/bin/bash
# status.sh - Check the status of the development environment
# Shows server status, pending migrations, and system health

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 Construction Dispatch System Status${NC}"
echo ""

# Check if we're in the project root
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: manage.py not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Check server status
echo -e "${BLUE}1. Server Status:${NC}"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    PID=$(lsof -ti:8000)
    echo -e "   ${GREEN}✓ Server is running on port 8000 (PID: $PID)${NC}"
    echo -e "   ${GREEN}  http://localhost:8000/${NC}"
else
    echo -e "   ${YELLOW}⚠ Server is not running${NC}"
    echo -e "   ${BLUE}  Start with: ./scripts/start.sh${NC}"
fi
echo ""

# Check Python version
echo -e "${BLUE}2. Python Environment:${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "   Python version: ${GREEN}$PYTHON_VERSION${NC}"
echo ""

# Check Django version
echo -e "${BLUE}3. Django Version:${NC}"
DJANGO_VERSION=$(python -c "import django; print(django.get_version())" 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "   Django version: ${GREEN}$DJANGO_VERSION${NC}"
else
    echo -e "   ${RED}✗ Django not installed${NC}"
fi
echo ""

# Check database
echo -e "${BLUE}4. Database Status:${NC}"
if [ -f "db.sqlite3" ]; then
    DB_SIZE=$(du -h db.sqlite3 | cut -f1)
    echo -e "   ${GREEN}✓ Database exists (Size: $DB_SIZE)${NC}"
else
    echo -e "   ${YELLOW}⚠ Database file not found${NC}"
    echo -e "   ${BLUE}  Run migrations: python manage.py migrate${NC}"
fi
echo ""

# Check pending migrations
echo -e "${BLUE}5. Migrations Status:${NC}"
PENDING_MIGRATIONS=$(python manage.py showmigrations --plan 2>/dev/null | grep -c "\[ \]" || true)
APPLIED_MIGRATIONS=$(python manage.py showmigrations --plan 2>/dev/null | grep -c "\[X\]" || true)
echo -e "   Applied migrations: ${GREEN}$APPLIED_MIGRATIONS${NC}"
if [ "$PENDING_MIGRATIONS" -gt 0 ]; then
    echo -e "   ${YELLOW}⚠ Pending migrations: $PENDING_MIGRATIONS${NC}"
    echo -e "   ${BLUE}  Apply with: python manage.py migrate${NC}"
else
    echo -e "   ${GREEN}✓ No pending migrations${NC}"
fi
echo ""

# Check static files
echo -e "${BLUE}6. Static Files:${NC}"
if [ -d "staticfiles" ]; then
    STATIC_COUNT=$(find staticfiles -type f 2>/dev/null | wc -l | tr -d ' ')
    echo -e "   ${GREEN}✓ Static files collected ($STATIC_COUNT files)${NC}"
else
    echo -e "   ${YELLOW}⚠ Static files not collected${NC}"
    echo -e "   ${BLUE}  Collect with: python manage.py collectstatic${NC}"
fi
echo ""

# Check media directory
echo -e "${BLUE}7. Media Directory:${NC}"
if [ -d "media" ]; then
    MEDIA_SIZE=$(du -sh media 2>/dev/null | cut -f1)
    echo -e "   ${GREEN}✓ Media directory exists (Size: $MEDIA_SIZE)${NC}"
else
    echo -e "   ${YELLOW}⚠ Media directory not found${NC}"
fi
echo ""

# Check installed packages
echo -e "${BLUE}8. Dependencies:${NC}"
if [ -f "requirements.txt" ]; then
    REQUIRED_PACKAGES=$(wc -l < requirements.txt | tr -d ' ')
    echo -e "   Required packages: ${GREEN}$REQUIRED_PACKAGES${NC}"

    # Check if all required packages are installed
    MISSING_PACKAGES=0
    while IFS= read -r package; do
        # Skip empty lines and comments
        [[ -z "$package" || "$package" =~ ^# ]] && continue

        # Extract package name (before ==, >=, etc.)
        PKG_NAME=$(echo "$package" | sed 's/[=><!].*//' | tr -d '[:space:]')

        # Check if installed
        if ! pip list 2>/dev/null | grep -i "^$PKG_NAME " >/dev/null 2>&1; then
            MISSING_PACKAGES=$((MISSING_PACKAGES + 1))
        fi
    done < requirements.txt

    if [ $MISSING_PACKAGES -eq 0 ]; then
        echo -e "   ${GREEN}✓ All dependencies installed${NC}"
    else
        echo -e "   ${YELLOW}⚠ Missing $MISSING_PACKAGES package(s)${NC}"
        echo -e "   ${BLUE}  Install with: pip install -r requirements.txt${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠ requirements.txt not found${NC}"
fi
echo ""

# System check
echo -e "${BLUE}9. Django System Check:${NC}"
DJANGO_CHECK=$(python manage.py check 2>&1)
if [ $? -eq 0 ]; then
    echo -e "   ${GREEN}✓ No system check errors${NC}"
else
    echo -e "   ${RED}✗ System check found issues:${NC}"
    echo "$DJANGO_CHECK" | head -5
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Quick Actions:${NC}"
echo -e "${BLUE}========================================${NC}"
echo "  Start server:    ${GREEN}./scripts/start.sh${NC}"
echo "  Run tests:       ${GREEN}./scripts/test.sh${NC}"
echo "  Run linters:     ${GREEN}./scripts/lint.sh${NC}"
echo "  Reset env:       ${GREEN}./scripts/reset.sh${NC}"
echo ""
