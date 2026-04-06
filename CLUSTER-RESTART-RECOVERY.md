# Cluster Restart Recovery Guide

This guide ensures all configurations are restored after a Kind cluster restart.

---

## ✅ What's Already Persisted (No Action Needed)

These are committed to git and automatically applied by `deploy.sh`:

- ✅ **Helm values:** `FORCE_MOCK_MODE: "false"` (live OpenAI mode)
- ✅ **Helm values:** `DEMO_MODE: "true"` (VT cache mode)
- ✅ **Adversarial detector:** Fixed field name (`resolution_notes`)
- ✅ **Pattern detection:** Exact template matching
- ✅ **Demo reset script:** `reset-demo-state.sh`
- ✅ **Observability:** `startup-cluster-services.sh`
- ✅ **All backend code:** Deployed via Docker image

---

## ⚠️ What's NOT Persisted (Action Required)

These must be recreated after cluster restart:

### 1. **OpenAI API Key Secret** ← **CRITICAL!**

**Why not persisted:** Secrets are stored in cluster etcd, not in git (for security)

**How to restore:**
```bash
# Option 1: Use setup script (recommended)
bash soc-agent-system/k8s/setup-openai-secret.sh

# Option 2: Manual
source soc-agent-system/backend/.env
kubectl create secret generic openai-api-key \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  -n soc-agent-demo
kubectl set env deployment/soc-agent-backend \
  --from=secret/openai-api-key \
  -n soc-agent-demo
```

### 2. **VT Cache (Redis)** ← **Handled by deploy.sh**

**Why not persisted:** Redis data is ephemeral (no PersistentVolume)

**How to restore:** Automatically seeded by backend on startup when `DEMO_MODE=true`

---

## 🚀 Complete Cluster Restart Recovery (One Command)

```bash
# Full recovery script
bash soc-agent-system/k8s/post-cluster-restart.sh
```

This script will:
1. ✅ Check if cluster is running
2. ✅ Deploy all Helm charts (includes FORCE_MOCK_MODE=false)
3. ✅ Create OpenAI API key secret (from .env file)
4. ✅ Start observability port-forwards
5. ✅ Verify backend is in live mode
6. ✅ Verify VT cache is seeded

---

## 📋 Manual Recovery Checklist

If you prefer to run steps manually:

### Step 1: Deploy Cluster
```bash
cd soc-agent-system/k8s
./deploy.sh
```

**This automatically:**
- ✅ Deploys backend with `FORCE_MOCK_MODE: "false"`
- ✅ Deploys backend with `DEMO_MODE: "true"`
- ✅ Seeds VT cache with 3 malware packages
- ✅ Starts observability services

### Step 2: Configure OpenAI API Key
```bash
bash soc-agent-system/k8s/setup-openai-secret.sh
```

**This creates:**
- ✅ Kubernetes secret: `openai-api-key`
- ✅ Environment variable in pods: `OPENAI_API_KEY`
- ✅ Restarts backend pods

### Step 3: Verify Live Mode
```bash
kubectl logs -n soc-agent-demo -l app=soc-backend --tail=50 | grep -E "Mode:|use_mock|demo_mode"
```

**Expected output:**
```
Mode: LIVE (OpenAI API enabled)  ✅
demo_mode=True                    ✅
```

### Step 4: Test ACT2
```bash
./test-act2.sh
```

**Expected output:**
```
✅ SUCCESS: Adversarial manipulation detected!
manipulation_detected: true
attack_vector: "context_agent, historical_note_fabrication"
```

---

## 🔧 Troubleshooting

### Backend Pods CrashLoopBackOff
**Cause:** OpenAI API key not configured  
**Fix:**
```bash
bash soc-agent-system/k8s/setup-openai-secret.sh
```

### "Mode: MOCK" in logs
**Cause:** Helm values not applied  
**Fix:**
```bash
cd soc-agent-system/k8s
helm upgrade soc-agent charts/soc-agent -n soc-agent-demo
kubectl rollout restart deployment/soc-agent-backend -n soc-agent-demo
```

### VT Cache Empty
**Cause:** `DEMO_MODE` not enabled  
**Fix:**
```bash
# Check if DEMO_MODE is set
kubectl exec -n soc-agent-demo deployment/soc-agent-backend -- env | grep DEMO_MODE

# If not set, upgrade Helm
helm upgrade soc-agent soc-agent-system/k8s/charts/soc-agent -n soc-agent-demo
```

### Adversarial Detection Not Working
**Cause:** Missing OpenAI key or wrong field name  
**Fix:**
```bash
# 1. Verify API key
kubectl get secret openai-api-key -n soc-agent-demo

# 2. Verify code has field fix
kubectl logs -n soc-agent-demo -l app=soc-backend | grep "resolution_notes"

# 3. If not found, redeploy
cd soc-agent-system/k8s
./deploy.sh
bash setup-openai-secret.sh
```

---

## ✅ Success Criteria

After cluster restart recovery, verify:

- ✅ Pods: `kubectl get pods -n soc-agent-demo` → All Running
- ✅ Live mode: Logs show `Mode: LIVE`
- ✅ OpenAI key: Secret exists in namespace
- ✅ VT cache: Redis has 3 keys
- ✅ ACT2: Test script shows `manipulation_detected: true`

---

## 📝 Summary

**What persists across restarts:**
- All code changes (via Docker image)
- Helm configuration (FORCE_MOCK_MODE=false, DEMO_MODE=true)
- Scripts (reset, setup, test)

**What doesn't persist:**
- OpenAI API key secret (must recreate)
- Redis VT cache (auto-reseeded)

**One-command recovery:**
```bash
bash soc-agent-system/k8s/post-cluster-restart.sh
```

**Manual recovery:**
1. `./deploy.sh`
2. `bash setup-openai-secret.sh`
3. `./test-act2.sh` (verify)
