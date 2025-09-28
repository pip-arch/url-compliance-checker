#!/bin/bash
# run_initial_tests.sh
# Script to run incremental batch tests to validate system performance and optimizations

# Ensure we're in the correct directory
cd "$(dirname "$0")"

# Ensure required directories exist
mkdir -p data/test_results
mkdir -p data/batch_state

echo "==== URL Checker Batch Testing Tool ===="
echo "This script will run incremental batch tests to validate system performance"
echo "before proceeding to full-scale testing with 130,000 URLs."
echo ""
echo "The tests will use a combination of real and mock API calls to save Firecrawl credits."
echo ""

# Setup the Python virtual environment
if [ ! -d "venv" ]; then
    echo "Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "Activating existing virtual environment..."
    source venv/bin/activate
fi

# Set environment variables for testing
export USE_MOCK_PERCENTAGE=95  # Use 95% mock calls for testing
export FIRECRAWL_CREDITS_USED=603  # Starting credit usage
export MAX_URLS_PER_BATCH=100  # Start with small batches
export MAX_CONCURRENT_REQUESTS=10  # Start with modest concurrency
export MEMORY_CHECKPOINT_INTERVAL=500  # Perform memory checkpoints frequently during testing
export GC_THRESHOLD=70.0  # More aggressive garbage collection during testing

# Generate a test run ID
RUN_ID="initial_test_$(date +%Y%m%d_%H%M%S)"
echo "Test run ID: $RUN_ID"

# Small test first to ensure everything is working
echo ""
echo "--- Running initial small test (100 URLs) ---"
python -m app.test_batch_scaling --sizes 100 --run-id "${RUN_ID}_small"

# Wait a moment
echo "Waiting for 5 seconds before proceeding to incremental tests..."
sleep 5

# Run incremental tests with modest sizes to validate optimizations
echo ""
echo "--- Running incremental batch tests (500, 1000, 2000) ---"
python -m app.test_batch_scaling --sizes 500 1000 2000 --run-id "${RUN_ID}_incremental"

# Display test results summary
echo ""
echo "--- Test Results Summary ---"
echo "Test results are saved in data/test_results/"
echo "Log file: data/batch_scaling_test.log"

# Parse and show the last few lines of the log
echo ""
echo "Recent log entries:"
tail -n 20 data/batch_scaling_test.log

# Output recommendations
echo ""
echo "--- Recommendations for next steps ---"
echo "Based on the initial test results, adjust the following parameters in .env:"
echo "1. MAX_URLS_PER_BATCH - Optimal batch size for processing"
echo "2. MAX_CONCURRENT_REQUESTS - Optimal concurrent requests"
echo "3. DOMAIN_COOLDOWN_PERIOD - Adjust based on error rates"
echo "4. MEMORY_CHECKPOINT_INTERVAL - Frequency of memory checkpoints"
echo ""
echo "After updating these parameters, run the larger scaled tests with:"
echo "./run_scaled_tests.sh"
echo ""
echo "For a detailed analysis of test results, check the JSON files in data/test_results/"
echo ""

# Deactivate virtual environment
deactivate

echo "Testing completed" 