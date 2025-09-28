# URL Checker Testing Guide

This guide explains how to run the incremental batch tests to validate the URL Checker system's performance and readiness for processing large volumes of URLs.

## Prerequisites

- Python 3.11+
- Git repository cloned
- Sufficient system resources (at least 8GB RAM recommended)
- Approximately 1,000 Firecrawl credits available (most tests use mock mode)

## Testing Process Overview

The testing process is divided into two phases:

1. **Initial Testing (Small Batches)**: Test with small batches (100-2000 URLs) to validate the system's functionality and establish baseline performance metrics.

2. **Scaled Testing (Larger Batches)**: Test with progressively larger batches (5,000-100,000 URLs) to identify scaling issues and determine optimal configuration settings.

## Running the Tests

### Step 1: Initial Testing

Run the initial tests to validate the system's functionality and gather baseline performance data:

```bash
./run_initial_tests.sh
```

This script will:
- Set up the Python virtual environment if needed
- Configure testing parameters to conserve Firecrawl credits (95% mock mode)
- Run tests with batch sizes of 100, 500, 1000, and 2000 URLs
- Generate performance metrics and recommendations

### Step 2: Review Initial Results

After the initial tests complete:
1. Review the log file: `data/batch_scaling_test.log`
2. Examine the detailed test results in `data/test_results/`
3. Note the recommended batch size and concurrency settings

### Step 3: Scaled Testing

Run the larger-scale tests using the optimized parameters from initial testing:

```bash
./run_scaled_tests.sh
```

When prompted:
- Enter the optimal parameters determined from initial tests
- Confirm at each step before proceeding to larger tests
- Consider running the largest tests during off-hours

### Step 4: Review Final Results

After the scaled tests complete:
1. Analyze the detailed performance metrics in `data/test_results/`
2. Review error patterns and categories
3. Determine the optimal configuration for production use

## Test Results Analysis

The test results JSON files contain detailed metrics, including:

- Processing speed (URLs per second)
- Memory usage patterns
- Error rates and categories
- Domain-specific performance
- Firecrawl API usage statistics

### Key Metrics to Review

- **URLs per second**: Throughput of the system
- **Memory usage**: Both peak and per-URL memory consumption
- **Error rate**: Percentage of failed URLs
- **Resource utilization**: CPU and memory patterns during processing
- **Domain distribution**: Performance across different domains

## Configuring for Production

Based on test results, update your `.env` file with the optimal settings:

```
# Batch Processing Settings
MAX_URLS_PER_BATCH=500           # Adjust based on test results
MAX_CONCURRENT_REQUESTS=20        # Adjust based on test results
MAX_REQUESTS_PER_DOMAIN=2        # Adjust if domain-specific errors are high
DOMAIN_COOLDOWN_PERIOD=2.0       # Adjust based on rate limiting patterns
MAX_CPU_PERCENT=80.0             # Recommended threshold
MAX_MEMORY_PERCENT=80.0          # Recommended threshold
MEMORY_CHECKPOINT_INTERVAL=1000  # Frequency of memory optimization
GC_THRESHOLD=75.0                # When to trigger garbage collection
```

## Troubleshooting

If you encounter issues during testing:

- **Memory errors**: Reduce batch size and concurrent requests
- **High error rates**: Check error categories to identify patterns
- **Slow processing**: Examine domain distribution and rate limiting
- **Firecrawl errors**: Check credit usage and adjust mock percentage

## Final Testing for 130,000 URLs

After validating with 100,000 URLs, you can proceed to the final 130,000 URL test:

```bash
# Edit the maximum test size in app/test_batch_scaling.py
# Line: DEFAULT_TEST_SIZES = [100, 1000, 10000, 50000, 100000, 130000]

# Run with specific size
python -m app.test_batch_scaling --sizes 130000 --run-id "final_test"
```

This final test should be run only after all optimizations are in place and the system has been thoroughly validated with smaller batches. 