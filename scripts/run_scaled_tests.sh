#!/bin/bash
# run_scaled_tests.sh
# Script to run larger-scale batch tests with optimized parameters

# Ensure we're in the correct directory
cd "$(dirname "$0")"

# Ensure required directories exist
mkdir -p data/test_results
mkdir -p data/batch_state

echo "==== URL Checker Large-Scale Batch Testing Tool ===="
echo "This script will run larger-scale batch tests to validate system readiness"
echo "for processing up to 130,000 URLs."
echo ""
echo "WARNING: This test will use significant system resources and may take hours to complete."
echo "Make sure your system has enough memory and CPU resources available."
echo ""
echo "The tests will primarily use mock API calls to save Firecrawl credits."
echo ""

# Confirm before proceeding
read -p "Are you sure you want to continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Test cancelled."
    exit 1
fi

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

# Prompt for optimal parameters from initial tests
echo ""
echo "Enter the optimal parameters determined from initial tests:"
read -p "MAX_URLS_PER_BATCH [500]: " batch_size
read -p "MAX_CONCURRENT_REQUESTS [20]: " concurrent_requests
read -p "USE_MOCK_PERCENTAGE [98]: " mock_percentage
read -p "DOMAIN_COOLDOWN_PERIOD [2.0]: " domain_cooldown

# Set defaults if not provided
batch_size=${batch_size:-500}
concurrent_requests=${concurrent_requests:-20}
mock_percentage=${mock_percentage:-98}
domain_cooldown=${domain_cooldown:-2.0}

# Set environment variables for testing
export USE_MOCK_PERCENTAGE=$mock_percentage
export FIRECRAWL_CREDITS_USED=603  # Starting credit usage
export MAX_URLS_PER_BATCH=$batch_size
export MAX_CONCURRENT_REQUESTS=$concurrent_requests
export DOMAIN_COOLDOWN_PERIOD=$domain_cooldown
export MEMORY_CHECKPOINT_INTERVAL=1000  # Memory checkpoints every 1000 URLs
export GC_THRESHOLD=75.0  # Standard garbage collection threshold

# Generate a test run ID
RUN_ID="scaled_test_$(date +%Y%m%d_%H%M%S)"
echo "Test run ID: $RUN_ID"
echo ""
echo "Using the following parameters:"
echo "- MAX_URLS_PER_BATCH: $batch_size"
echo "- MAX_CONCURRENT_REQUESTS: $concurrent_requests"
echo "- USE_MOCK_PERCENTAGE: $mock_percentage%"
echo "- DOMAIN_COOLDOWN_PERIOD: $domain_cooldown seconds"
echo ""

# Run medium-size test first 
echo "--- Running medium-scale test (5,000 URLs) ---"
python -m app.test_batch_scaling --sizes 5000 --run-id "${RUN_ID}_medium"

# Wait a moment
echo "Waiting for 10 seconds before proceeding to large-scale test..."
sleep 10

# Run large-scale test
echo ""
echo "--- Running large-scale test (25,000 and 50,000 URLs) ---"
python -m app.test_batch_scaling --sizes 25000 50000 --run-id "${RUN_ID}_large"

# Wait and confirm before running the final test
echo ""
echo "Medium and large-scale tests completed. Review the results before proceeding to the final test."
echo "Results are available in data/test_results/batch_test_results_${RUN_ID}_*.json"
echo ""
read -p "Proceed with final 100,000 URL test? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Final test cancelled."
else
    # Final largest test
    echo ""
    echo "--- Running final large-scale test (100,000 URLs) ---"
    echo "This test may take several hours to complete."
    echo "Consider running this test overnight or during off-hours."
    echo ""
    read -p "Still want to proceed? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Final test cancelled."
    else
        python -m app.test_batch_scaling --sizes 100000 --run-id "${RUN_ID}_final"
    fi
fi

# Display test results summary
echo ""
echo "--- Test Results Summary ---"
echo "All test results are saved in data/test_results/"
echo "Log file: data/batch_scaling_test.log"

# Parse and show the last few lines of the log
echo ""
echo "Recent log entries:"
tail -n 20 data/batch_scaling_test.log

# Output next steps
echo ""
echo "--- Next Steps ---"
echo "Based on these test results, you can now:"
echo "1. Update the production .env file with optimal parameters"
echo "2. Prepare for the full 130,000 URL test"
echo "3. Review error patterns and optimize error handling"
echo ""
echo "To analyze detailed test results, check the JSON files in data/test_results/"
echo ""
echo "For memory usage analysis, check the memory checkpoints in the result files"
echo ""

# Deactivate virtual environment
deactivate

echo "Testing completed" 