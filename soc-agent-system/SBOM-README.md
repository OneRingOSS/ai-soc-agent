# Software Bill of Materials (SBOM) - Implementation Guide

## Executive Summary

**Format:** CycloneDX 1.5 JSON (OWASP standard)  
**Tool:** Syft by Anchore  
**Automation:** Generated automatically in CI/CD  
**Purpose:** Supply chain security, vulnerability tracking, compliance audits

---

## What is an SBOM?

An SBOM (Software Bill of Materials) is a comprehensive inventory of all components, dependencies, and libraries used in a software application. It's analogous to an ingredients label on food products.

**Key use cases:**
1. **Vulnerability Management** - Identify affected components when CVEs are disclosed
2. **License Compliance** - Track open-source license obligations
3. **Supply Chain Security** - Detect compromised or malicious dependencies
4. **Regulatory Compliance** - SBOM mandated by EO 14028 (Federal software)

---

## Implementation

### Local Generation

```bash
# Generate SBOM for backend
cd soc-agent-system
bash generate-sbom.sh
```

**Output:**
- `sbom-backend.json` - Backend source code dependencies
- `sbom-frontend.json` - Frontend source code dependencies
- `sbom-backend-image.json` - Backend Docker image dependencies
- `sbom-frontend-image.json` - Frontend Docker image dependencies

### CI/CD Automation

**GitHub Actions workflow** (`.github/workflows/ci.yml`):

```yaml
- name: Install Syft
  run: |
    SYFT_VERSION="1.0.1"
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin v${SYFT_VERSION}

- name: Generate SBOM
  run: |
    syft packages dir:backend -o cyclonedx-json > sbom-backend.json
    syft packages docker:soc-backend:latest -o cyclonedx-json > sbom-backend-image.json

- name: Upload SBOM artifacts
  uses: actions/upload-artifact@v4
  with:
    name: sbom-cyclonedx
    path: soc-agent-system/sbom-*.json
    retention-days: 90
```

**Every CI run** produces SBOM artifacts attached to the workflow run.

---

## SBOM Contents

### Backend SBOM (Sample)

**Total components:** 37 (example from test run)

**Sample dependencies:**
```
- fastapi@0.109.1
- uvicorn@0.27.0
- pydantic@2.5.3
- openai@1.10.0
- prometheus-client@0.19.0
```

**Metadata included:**
- Component name and version
- Package type (PyPI, npm, OS package)
- License information (when available)
- File paths and hashes
- Dependencies tree

---

## Vulnerability Scanning with SBOM

### Using Grype (Syft's companion tool)

```bash
# Install Grype
brew install grype

# Scan SBOM for vulnerabilities
grype sbom:soc-agent-system/sbom-backend.json

# Filter by severity
grype sbom:soc-agent-system/sbom-backend.json --fail-on critical
```

**Output:** List of known CVEs affecting dependencies

---

## CycloneDX Format

**Why CycloneDX over SPDX?**

| Criterion | CycloneDX | SPDX |
|-----------|-----------|------|
| **Focus** | Application security | License compliance |
| **Vulnerability data** | ✅ Native support | ⚠️ Limited |
| **Tooling** | ✅ Broad support | ✅ Good support |
| **Standardization** | OWASP standard | ISO/IEC 5962 |
| **JSON schema** | ✅ Well-defined | ✅ Well-defined |

**Decision:** CycloneDX chosen for security-first use case (vulnerability tracking > license compliance)

---

## Compliance & Regulatory

### Executive Order 14028 (U.S. Federal)

**Requires:** Software vendors to provide SBOM for all software sold to U.S. Government

**Our compliance:**
- ✅ SBOM generated automatically
- ✅ CycloneDX format (NTIA minimum elements compliant)
- ✅ Archived in CI artifacts (90-day retention)
- ✅ Machine-readable JSON

### NTIA Minimum Elements

Our SBOM includes all required fields:
- ✅ Supplier name (Anchore Syft)
- ✅ Component name
- ✅ Version of component
- ✅ Other unique identifiers (package URLs)
- ✅ Dependency relationships
- ✅ Author of SBOM data (automated CI)
- ✅ Timestamp (CI run date)

---

## Integration with Security Scanning

### Current Workflow

```
1. Developer commits code
2. CI builds Docker images
3. Syft generates SBOM from images
4. SBOM uploaded as artifact
5. (Future) Grype scans SBOM for CVEs
6. (Future) Results posted to security dashboard
```

### Future Enhancements

**Not yet implemented (documented in THREAT_MODEL.md):**
1. **Automated CVE scanning** - Grype in CI pipeline
2. **SBOM diffing** - Track dependency changes between releases
3. **License compliance** - Automated detection of restrictive licenses
4. **SBOM signing** - Cosign signatures for SBOM authenticity

---

## Demo Validation

### Verify SBOM generated locally

```bash
cd soc-agent-system
bash generate-sbom.sh

# Expected output:
# ✅ sbom-backend.json created (37 components)
# ✅ sbom-frontend.json created
```

### Verify CI artifacts

**GitHub Actions run:** https://github.com/OneRingOSS/ai-soc-agent/actions

**Check for:**
- Artifact named `sbom-cyclonedx`
- Contains 4 JSON files (backend source, frontend source, backend image, frontend image)

---

## Files Reference

```
soc-agent-system/
├── generate-sbom.sh              # Local SBOM generation script
├── SBOM-README.md                # This document
└── sbom-*.json                   # Generated SBOMs (gitignored)
```

---

## Talking Points for Demo

> "Every CI run automatically produces a Software Bill of Materials—a complete inventory of every dependency, library, and component in the application. This is stored as a CycloneDX JSON artifact.
>
> **Why this matters:** When a CVE like Log4Shell is disclosed, I can query the SBOM in seconds to know if we're affected. No manual audits, no 'we think we're using version X.'
>
> **The format is CycloneDX** because it's designed for security use cases—it includes vulnerability metadata natively, unlike SPDX which focuses on licensing.
>
> **This is a compliance requirement** for Federal software under Executive Order 14028. But beyond compliance, it's operational intelligence: I know exactly what's running in production at the dependency level."

---

**Status:** ✅ Implemented, tested, and integrated into CI/CD  
**Demo ready:** YES (show CI artifacts)  
**Next steps:** Add Grype scanning + automated CVE tracking
