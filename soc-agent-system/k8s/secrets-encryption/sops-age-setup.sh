#!/bin/bash
# Mozilla SOPS with age encryption setup (Open Source - Zero Lock-in)
# Reference: https://github.com/getsops/sops

set -e

echo "=== SOPS + age Encryption Setup for SOC Agent ==="
echo ""

# Step 1: Install age (encryption tool)
echo "[1/4] Installing age encryption tool..."
if command -v age &> /dev/null; then
    echo "age already installed: $(age --version 2>&1 | head -1)"
else
    # macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install age
    # Linux
    else
        wget https://github.com/FiloSottile/age/releases/download/v1.1.1/age-v1.1.1-linux-amd64.tar.gz
        tar -xvzf age-v1.1.1-linux-amd64.tar.gz
        sudo mv age/age /usr/local/bin/
        sudo mv age/age-keygen /usr/local/bin/
    fi
fi
echo "✅ age installed"
echo ""

# Step 2: Install SOPS
echo "[2/4] Installing SOPS..."
if command -v sops &> /dev/null; then
    echo "sops already installed: $(sops --version 2>&1 | head -1)"
else
    # macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install sops
    # Linux
    else
        wget https://github.com/getsops/sops/releases/download/v3.8.1/sops-v3.8.1.linux.amd64
        sudo mv sops-v3.8.1.linux.amd64 /usr/local/bin/sops
        sudo chmod +x /usr/local/bin/sops
    fi
fi
echo "✅ sops installed"
echo ""

# Step 3: Generate age key pair
echo "[3/4] Generating age encryption key pair..."
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt

echo "✅ Age key pair generated"
echo "   Private key: ~/.config/sops/age/keys.txt"
echo "   ⚠️  CRITICAL: Backup this file securely (password manager, NOT Git)"
echo ""

# Extract public key
AGE_PUBLIC_KEY=$(grep "# public key:" ~/.config/sops/age/keys.txt | cut -d ' ' -f 4)
echo "Public key: $AGE_PUBLIC_KEY"
echo "$AGE_PUBLIC_KEY" > .sops-age-public-key.txt
echo "   Saved to: .sops-age-public-key.txt (safe to commit to Git)"
echo ""

# Step 4: Create encrypted Secret for Redis
echo "[4/4] Creating SOPS-encrypted Secret for REDIS_PASSWORD..."

# Generate strong Redis password
REDIS_PASSWORD=$(head -c 32 /dev/urandom | base64 | tr -d '\n')

# Create plaintext Secret
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

# Encrypt with SOPS
sops --encrypt \
  --age "$AGE_PUBLIC_KEY" \
  --encrypted-regex '^(data|stringData)$' \
  /tmp/redis-secret.yaml > redis-secret.enc.yaml

rm /tmp/redis-secret.yaml  # Delete plaintext

echo "✅ Encrypted Secret created: redis-secret.enc.yaml"
echo "   (This file is ENCRYPTED and safe to commit to Git)"
echo ""

echo "=== SOPS + age Setup Complete! ==="
echo ""
echo "Usage:"
echo "  1. View encrypted file:"
echo "     cat redis-secret.enc.yaml"
echo ""
echo "  2. Edit encrypted file (decrypts in editor, re-encrypts on save):"
echo "     sops redis-secret.enc.yaml"
echo ""
echo "  3. Apply to cluster (decrypt on-the-fly):"
echo "     sops --decrypt redis-secret.enc.yaml | kubectl apply -f -"
echo ""
echo "  4. Commit encrypted file to Git:"
echo "     git add redis-secret.enc.yaml .sops-age-public-key.txt"
echo "     git commit -m 'Add encrypted Redis secret'"
echo ""
echo "Team setup:"
echo "  1. Share public key file: .sops-age-public-key.txt"
echo "  2. Team members add to .sops.yaml:"
echo "     creation_rules:"
echo "       - age: $AGE_PUBLIC_KEY"
echo ""
echo "CI/CD setup:"
echo "  1. Store private key as GitHub Secret: SOPS_AGE_KEY"
echo "  2. In workflow:"
echo "     - run: echo \"\${{ secrets.SOPS_AGE_KEY }}\" > /tmp/age-key.txt"
echo "     - run: export SOPS_AGE_KEY_FILE=/tmp/age-key.txt"
echo "     - run: sops --decrypt redis-secret.enc.yaml | kubectl apply -f -"
