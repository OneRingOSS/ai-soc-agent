#!/bin/bash
# Run the SOC Agent backend with logging to file for Promtail
#
# Usage:
#   ./run_with_logging.sh              # Run in MOCK mode (default, fast, no API costs)
#   LIVE_API=1 ./run_with_logging.sh   # Run in LIVE mode (uses OpenAI API)

# Navigate to the backend src directory
cd "$(dirname "$0")/src"

# Activate virtual environment
source ../venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p ../../observability/logs

# Determine mode: MOCK (default) or LIVE (if LIVE_API=1)
if [ "$LIVE_API" = "1" ]; then
  echo "🔴 Starting backend in LIVE API mode..."
  python main.py 2>&1 | tee ../../observability/logs/soc-agent.log
else
  echo "⚡ Starting backend in MOCK mode (FORCE_MOCK_MODE=1)..."
  FORCE_MOCK_MODE=1 python main.py 2>&1 | tee ../../observability/logs/soc-agent.log
fi

