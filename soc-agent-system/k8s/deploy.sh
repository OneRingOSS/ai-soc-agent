#!/bin/bash
set -e

echo "=== SOC Agent System — Kubernetes Deployment ==="
echo ""

# -------------------------------------------------------
# Step 1: Check prerequisites
# -------------------------------------------------------
echo "Step 1: Checking prerequisites..."

MISSING=""
for cmd in kind kubectl helm docker; do
  if ! command -v "$cmd" &> /dev/null; then
    MISSING="$MISSING $cmd"
  fi
done

if [ -n "$MISSING" ]; then
  echo "❌ Missing required tools:$MISSING"
  echo "Please install them before running this script."
  exit 1
fi

echo "  kind:    $(kind version)"
echo "  kubectl: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
echo "  helm:    $(helm version --short)"
echo "  docker:  $(docker version --format '{{.Client.Version}}')"
echo "✅ All prerequisites met"
echo ""

# -------------------------------------------------------
# Step 2: Create Kind cluster
# -------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Step 2: Creating Kind cluster..."
if kind get clusters 2>/dev/null | grep -q "^soc-demo$"; then
  echo "  Cluster 'soc-demo' already exists, deleting..."
  kind delete cluster --name soc-demo
fi
kind create cluster --config kind-config.yaml --name soc-demo
echo "  Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=60s
echo "✅ Kind cluster 'soc-demo' created"
echo ""

# -------------------------------------------------------
# Step 3: Build and load Docker images
# -------------------------------------------------------
echo "Step 3: Building and loading Docker images..."
PROJECT_ROOT="$SCRIPT_DIR/../.."
cd "$PROJECT_ROOT"

echo "  Building soc-backend:latest..."
docker build -t soc-backend:latest -f backend/Dockerfile backend/

echo "  Building soc-frontend:latest..."
docker build -t soc-frontend:latest -f frontend/Dockerfile frontend/

echo "  Loading images into Kind cluster..."
kind load docker-image soc-backend:latest --name soc-demo
kind load docker-image soc-frontend:latest --name soc-demo
echo "✅ Images loaded into Kind cluster"
echo ""

# -------------------------------------------------------
# Step 4: Install nginx ingress controller
# -------------------------------------------------------
cd "$SCRIPT_DIR"
echo "Step 4: Installing nginx ingress controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
echo "  Waiting for ingress controller to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
echo "✅ Nginx ingress controller ready"
echo ""

# -------------------------------------------------------
# Step 5: Install SOC Agent System via Helm
# -------------------------------------------------------
echo "Step 5: Installing SOC Agent System..."
helm install soc-agent ./charts/soc-agent --wait --timeout 5m
echo "✅ SOC Agent System deployed"
echo ""

# -------------------------------------------------------
# Step 6: Verify deployment
# -------------------------------------------------------
echo "Step 6: Verifying deployment..."
echo ""
echo "Backend pods:"
kubectl get pods -l app=soc-backend
echo ""
echo "Redis pods:"
kubectl get pods -l app=redis
echo ""
echo "HPA status:"
kubectl get hpa
echo ""
echo "Ingress:"
kubectl get ingress
echo ""
echo "Waiting for backend pods to be ready..."
kubectl wait --for=condition=ready pod -l app=soc-backend --timeout=120s
echo "✅ All backend pods ready"
echo ""

# -------------------------------------------------------
# Step 7: Print access instructions
# -------------------------------------------------------
echo "=== Deployment Complete ==="
echo ""
echo "SOC Dashboard: http://localhost:8080"
echo "Backend API:   http://localhost:8080/api/threats"
echo "Health Check:  curl http://localhost:8080/health"
echo ""
echo "Backend Pods: $(kubectl get pods -l app=soc-backend --no-headers | wc -l)"
echo "Redis Status: $(kubectl get pods -l app=redis --no-headers)"
echo ""
echo "To view logs:  kubectl logs -l app=soc-backend --tail=50 -f"
echo "To check HPA:  kubectl get hpa -w"
echo "To teardown:   ./teardown.sh"

