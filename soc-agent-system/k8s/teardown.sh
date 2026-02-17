#!/bin/bash
set -e

echo "=== Tearing down SOC Agent System ==="
echo ""

if ! command -v kind &> /dev/null; then
  echo "❌ 'kind' is not installed. Cannot tear down cluster."
  exit 1
fi

if kind get clusters 2>/dev/null | grep -q "^soc-demo$"; then
  echo "Deleting Kind cluster 'soc-demo'..."
  kind delete cluster --name soc-demo
  echo "✅ Cluster deleted"
else
  echo "⚠️  Cluster 'soc-demo' not found. Nothing to delete."
fi

echo ""
echo "Note: Docker images remain cached. Run the following to remove them:"
echo "  docker rmi soc-backend:latest soc-frontend:latest"

