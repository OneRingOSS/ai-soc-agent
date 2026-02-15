#!/bin/bash
# Run the SOC Agent backend with logging to file for Promtail

# Navigate to the backend src directory
cd "$(dirname "$0")/src"

# Activate virtual environment
source ../venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p ../../observability/logs

# Run the backend and tee output to both console and log file
python main.py 2>&1 | tee ../../observability/logs/soc-agent.log

