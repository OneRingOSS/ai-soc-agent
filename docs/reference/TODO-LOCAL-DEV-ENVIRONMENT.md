# TODO: Fix Local Development Environment

## Status: Deferred (Not blocking demos)

**Decision Date:** April 6, 2026  
**Reason:** CI provides equivalent validation. Local dev environment has Python version conflicts that require time to debug properly.

---

## 🎯 Issue Summary

### Problem:
Running `make quality-gate` locally fails due to Python version incompatibilities.

**Error:**
```
pydantic-core==2.14.6 cannot build on Python 3.13
TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'
ERROR: Failed building wheel for pydantic-core
```

**Root Cause:**
- User has Python 3.13.2 (system default)
- pydantic-core 2.14.6 was released before Python 3.13 existed
- Rust extensions in pydantic-core don't support Python 3.13

---

## ✅ Current Workaround

### Use CI for Validation:

**GitHub Actions runs all quality checks:** https://github.com/OneRingOSS/ai-soc-agent/actions

**CI validates:**
- ✅ Linting (ruff)
- ✅ Unit tests (pytest with 55%+ coverage)
- ✅ Secret scanning (TruffleHog)
- ✅ Dependency scanning (pip-audit)
- ✅ Workflow scanning (zizmor)
- ✅ Lockfile validation (npm)
- ✅ Container scanning (Trivy)

**For demos:** Use CI logs as proof that all quality gates pass.

---

## 🔧 Proposed Solution (Future Work)

### Option 1: Install Python 3.11 (Recommended)

```bash
# Install Python 3.11 via Homebrew
brew install python@3.11

# Recreate venv with Python 3.11
cd soc-agent-system/backend
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip==24.0
pip install -r requirements.txt
pip install ruff==0.1.14 pytest==7.4.4 pytest-cov==4.1.0 pytest-asyncio==0.23.3

# Test it works
cd ../..
make quality-gate
```

**Why Python 3.11:**
- ✅ Matches Docker image (FROM python:3.11-slim)
- ✅ Fully compatible with all dependencies
- ✅ Production parity (dev = prod)
- ✅ Same version as some CI jobs

### Option 2: Upgrade Dependencies (Future)

Update `requirements.txt` to use newer pydantic that supports Python 3.13:
```
pydantic==2.9.0  # Supports Python 3.13
pydantic-core==2.23.0  # Supports Python 3.13
```

**But this requires:**
- Testing all code for breaking changes
- Updating Docker image Python version
- Coordinating CI Python version
- Part of P2 work (Python version standardization)

### Option 3: Use pyenv for Multiple Python Versions

```bash
brew install pyenv
pyenv install 3.11.10
cd soc-agent-system/backend
pyenv local 3.11.10
rm -rf venv
python -m venv venv
# ... rest of setup
```

---

## 📊 What Works vs. What Doesn't

### ✅ What Works (Production):
- Kubernetes deployment (Python 3.11 in Docker)
- CI/CD pipeline (Python 3.9/3.11 in GitHub Actions)
- All 57 tests passing
- All security scans passing
- ACT2 adversarial detection working
- Observability stack working

### ❌ What Doesn't Work (Local Dev):
- `make quality-gate` (Python 3.13 incompatibility)
- Local linting via Make (requires venv)
- Local testing via Make (requires venv)

### ✅ What Works (Local Dev):
- Kubernetes cluster (Kind)
- Backend/frontend deployment
- All demos (ACT1, ACT2)
- Observability dashboards
- API testing (curl)
- validate-deployment.sh (8/8 tests pass)

---

## 🎯 Impact Assessment

### Blocking for:
- ❌ **NOT BLOCKING:** Demos (use CI logs)
- ❌ **NOT BLOCKING:** Deployments (Docker/K8s work)
- ❌ **NOT BLOCKING:** Testing (CI validates)
- ❌ **NOT BLOCKING:** Production (unaffected)

### Would be nice for:
- ⚠️ Local development iteration speed
- ⚠️ Pre-commit validation
- ⚠️ Offline development

---

## 📝 Files Created (For Future Fix)

1. `soc-agent-system/backend/setup-dev-env.sh`
   - Automated venv setup
   - Python version detection
   - Rejects Python 3.13+ with helpful error

2. `soc-agent-system/Makefile` (Updated)
   - Added venv path variables
   - Added check-venv target
   - Better error messages

3. `validate-deployment.sh`
   - Alternative to `make quality-gate`
   - Tests deployed K8s environment
   - 8 validation checks (all passing)

---

## 🚀 Recommendation

### For Now:
**Use CI for validation.** It's actually more reliable than local dev because:
- ✅ Clean environment every run
- ✅ Reproducible
- ✅ Same as production
- ✅ No version conflicts

### For Future (P2 Work):
**Standardize Python versions across all environments:**
- Dev: Python 3.11 (via pyenv or Homebrew)
- CI: Python 3.11 (update workflow)
- Docker: Python 3.11 (already matches)
- Result: Consistent everywhere

---

## 📋 Related Documents

- `STRIDE-THREAT-MODEL-v6.md` - P2: Python version standardization
- `.github/workflows/ci.yml` - CI validation (working)
- `soc-agent-system/Makefile` - Local validation (needs Python 3.11)
- `validate-deployment.sh` - K8s validation (working)

---

## ✅ Acceptance Criteria (For Future Fix)

When this TODO is addressed, the following should work:

```bash
# Fresh checkout
git clone <repo>
cd soc-agent-system/backend

# Automated setup
bash setup-dev-env.sh

# Quality gate passes
cd ../..
make quality-gate

# Output:
# ✅ ALL QUALITY GATES PASSED (7 checks)
```

**Current status:** ❌ Fails on Python 3.13  
**Target status:** ✅ Works on Python 3.11  
**Priority:** Low (not blocking any work)

---

**For demos: Use https://github.com/OneRingOSS/ai-soc-agent/actions to show CI validation.** ✅
