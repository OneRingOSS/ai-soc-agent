#!/bin/bash

# Test wrapper for generate_threat_with_openai.sh
# This automatically answers "yes" to the confirmation prompt

set -e

cd "$(dirname "$0")"

echo "Testing OpenAI Live Demo Script..."
echo ""

# Run the script and automatically answer "yes"
echo "yes" | ./generate_threat_with_openai.sh

echo ""
echo "Test complete!"

