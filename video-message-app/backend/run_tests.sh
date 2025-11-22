#!/bin/bash
# Test Runner Script for Video Message App
# Author: Hestia (Security Guardian) + Artemis (Technical Perfectionist)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Video Message App - Test Suite"
echo "========================================="
echo ""

# Parse arguments
TEST_TYPE=${1:-all}
COVERAGE=${2:-false}

# Test functions
run_unit_tests() {
    echo -e "${GREEN}Running Unit Tests...${NC}"
    if [ "$COVERAGE" = "true" ]; then
        pytest tests/ -m "unit" -v --cov=services --cov-report=term --cov-report=html
    else
        pytest tests/ -m "unit" -v
    fi
}

run_integration_tests() {
    echo -e "${GREEN}Running Integration Tests...${NC}"
    pytest tests/integration/ -v
}

run_e2e_tests() {
    echo -e "${GREEN}Running E2E Tests (Fast)...${NC}"
    pytest tests/e2e/ -m "e2e and not slow" -v
}

run_e2e_slow_tests() {
    echo -e "${YELLOW}Running E2E Tests (Slow - may take several minutes)...${NC}"
    pytest tests/e2e/ -m "e2e and slow" -v --tb=short
}

run_security_tests() {
    echo -e "${GREEN}Running Security Tests...${NC}"
    pytest tests/e2e/test_security.py -m "security" -v
}

run_performance_tests() {
    echo -e "${GREEN}Running Performance Tests...${NC}"
    pytest tests/ -m "benchmark or performance" -v --tb=short
}

run_smoke_tests() {
    echo -e "${GREEN}Running Smoke Tests (Quick Validation)...${NC}"
    pytest tests/ -m "smoke" -v --tb=short -x
}

run_all_tests() {
    echo -e "${GREEN}Running All Tests (Except Slow)...${NC}"
    if [ "$COVERAGE" = "true" ]; then
        pytest tests/ -m "not slow" -v --cov=services --cov-report=term --cov-report=html
    else
        pytest tests/ -m "not slow" -v
    fi
}

run_all_tests_including_slow() {
    echo -e "${YELLOW}Running ALL Tests (Including Slow - this will take a while)...${NC}"
    if [ "$COVERAGE" = "true" ]; then
        pytest tests/ -v --cov=services --cov-report=term --cov-report=html
    else
        pytest tests/ -v
    fi
}

# Main test execution
case $TEST_TYPE in
    unit)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    e2e)
        run_e2e_tests
        ;;
    e2e-slow)
        run_e2e_slow_tests
        ;;
    security)
        run_security_tests
        ;;
    performance)
        run_performance_tests
        ;;
    smoke)
        run_smoke_tests
        ;;
    all)
        run_all_tests
        ;;
    full)
        run_all_tests_including_slow
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: ./run_tests.sh [test_type] [coverage]"
        echo ""
        echo "Test Types:"
        echo "  unit         - Unit tests only"
        echo "  integration  - Integration tests"
        echo "  e2e          - E2E tests (fast)"
        echo "  e2e-slow     - E2E tests (slow)"
        echo "  security     - Security tests"
        echo "  performance  - Performance/benchmark tests"
        echo "  smoke        - Smoke tests (quick validation)"
        echo "  all          - All tests (except slow)"
        echo "  full         - ALL tests (including slow)"
        echo ""
        echo "Coverage:"
        echo "  true         - Generate coverage report"
        echo "  false        - No coverage (default)"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh unit"
        echo "  ./run_tests.sh all true"
        echo "  ./run_tests.sh security"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Tests completed!${NC}"

if [ "$COVERAGE" = "true" ]; then
    echo ""
    echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
fi
