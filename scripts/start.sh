#!/bin/bash
# start.sh - Start the Django development server
# Gracefully handles existing servers and provides clear status

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default port
PORT="${1:-8000}"

echo -e "${BLUE}🚀 Starting Construction Dispatch System...${NC}"
echo ""

# Check if we're in the project root
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: manage.py not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Port $PORT is already in use${NC}"
    echo -e "${BLUE}Killing existing server on port $PORT...${NC}"
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}✓ Existing server stopped${NC}"
    echo ""
fi

# Collect static files (quick check)
echo -e "${BLUE}Checking static files...${NC}"
python manage.py collectstatic --no-input --clear > /dev/null 2>&1 || true
echo -e "${GREEN}✓ Static files ready${NC}"
echo ""

# Check for pending migrations
echo -e "${BLUE}Checking for pending migrations...${NC}"
PENDING_MIGRATIONS=$(python manage.py showmigrations --plan | grep -c "\[ \]" || true)
if [ "$PENDING_MIGRATIONS" -gt 0 ]; then
    echo -e "${YELLOW}⚠ Found $PENDING_MIGRATIONS pending migration(s)${NC}"
    echo -e "${YELLOW}Do you want to apply them now? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        python manage.py migrate
        echo -e "${GREEN}✓ Migrations applied${NC}"
    else
        echo -e "${YELLOW}⚠ Continuing without applying migrations${NC}"
    fi
else
    echo -e "${GREEN}✓ No pending migrations${NC}"
fi
echo ""

# Start the server
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting Django server on port $PORT...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo "  • Dashboard:  ${GREEN}http://localhost:$PORT/orders/dashboard/${NC}"
echo "  • Login:      ${GREEN}http://localhost:$PORT/orders/login/${NC}"
echo "  • Admin:      ${GREEN}http://localhost:$PORT/admin/${NC}"
echo "  • Project List: ${GREEN}http://localhost:$PORT/orders/list/${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start server
python manage.py runserver $PORT
