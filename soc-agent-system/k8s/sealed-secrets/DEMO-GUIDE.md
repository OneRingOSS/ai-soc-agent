# Sealed Secrets Demo Guide

## ✅ Quick Demo Script (60 seconds)

### Step 1: Show Controller Running

```bash
kubectl get pods -n kube-system | grep sealed-secrets
```

**Expected output:**
```
sealed-secrets-controller-xxx   1/1     Running   0   5m
```

---

### Step 2: Show SealedSecret Exists

```bash
kubectl get sealedsecret -n soc-agent-demo
```

**Expected output:**
```
NAME           AGE
demo-api-key   5m
```

---

### Step 3: Show Encrypted YAML (Safe for Git)

```bash
cat soc-agent-system/k8s/sealed-secrets/demo-sealed-secret.yaml
```

**Point out:**
- All secret values are encrypted ciphertext
- Safe to commit to Git
- Cannot be decrypted without cluster's private key

---

### Step 4: Show Unsealed Secret

```bash
kubectl get secret demo-api-key -n soc-agent-demo
```

**Expected output:**
```
NAME           TYPE     DATA   AGE
demo-api-key   Opaque   2      5m
```

---

## 🎯 Talking Points

### After showing the encrypted YAML:

> "This is the GitOps solution to the secret leak problem. The YAML you're looking at contains API keys, but they're encrypted with the cluster's public key. I can commit this file to Git safely—if it leaks, it's useless without the cluster's private key.
>
> **The workflow is:** developer creates plaintext secret → kubeseal encrypts it with cluster public key → encrypted YAML committed to Git → controller in the cluster decrypts it on apply. The private key never leaves the cluster.
>
> **Key rotation happens automatically every 30 days**. Old keys are retained for grace period, so existing secrets keep working.
>
> **This is the alternative to HashiCorp Vault or AWS Secrets Manager**—it solves the same problem but doesn't require external dependencies. The trade-off: per-cluster encryption keys instead of centralized secret management. For a single-cluster deployment, Sealed Secrets is simpler."

---

## 📊 Validation Commands

**Before demo:**

```bash
# 1. Controller running
kubectl get deployment sealed-secrets-controller -n kube-system
# Expected: 1/1 READY

# 2. SealedSecret CRD exists
kubectl get crd sealedsecrets.bitnami.com
# Expected: CRD listed

# 3. Demo SealedSecret deployed
kubectl get sealedsecret demo-api-key -n soc-agent-demo
# Expected: AGE > 0

# 4. Secret unsealed successfully
kubectl get secret demo-api-key -n soc-agent-demo
# Expected: DATA column shows 2
```

---

## 🔧 Live Demo (If Needed)

### Create a new sealed secret live:

```bash
# 1. Create plaintext secret (dry-run)
kubectl create secret generic live-demo \
    --from-literal=password=supersecret123 \
    --namespace=soc-agent-demo \
    --dry-run=client -o yaml > /tmp/plaintext.yaml

# 2. Show plaintext (for contrast)
cat /tmp/plaintext.yaml | grep password:

# 3. Encrypt it
kubeseal -o yaml < /tmp/plaintext.yaml > /tmp/sealed.yaml

# 4. Show encrypted ciphertext
cat /tmp/sealed.yaml | grep encryptedData: -A2

# 5. Apply it
kubectl apply -f /tmp/sealed.yaml

# 6. Verify secret was created
kubectl get secret live-demo -n soc-agent-demo
```

**Time:** ~90 seconds

---

## 📋 Comparison Matrix Reference

**Location:** `soc-agent-system/k8s/sealed-secrets/README.md`

**Quick comparison:**

| Solution | GitOps Safe | Operational Complexity | External Dependencies |
|----------|-------------|------------------------|----------------------|
| **Sealed Secrets** | ✅ YES | Low (1 pod) | None |
| External Secrets Operator | ⚠️ Partial | Medium | Vault/AWS/GCP |
| Native K8s Secrets | ❌ NO | None | None |

**Decision:** Sealed Secrets for GitOps workflow, zero external dependencies

---

## ✅ Verification Checklist

Before demo:

- [ ] Controller pod running: `kubectl get pods -n kube-system | grep sealed`
- [ ] CRD installed: `kubectl get crd sealedsecrets.bitnami.com`
- [ ] Demo SealedSecret exists: `kubectl get sealedsecret -n soc-agent-demo`
- [ ] Demo Secret unsealed: `kubectl get secret demo-api-key -n soc-agent-demo`
- [ ] Encrypted YAML file: `cat soc-agent-system/k8s/sealed-secrets/demo-sealed-secret.yaml`

---

## 🎯 Key Stats for Demo

| Metric | Value | Meaning |
|--------|-------|---------|
| **Controller version** | v0.24.5 | Latest stable |
| **Key rotation** | Every 30 days | Automatic |
| **Encryption** | AES-256-GCM | Authenticated encryption |
| **Key size** | 4096-bit RSA | Industry standard |
| **Scope** | Cluster-wide | Single private key |
| **Git-safe** | ✅ YES | Encrypted YAML committable |

---

## 🚨 If Demo Fails

### If controller isn't running:

```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.5/controller.yaml
kubectl wait --for=condition=Available --timeout=60s -n kube-system deployment/sealed-secrets-controller
```

### If SealedSecret doesn't exist:

```bash
bash soc-agent-system/k8s/sealed-secrets/deploy-sealed-secrets.sh
```

### Fallback: Show the concept without live demo

> "The controller architecture is: plaintext secret → kubeseal CLI encrypts with cluster public key → encrypted YAML committed to Git → controller decrypts with cluster private key on apply. The decision matrix is here [show README.md] — Sealed Secrets won because it's GitOps-native and has zero external dependencies."

---

## 📁 Files Reference

```
soc-agent-system/k8s/sealed-secrets/
├── deploy-sealed-secrets.sh          # Automated deployment
├── DEMO-GUIDE.md                     # This file
├── README.md                         # Comparison matrix + decision rationale
└── demo-sealed-secret.yaml           # Encrypted demo secret (safe for Git)
```

---

**Demo ready! Sealed Secrets validated and working.** ✅
