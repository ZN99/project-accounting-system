#!/bin/bash
# test.sh - Run test suite for Construction Dispatch System
# Supports running all tests or specific app/module tests

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Running Test Suite...${NC}"
echo ""

# Check if we're in the project root
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: manage.py not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Parse arguments
TEST_TARGET="${1:-all}"
VERBOSITY="${2:-2}"

case "$TEST_TARGET" in
    "all")
        echo -e "${BLUE}Running all tests...${NC}"
        python manage.py test --verbosity=$VERBOSITY
        ;;
    "order")
        echo -e "${BLUE}Running order_management tests...${NC}"
        python manage.py test order_management --verbosity=$VERBOSITY
        ;;
    "subcontract")
        echo -e "${BLUE}Running subcontract_management tests...${NC}"
        python manage.py test subcontract_management --verbosity=$VERBOSITY
        ;;
    "quick")
        echo -e "${BLUE}Running quick test (verbosity 1)...${NC}"
        python manage.py test --verbosity=1
        ;;
    "coverage")
        echo -e "${BLUE}Running tests with coverage...${NC}"
        if command -v coverage &> /dev/null; then
            coverage run --source='.' manage.py test --verbosity=$VERBOSITY
            coverage report
            coverage html
            echo -e "${GREEN}✓ Coverage report generated in htmlcov/index.html${NC}"
        else
            echo -e "${YELLOW}⚠ Coverage not installed. Install with: pip install coverage${NC}"
            echo -e "${BLUE}Running tests without coverage...${NC}"
            python manage.py test --verbosity=$VERBOSITY
        fi
        ;;
    *)
        # Custom test path provided
        echo -e "${BLUE}Running specific test: $TEST_TARGET${NC}"
        python manage.py test $TEST_TARGET --verbosity=$VERBOSITY
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Some tests failed${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

# Show usage if no arguments
if [ "$TEST_TARGET" = "all" ] && [ $# -eq 0 ]; then
    echo ""
    echo -e "${BLUE}Usage examples:${NC}"
    echo "  ./scripts/test.sh                          # Run all tests"
    echo "  ./scripts/test.sh order                    # Run order_management tests"
    echo "  ./scripts/test.sh subcontract              # Run subcontract_management tests"
    echo "  ./scripts/test.sh quick                    # Quick run (verbosity 1)"
    echo "  ./scripts/test.sh coverage                 # Run with coverage report"
    echo "  ./scripts/test.sh order_management.tests.TestProjectModel  # Specific test"
fi
