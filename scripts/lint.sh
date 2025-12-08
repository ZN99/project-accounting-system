#!/bin/bash
# lint.sh - Run linters and code quality checks
# Checks Python code style and quality

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Running Code Quality Checks...${NC}"
echo ""

# Check if we're in the project root
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: manage.py not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Track overall status
OVERALL_STATUS=0

# Check Django code quality
echo -e "${BLUE}Checking Django project configuration...${NC}"
python manage.py check
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Django check passed${NC}"
else
    echo -e "${RED}✗ Django check failed${NC}"
    OVERALL_STATUS=1
fi
echo ""

# Check for flake8
if command -v flake8 &> /dev/null; then
    echo -e "${BLUE}Running flake8 (Python style checker)...${NC}"
    flake8 order_management subcontract_management construction_dispatch --max-line-length=120 --exclude=migrations,__pycache__,venv,env
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Flake8 passed${NC}"
    else
        echo -e "${YELLOW}⚠ Flake8 found issues${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠ Flake8 not installed (pip install flake8)${NC}"
fi
echo ""

# Check for pylint
if command -v pylint &> /dev/null; then
    echo -e "${BLUE}Running pylint (code analysis)...${NC}"
    pylint order_management subcontract_management --disable=C,R --ignore=migrations
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Pylint passed${NC}"
    else
        echo -e "${YELLOW}⚠ Pylint found issues${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠ Pylint not installed (pip install pylint)${NC}"
fi
echo ""

# Check for black (code formatter)
if command -v black &> /dev/null; then
    echo -e "${BLUE}Checking code formatting with black...${NC}"
    black --check order_management subcontract_management construction_dispatch --exclude='/(migrations|venv|env|\.git)/'
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Code formatting is correct${NC}"
    else
        echo -e "${YELLOW}⚠ Code needs formatting. Run: black .${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠ Black not installed (pip install black)${NC}"
fi
echo ""

# Check for isort (import sorting)
if command -v isort &> /dev/null; then
    echo -e "${BLUE}Checking import sorting with isort...${NC}"
    isort --check-only order_management subcontract_management construction_dispatch --skip migrations --skip venv --skip env
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Import sorting is correct${NC}"
    else
        echo -e "${YELLOW}⚠ Imports need sorting. Run: isort .${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠ Isort not installed (pip install isort)${NC}"
fi
echo ""

# Check for security issues with bandit
if command -v bandit &> /dev/null; then
    echo -e "${BLUE}Running security checks with bandit...${NC}"
    bandit -r order_management subcontract_management construction_dispatch -x "*/migrations/*,*/tests/*" --quiet
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Security checks passed${NC}"
    else
        echo -e "${YELLOW}⚠ Security issues found${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠ Bandit not installed (pip install bandit)${NC}"
fi
echo ""

# Check for unused imports with autoflake
if command -v autoflake &> /dev/null; then
    echo -e "${BLUE}Checking for unused imports...${NC}"
    autoflake --check --recursive order_management subcontract_management construction_dispatch --exclude=migrations,__pycache__,venv,env
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ No unused imports found${NC}"
    else
        echo -e "${YELLOW}⚠ Unused imports found. Run: autoflake --in-place --recursive .${NC}"
        OVERALL_STATUS=1
    fi
else
    echo -e "${YELLOW}⚠ Autoflake not installed (pip install autoflake)${NC}"
fi
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ All code quality checks passed!${NC}"
    echo -e "${BLUE}========================================${NC}"
else
    echo -e "${YELLOW}⚠ Some checks found issues${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${BLUE}To install missing linters:${NC}"
    echo "  pip install flake8 pylint black isort bandit autoflake"
    echo ""
    echo -e "${BLUE}To auto-fix some issues:${NC}"
    echo "  black .                    # Format code"
    echo "  isort .                    # Sort imports"
    echo "  autoflake --in-place -r .  # Remove unused imports"
fi

exit $OVERALL_STATUS
