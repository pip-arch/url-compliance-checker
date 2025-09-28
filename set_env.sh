#!/bin/bash
# Set the OpenAI API key
export OPENAI_API_KEY="sk-YOUR-API-KEY-HERE"
export FORCE_OPENAI=1
export FORCE_ANALYSIS=1

# Run the original script
PYTHONPATH=. python scripts/run_improved_process.py --file test_urls.csv --column URL --limit 1 