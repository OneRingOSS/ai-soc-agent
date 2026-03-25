# Historical Note Poisoning Demo - Quick Reference Guide

## 🎯 Overview

This demo showcases **LLM semantic reasoning** to detect fabricated analyst notes - an attack surface that **rule-based systems cannot detect**.

---

## 🚀 How to Run

### Quick Demo (Recommended) ⭐

**Shows threats in the actual UX feed** - Best for demonstrating real-world impact!

#### Prerequisites

Ensure your Kind cluster is running:
```bash
# Check cluster status
kubectl get pods -n soc-agent-demo

# If not running, deploy:
cd soc-agent-system/k8s
./deploy.sh
```

#### Run the Demo

**From your local machine** (not inside the cluster), run these curl commands:

```bash
# ACT 1: Bypass (Detector Disabled) - Attack Succeeds
curl -X POST http://localhost:8080/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_bypass", "adversarial_detector_enabled": false}'

# ACT 2: Catch (Detector Enabled) - Attack Caught
curl -X POST http://localhost:8080/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_catch", "adversarial_detector_enabled": true}'

# View in Browser
open http://localhost:8080
# Hard refresh: Cmd + Shift + R (Mac) or Ctrl + Shift + R (Windows/Linux)
```

**Access Points**:
- **Frontend UI**: http://localhost:8080 (via ingress)
- **Backend API**: http://localhost:8080/api/threats (via ingress)
- **Backend Logs**: `kubectl logs -n soc-agent-demo -l app=soc-backend --tail=100`

**Duration**: ~30 seconds
**UX Impact**: ✅ **Threats appear in the UI at http://localhost:8080**
**Customer Names**: `DEMO_NotePoisonCorp_ACT1`, `DEMO_NotePoisonCorp_ACT2`

---

## 📋 What You'll See

### **ACT 1: THE BYPASS** (Detector Disabled)
- ✅ 18 fabricated notes injected
- ❌ Detector is DISABLED
- ❌ Attack bypasses detection
- **Result**: `manipulation_detected: False`

### **ACT 2: THE CATCH** (Detector Enabled)
- ✅ Same 18 fabricated notes
- ✅ Detector is ENABLED
- ✅ Attack is CAUGHT
- **Result**: `manipulation_detected: True`, `attack_vector: historical_note_fabrication`

### **BASELINE: NO FALSE POSITIVES**
- ✅ 4 real analyst notes
- ✅ Detector is ENABLED
- ❌ No false alerts (below 5-note threshold)
- **Result**: `manipulation_detected: False`

---

## 🎨 UI Testing - Visual Comparison (Kind Cluster)

### **Quick Test Commands**

**Trigger ACT 1 (Bypass):**
```bash
curl -X POST http://localhost:8080/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_bypass", "adversarial_detector_enabled": false}'
```

**Trigger ACT 2 (Catch):**
```bash
curl -X POST http://localhost:8080/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_catch", "adversarial_detector_enabled": true}'
```

**View Results:**
- Open browser: http://localhost:8080
- Hard refresh: `Cmd + Shift + R` (Mac) or `Ctrl + Shift + F5` (Windows)

### **Visual Differences**

#### **ACT 1 (DEMO_NotePoisonCorp_ACT1) - Attack Succeeds:**
- ❌ **NO red "Adversarial Attack Detected" badge** (detector was disabled)
- ❌ **NO yellow "Requires Review" badge** (system thinks it's safe)
- ⚠️ **FP Score: 65%** - High score, **NO warning** (attack succeeded)
- ✅ **Clean FP Analysis section** - No red border, no warning box
- ❌ **NO Adversarial Detection section** when expanded

**This demonstrates the attack working!** The poisoned historical notes successfully tricked the system into thinking this is likely a false positive, and there's no warning to the analyst.

#### **ACT 2 (DEMO_NotePoisonCorp_ACT2) - Attack Caught:**
- 🚨 **Red "Adversarial Attack Detected" badge** (detector caught it)
- ⚠️ **Yellow "Requires Review" badge** (flagged for human review)
- 🚨 **FP Score: 65%** - Same score, but **WITH red warning box** explaining it's unreliable
- 🚨 **Red border around FP Analysis section**
- 🚨 **Red warning box**: "⚠️ WARNING: This FP score may be unreliable due to detected adversarial manipulation of historical data"
- 🚨 **Full Adversarial Detection section** with detailed analysis when expanded

**This demonstrates the defense working!** The adversarial detector caught the manipulation and warned the analyst that the FP score is unreliable.

### **The FP Score Paradox - Explained**

Both ACT 1 and ACT 2 show **FP Score: 65%** (likely false positive). This is actually **proof the attack is working**!

- The poisoned historical notes successfully tricked the **FP Analyzer** into thinking this is a false positive
- However, the **Adversarial Detector** (when enabled) catches the manipulation
- The UI now warns the analyst that the FP score is unreliable due to poisoned data
- This demonstrates the **value of the adversarial detection layer** - it catches attacks that fool other parts of the system

### **Demo Narrative for Presentations**

1. **Show ACT 1**: "Here's a real attack with poisoned historical notes. The system thinks it's 65% likely a false positive. **No warnings, no alerts.** The attack succeeded - this threat would likely be dismissed."

2. **Show ACT 2**: "Same attack, same poisoned data, but with adversarial detection enabled. **Red badges everywhere!** The system caught the manipulation and warned the analyst that the FP score is unreliable."

3. **The Punchline**: "Without adversarial detection, this real attack would have been dismissed as a false positive. With it, we catch the manipulation and flag it for human review. The FP score is still 65%, but now the analyst knows it's been compromised."

---

## 🔍 Key Logs to Watch For

### **1. Attack Injection (Step 1)**
```
📍 Step 1: Red Team injects poisoned notes...
   ✓ Poisoned historical context:
     - Similar incidents: 18                 ← 18 FABRICATED NOTES
```

### **2. Detection Result (Step 3 - ACT 2 ONLY)**
```
🚨 ADVERSARIAL MANIPULATION DETECTED
   attack_vector: historical_note_fabrication    ← KEY DETECTION!
   anomalies: 1
   confidence: 0.80

✅ Step 3: Verifying attack was CAUGHT...
   ✓ Manipulation detected: True
   ✓ Attack vector: historical_note_fabrication
   ✓ Anomaly description: These notes exhibit hallmarks of automated fabrication...
```

---

## 🎭 Attack Signatures Detected

The LLM identifies these fabrication indicators:

1. **Templated Structure** - All 18 notes follow identical pattern:
   ```
   "Closed - false positive. [Team] confirmed [activity]. [Benign phrase]."
   ```

2. **Service Account Authorship** - All resolved by `admin_svc` (not human analysts)

3. **Unrealistic Resolution Times** - 3 minutes for complex SQL injection threats

4. **Missing Work Item References** - No JIRA tickets, no colleague names

5. **Generic Team References** - "Security team" instead of "sarah.chen" or "james.okafor"

6. **Temporal Clustering** - 1 note/day pattern over 18 days

---

## 💡 Why This Demo Matters

### **Rule-Based Systems CANNOT Detect This Because:**
- ❌ No single field is "wrong" (all values are technically valid)
- ❌ Service accounts are legitimate (can't ban them)
- ❌ Fast resolutions happen (some issues are quick)
- ❌ Generic language is valid (not all analysts write detailed notes)

### **Only LLM Semantic Reasoning Can:**
- ✅ Evaluate linguistic plausibility across multiple notes
- ✅ Detect templated patterns that indicate automation
- ✅ Identify domain reasoning mismatches (e.g., service account resolving complex threats in 3 min)
- ✅ Compare against authentic analyst behavior

---

## 🎤 Presentation Script

### **Opening (30 seconds)**
> "I'm going to show you an attack that **rule-based systems cannot detect**. We'll inject 18 fabricated analyst notes designed to bias the system toward False Positives. Watch what happens when the detector is off, then on."

### **ACT 1 (20 seconds)**
> "First, the detector is DISABLED. Notice the attack bypasses detection - the system processes normally. This is the vulnerability."

### **ACT 2 (30 seconds)**
> "Now, the **same attack** with the detector ENABLED. Watch for the `🚨 ADVERSARIAL MANIPULATION DETECTED` log. The LLM identifies `historical_note_fabrication` with 0.80 confidence. It detected the templated structure, service account authorship, and unrealistic resolution times - things rules can't evaluate."

### **BASELINE (10 seconds)**
> "Finally, 4 real analyst notes. No false positives. The system correctly identifies authentic notes."

---

## 📊 Success Metrics

| Test | Expected Result | What to Verify |
|------|----------------|----------------|
| **ACT 1** | Attack bypasses | `manipulation_detected: False` |
| **ACT 2** | Attack caught | `attack_vector: historical_note_fabrication` |
| **BASELINE** | No false positive | `manipulation_detected: False` |

---

## 🔧 Troubleshooting

### **Script Permission Denied**
```bash
chmod +x demo_note_poisoning.sh
```

### **Tests Fail**
```bash
# Run tests individually to debug
pytest tests/test_e2e_note_poisoning.py::TestE2ENotePoisoning::test_e2e_act1_bypass_with_detector_disabled -v
pytest tests/test_e2e_note_poisoning.py::TestE2ENotePoisoning::test_e2e_act2_catch_with_detector_enabled -v
pytest tests/test_e2e_note_poisoning.py::TestE2ENotePoisoning::test_e2e_no_false_positive_on_real_notes -v
```

---

## 📚 Additional Resources

- **Full Demo Guide**: `README_DEMOS.md`
- **Evidence Guide**: `DEMO_EVIDENCE_GUIDE.md`
- **Implementation Spec**: `docs/specs/Adversarial Demo Spec  Historical Note Poisoning.md`
- **Test File**: `tests/test_e2e_note_poisoning.py`
- **Mock Data**: `tests/adversarial_mock_data/historical_notes.py`

---

## 🎯 Key Takeaway

> **This demo proves that agentic SOC systems can detect attacks that are architecturally impossible for rule-based systems to identify - specifically, the semantic plausibility of free-text analyst notes.**

