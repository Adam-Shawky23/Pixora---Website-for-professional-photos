#!/bin/bash
# Quick test runner for k29photo
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  k29photo Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}[!] pytest not found. Installing test dependencies...${NC}"
    pip install -q pytest pytest-cov pytest-flask
    echo -e "${GREEN}[✓] Dependencies installed${NC}"
    echo ""
fi

# Run tests based on argument
case "${1:-all}" in
    all)
        echo -e "${BLUE}[*] Running all tests...${NC}"
        pytest tests/ -v --tb=short
        ;;
    security)
        echo -e "${BLUE}[*] Running security tests...${NC}"
        pytest tests/test_security.py -v --tb=short -m "security"
        ;;
    auth)
        echo -e "${BLUE}[*] Running authentication tests...${NC}"
        pytest tests/test_auth.py -v --tb=short -m "auth"
        ;;
    unit)
        echo -e "${BLUE}[*] Running unit tests...${NC}"
        pytest tests/ -v --tb=short -m "unit"
        ;;
    coverage)
        echo -e "${BLUE}[*] Running tests with coverage report...${NC}"
        pytest tests/ --cov=k29photo --cov-report=html --cov-report=term-missing -v
        echo -e "${GREEN}[✓] Coverage report generated: htmlcov/index.html${NC}"
        ;;
    quick)
        echo -e "${BLUE}[*] Running quick tests (no slow tests)...${NC}"
        pytest tests/ -v -m "not slow" --tb=short -x
        ;;
    watch)
        echo -e "${BLUE}[*] Watching for changes...${NC}"
        pytest-watch tests/
        ;;
    lint)
        echo -e "${BLUE}[*] Running linters...${NC}"
        echo -e "${YELLOW}  - flake8${NC}"
        flake8 k29photo --count --exit-zero --max-line-length=127
        echo -e "${GREEN}[✓] Linting complete${NC}"
        ;;
    *)
        echo "Usage: $0 [all|security|auth|unit|coverage|quick|watch|lint]"
        echo ""
        echo "Options:"
        echo "  all       - Run all tests (default)"
        echo "  security  - Run security tests only"
        echo "  auth      - Run authentication tests only"
        echo "  unit      - Run unit tests only"
        echo "  coverage  - Run tests with coverage report"
        echo "  quick     - Run quick tests (exclude slow)"
        echo "  watch     - Watch for changes and rerun tests"
        echo "  lint      - Run linters (flake8)"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Done${NC}"
echo -e "${GREEN}========================================${NC}"
