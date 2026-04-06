# Demo State Reset Guide

**Purpose:** Clean demo state between runs to prevent false positives  
**Use Case:** After running adversarial attacks (note poisoning, etc.)

---

## 🚨 When to Reset

Reset demo state **before** running these scenarios:

1. ✅ **Before clean baseline demos** - Prevent false positives from previous attacks
2. ✅ **After note poisoning attack** - Clear fabricated historical notes
3. ✅ **Between demo sequences** - Start fresh for each demo run
4. ✅ **Before stakeholder presentations** - Ensure clean state

---

## 🛠️ How to Reset

### Option 1: CLI Script (Recommended)

**Full cleanup with confirmation:**

```bash
bash soc-agent-system/k8s/reset-demo-state.sh
```

**What it does:**
1. Shows current Redis keys (threats, VT cache, etc.)
2. Asks for confirmation before deleting
3. Clears all threat data (`threat:*`, `threats:*`)
4. Clears historical incidents (`historical:*`, `incidents:*`)
5. Preserves VT cache (`vt:pkg:*`)
6. Restarts backend pods (clears in-memory state)
7. Verifies cleanup completed

**Output:**
```
[1/4] Checking Redis connectivity...
✅ Redis pod: soc-agent-redis-xxx

[2/4] Current Redis keys...
Threat keys: 5
VT cache keys: 3

[3/4] Confirm cleanup
WARNING: This will delete all threats and historical data
Continue? (y/N): y

[4/4] Cleaning Redis...
✅ Redis cleanup complete

After cleanup:
  Threats: 0 (should be 0)
  VT cache: 3 (should be 3 - preserved)

✅ Demo State Reset Complete!
```

### Option 2: API Endpoint

**Programmatic reset (for automation):**

```bash
curl -X POST http://localhost:8000/api/demo/reset
```

**Response:**
```json
{
  "status": "success",
  "storage": "redis",
  "cleared": {
    "threat_keys": 5,
    "historical_keys": 18,
    "incident_keys": 0,
    "total_redis_keys": 25
  },
  "preserved": {
    "vt_cache": "vt:pkg:* keys preserved (demo malware data)"
  },
  "message": "Demo state reset complete. Frontend will show no threats."
}
```

---

## 📊 What Gets Cleared

### Deleted:

- ✅ **All threats** (`threat:*` keys)
- ✅ **Threats sorted set** (`threats:by_created`)
- ✅ **Threat counter** (`threats:total_count`)
- ✅ **Historical incidents** (`historical:*` keys)
- ✅ **Incident data** (`incidents:*` keys)
- ✅ **In-memory state** (via pod restart)

### Preserved:

- ✅ **VT cache** (`vt:pkg:*`) - 3 malware packages for enrichment
- ✅ **Configuration** (ConfigMaps, Secrets)
- ✅ **Pod definitions** (Deployments, Services)
- ✅ **Observability data** (Prometheus, Loki, Jaeger)

---

## 🔍 Verify Reset Worked

### Check Redis is empty:

```bash
# Should return: (empty array)
kubectl exec -n soc-agent-demo deployment/soc-agent-redis -- redis-cli KEYS "threat:*"

# Should return: 3 VT cache keys (preserved)
kubectl exec -n soc-agent-demo deployment/soc-agent-redis -- redis-cli KEYS "vt:pkg:*"
```

### Check frontend:

1. Open http://localhost:8080
2. **Expected:** "No recent threats" message
3. **Expected:** Threat counter shows 0

---

## 🎯 Demo Sequence Workflow

### Full Demo Run (Clean → Attack → Clean)

```bash
# 1. Start with clean state
bash soc-agent-system/k8s/reset-demo-state.sh

# 2. Run baseline (clean signal)
curl -X POST http://localhost:8000/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"scenario":"demo"}'

# 3. Show clean analysis (no adversarial detection)
# Frontend shows: Normal threat analysis

# 4. Reset for attack demo
bash soc-agent-system/k8s/reset-demo-state.sh

# 5. Run note poisoning attack
curl -X POST http://localhost:8000/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_catch", "adversarial_detector_enabled": true}'

# 6. Show adversarial detection
# Frontend shows: "HISTORICAL NOTE FABRICATION" warning

# 7. Reset before next demo
bash soc-agent-system/k8s/reset-demo-state.sh
```

---

## ⚠️ Troubleshooting

### Issue 1: VT cache deleted by mistake

**Symptom:** No VT findings in new threats

**Fix:**
```bash
# Restart backend to re-seed VT cache (DEMO_MODE=true)
kubectl rollout restart deployment/soc-agent-backend -n soc-agent-demo

# Wait for seed
sleep 10

# Verify
kubectl exec -n soc-agent-demo deployment/soc-agent-redis -- redis-cli KEYS "vt:pkg:*"
# Should show: 3 keys
```

### Issue 2: Threats still showing in frontend

**Symptom:** Old threats visible after reset

**Fix:**
```bash
# Hard refresh frontend
# Chrome/Firefox: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)

# Or clear browser cache and reload
```

### Issue 3: Script can't find Redis pod

**Symptom:** "Redis pod not found"

**Fix:**
```bash
# Check namespace
kubectl get pods -n soc-agent-demo

# If different namespace, pass as argument:
bash soc-agent-system/k8s/reset-demo-state.sh your-namespace
```

---

## 📋 Quick Reference

### Common Commands

```bash
# Reset demo state (interactive)
bash soc-agent-system/k8s/reset-demo-state.sh

# Reset via API
curl -X POST http://localhost:8000/api/demo/reset

# Check Redis keys
kubectl exec -n soc-agent-demo deployment/soc-agent-redis -- redis-cli KEYS "*"

# View backend logs
kubectl logs -n soc-agent-demo -l app=soc-backend --tail=50

# Restart backend (re-seeds VT cache)
kubectl rollout restart deployment/soc-agent-backend -n soc-agent-demo
```

---

## ✅ Best Practices

1. **Always reset before stakeholder demos** - Ensures clean state
2. **Reset between attack scenarios** - Prevents cross-contamination
3. **Use CLI script for full cleanup** - Includes pod restart
4. **Use API for automation** - Good for CI/CD or scripted demos
5. **Verify VT cache preserved** - Should always have 3 keys

---

**Problem solved! Demo state can now be cleanly reset between runs.** 🎉
