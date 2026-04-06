# Documentation Index

This directory contains all project documentation organized by category.

## 📁 Directory Structure

```
docs/
├── deployment/          # Deployment guides and operational procedures
├── releases/           # Release notes and version summaries
├── testing/            # Test reports and validation documentation
├── reference/          # Reference materials and TODO lists
├── SecOps-demo-guide-v6.md        # Main demo script
└── STRIDE-THREAT-MODEL-v6.md      # Security threat model
```

---

## 📂 Deployment (`docs/deployment/`)

Guides for deploying and operating the system:

- **OBSERVABILITY-DEPLOYMENT-GUIDE.md** - Deploy Prometheus/Grafana/Loki stack
- **OBSERVABILITY-FIX-GUIDE.md** - Troubleshooting observability issues
- **OBSERVABILITY-ACCESS.md** - Access URLs and credentials
- **CLUSTER-RESTART-RECOVERY.md** - Recovery procedures after cluster restart
- **AUTOMATIC-STARTUP-SUMMARY.md** - Automated startup configuration
- **DEMO-RESET-GUIDE.md** - Reset demo state between runs
- **SBOM-IMPLEMENTATION-GUIDE.md** - Software Bill of Materials (SBOM) generation and compliance

---

## 📂 Releases (`docs/releases/`)

Release notes and version history:

- **RELEASE-v1.0.0-SUMMARY.md** - Initial release (ACT1 demo)
- **RELEASE-v1.1.0-DEMO-READY.md** - ACT2 adversarial detection release
- **FINAL-RELEASE-SUMMARY-v1.1.0.md** - Comprehensive v1.1.0 summary

---

## 📂 Testing (`docs/testing/`)

Test results and validation reports:

- **DEMO-VALIDATION-REPORT.md** - SecOps demo component validation
- **E2E-TEST-RESULTS.md** - End-to-end test results
- **IMPLEMENTATION-COMPLETE-SUMMARY.md** - Sealed Secrets + SBOM implementation
- **MAKEFILE-FIX-VALIDATION.md** - Makefile CI compatibility validation

---

## 📂 Reference (`docs/reference/`)

Reference materials and planning documents:

- **TODO-LOCAL-DEV-ENVIRONMENT.md** - Local dev setup TODO (deferred)
- **READY-FOR-MANUAL-VERIFICATION.md** - Manual verification checklist

---

## 🎯 Quick Links

### For Demos
- **[SecOps Demo Guide](SecOps-demo-guide-v6.md)** - Main demo walkthrough
- **[Demo Reset](deployment/DEMO-RESET-GUIDE.md)** - Reset state between demos
- **[Observability Access](deployment/OBSERVABILITY-ACCESS.md)** - Dashboard URLs

### For Deployment
- **[Observability Setup](deployment/OBSERVABILITY-DEPLOYMENT-GUIDE.md)** - Deploy monitoring stack
- **[Cluster Recovery](deployment/CLUSTER-RESTART-RECOVERY.md)** - Recover after restart
- **[Observability Troubleshooting](deployment/OBSERVABILITY-FIX-GUIDE.md)** - Fix common issues
- **[SBOM Guide](deployment/SBOM-IMPLEMENTATION-GUIDE.md)** - Software Bill of Materials generation

### For Security
- **[STRIDE Threat Model](STRIDE-THREAT-MODEL-v6.md)** - Complete security analysis
- **[Security Incident Response](/SECURITY-INCIDENT-RESPONSE.md)** - Incident playbook (root)
- **[Security Policy](/SECURITY.md)** - Vulnerability reporting (root)

### For Testing
- **[Demo Validation](testing/DEMO-VALIDATION-REPORT.md)** - Component readiness
- **[E2E Tests](testing/E2E-TEST-RESULTS.md)** - Full system validation
- **[CI Fix Validation](testing/MAKEFILE-FIX-VALIDATION.md)** - CI compatibility tests

---

## 🔄 Recent Updates

**Latest changes:**
- ✅ Reorganized all documentation from project root
- ✅ Created logical directory structure
- ✅ Consolidated release notes
- ✅ Grouped deployment guides
- ✅ Centralized test reports

---

## 📝 Contributing

When adding new documentation:

1. **Choose the right category:**
   - Deployment guides → `docs/deployment/`
   - Release notes → `docs/releases/`
   - Test reports → `docs/testing/`
   - Reference materials → `docs/reference/`

2. **Update this README** with a link to the new doc

3. **Use descriptive filenames** (e.g., `FEATURE-IMPLEMENTATION-GUIDE.md`)

---

## ✅ Documentation Health

**Status:** ✅ All docs organized and indexed  
**Last organized:** April 6, 2026  
**Total docs:** 15 files across 4 categories

---

**For the main project README, see [/README.md](/README.md)**
