#!/bin/bash
# Sealed Secrets Setup for P1.1 (Open Source - Zero Vendor Lock-in)
# Reference: https://github.com/bitnami-labs/sealed-secrets

set -e

echo "=== Sealed Secrets Setup for SOC Agent ==="
echo ""

# Step 1: Install Sealed Secrets controller
echo "[1/5] Installing Sealed Secrets controller in cluster..."
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.26.0/controller.yaml
# Creates namespace: kube-system
# Creates controller deployment: sealed-secrets-controller

echo "Waiting for controller to be ready..."
kubectl wait --for=condition=available --timeout=120s deployment/sealed-secrets-controller -n kube-system
echo "✅ Controller ready"
echo ""

# Step 2: Install kubeseal CLI
echo "[2/5] Installing kubeseal CLI..."
if command -v kubeseal &> /dev/null; then
    echo "kubeseal already installed: $(kubeseal --version)"
else
    echo "Installing kubeseal..."
    # macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install kubeseal
    # Linux
    else
        wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.26.0/kubeseal-0.26.0-linux-amd64.tar.gz
        tar -xvzf kubeseal-0.26.0-linux-amd64.tar.gz
        sudo install -m 755 kubeseal /usr/local/bin/kubeseal
    fi
fi
echo "✅ kubeseal installed"
echo ""

# Step 3: Fetch public key (for encrypting secrets)
echo "[3/5] Fetching public key from controller..."
kubeseal --fetch-cert > sealed-secrets-public-key.pem
echo "✅ Public key saved to: sealed-secrets-public-key.pem"
echo "   (Safe to commit to Git - this is the PUBLIC key only)"
echo ""

# Step 4: Create example SealedSecret for redis-auth-secret
echo "[4/5] Creating SealedSecret for REDIS_PASSWORD..."

# Generate a strong Redis password
REDIS_PASSWORD=$(head -c 32 /dev/urandom | base64 | tr -d '\n')

# Create regular Secret manifest (don't apply it!)
cat > /tmp/redis-secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: redis-auth-secret
  namespace: default
type: Opaque
stringData:
  REDIS_PASSWORD: ${REDIS_PASSWORD}
EOF

# Seal the secret (encrypt it)
kubeseal --format=yaml --cert=sealed-secrets-public-key.pem \
  < /tmp/redis-secret.yaml \
  > sealed-redis-secret.yaml

rm /tmp/redis-secret.yaml  # Delete plaintext version

echo "✅ SealedSecret created: sealed-redis-secret.yaml"
echo "   (This file is ENCRYPTED and safe to commit to Git)"
echo ""

# Step 5: Apply SealedSecret to cluster
echo "[5/5] Applying SealedSecret to cluster..."
kubectl apply -f sealed-redis-secret.yaml

# Wait for controller to decrypt it
sleep 3

# Verify regular Secret was created
if kubectl get secret redis-auth-secret -n default &> /dev/null; then
    echo "✅ Secret redis-auth-secret created successfully by controller"
    echo ""
    echo "Verify decryption:"
    echo "  kubectl get secret redis-auth-secret -o jsonpath='{.data.REDIS_PASSWORD}' | base64 -d"
else
    echo "❌ Secret not created - check controller logs"
    kubectl logs -n kube-system deployment/sealed-secrets-controller
    exit 1
fi

echo ""
echo "=== Sealed Secrets Setup Complete! ==="
echo ""
echo "Next steps:"
echo "  1. Commit sealed-secrets-public-key.pem and sealed-redis-secret.yaml to Git"
echo "  2. Share public key with team (safe to distribute)"
echo "  3. Team members can create SealedSecrets with:"
echo "     kubeseal --cert=sealed-secrets-public-key.pem < secret.yaml > sealed-secret.yaml"
echo ""
echo "Key rotation (every 30 days recommended):"
echo "  1. Controller auto-generates new key pair"
echo "  2. Fetch new public key: kubeseal --fetch-cert > sealed-secrets-public-key.pem"
echo "  3. Re-seal all secrets with new key"
echo ""
echo "Backup (CRITICAL - store private key securely):"
echo "  kubectl get secret -n kube-system sealed-secrets-key -o yaml > sealed-secrets-private-key-BACKUP.yaml"
echo "  # Store in password manager, NOT in Git!"
