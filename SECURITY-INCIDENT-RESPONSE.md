# Security Incident Response - Historical Record

This document tracks security incidents affecting the AI SOC Agent project, our response actions, and lessons learned.

---

## Incident #1: Trivy Container Scanner Tag Poisoning Vulnerability

**Date Discovered:** March 2024  
**Severity:** Critical  
**CVE/Advisory:** CERT-EU Advisory on Trivy SHA-pinning  
**Status:** ✅ Mitigated

### Summary

CERT-EU published an advisory highlighting that GitHub Actions using Docker image references with tags (e.g., `aquasec/trivy:latest` or `aquasec/trivy:0.48.0`) are vulnerable to tag poisoning attacks. An attacker with access to the image registry could retag a malicious image, causing CI pipelines to execute untrusted code.

### Impact

- **Affected Component:** `.github/workflows/ci.yml` - Quality Gate job
- **Attack Vector:** Malicious actor retags Trivy Docker image on registry
- **Potential Damage:** 
  - CI pipeline executes attacker-controlled code
  - Exposure of GitHub secrets (GITHUB_TOKEN, API keys)
  - Supply chain compromise via malicious CI artifacts
  - Potential for credential theft and lateral movement

### Root Cause

GitHub Actions were using semantic version tags instead of immutable SHA256 digests:

```yaml
# Vulnerable (before):
uses: aquasecurity/trivy-action@master  # Mutable branch reference
uses: actions/checkout@v4                # Tag can be force-pushed
uses: docker/setup-buildx-action@v3      # Mutable tag
```

### Remediation Actions

Implemented as part of Supply Chain Hardening Tier 1B and 1E:

1. **SHA-Pinned GitHub Actions (Tier 1B):**
   - Installed `pinact` tool for automated SHA pinning
   - Converted all GitHub Actions to SHA256 references
   - Added Dependabot to auto-update pinned SHAs weekly
   - Example fix:
     ```yaml
     # Secure (after):
     uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
     uses: docker/setup-buildx-action@2b51285047da1547ffb1b2203d8be4c0af6b1f20  # v3.2.0
     ```

2. **Workflow Security Analysis (Tier 1E):**
   - Installed `zizmor` workflow static analyzer
   - Added `make scan-workflows` target
   - Detects unpinned actions, excessive permissions, credential leaks
   - Integrated into CI quality gate

3. **Dependabot for Actions (Tier 1C):**
   - Configured `.github/dependabot.yml` for `github-actions` ecosystem
   - Weekly automated PR creation for SHA updates
   - Prevents SHA staleness over time

### Validation

- ✅ All GitHub Actions pinned to commit SHAs (verified via `zizmor`)
- ✅ Dependabot creating weekly update PRs
- ✅ CI pipeline passes with pinned actions
- ✅ No unpinned-uses errors in workflow scans

### Lessons Learned

- **Proactive scanning:** Workflow security analysis should be baseline, not reactive
- **Automation critical:** Manual SHA updates are error-prone; Dependabot essential
- **Defense in depth:** Combined SHA pinning + zizmor + Dependabot provides layered protection

### References

- CERT-EU Advisory: [Link to advisory if public]
- Tier 1B Implementation: `docs/specs/supply-chain-hardening-spec-v4.md`
- Commit: SHA of Tier 1B implementation

---

## Incident #2: CanisterWorm npm Supply Chain Attack (Proactive Mitigation)

**Date Discovered:** 2024 (public disclosure)  
**Severity:** Critical (Proactive - not exploited)  
**Attack Type:** Malicious npm postinstall hooks  
**Status:** ✅ Preemptively Mitigated

### Summary

The CanisterWorm attack demonstrated that malicious npm packages can execute arbitrary code via `postinstall`, `preinstall`, or `install` scripts. These scripts run automatically during `npm install` and can exfiltrate secrets, modify source code, or backdoor applications.

### Impact (Potential)

- **Affected Component:** Frontend build process (`soc-agent-system/frontend/`)
- **Attack Vector:** Malicious dependency executes code during npm install
- **Potential Damage:**
  - Exfiltration of environment variables (API keys, tokens)
  - Source code modification (backdoor injection)
  - CI secret theft (GITHUB_TOKEN, deployment credentials)
  - Supply chain compromise via infected builds

### Root Cause

Standard npm install workflow allows lifecycle scripts by default:

```bash
# Vulnerable (before):
npm install  # Executes all lifecycle scripts from node_modules
```

### Remediation Actions

Implemented as part of Supply Chain Hardening Tier 1A:

1. **npm --ignore-scripts Hardening:**
   - Updated `frontend/Dockerfile`: `npm ci` → `npm ci --ignore-scripts`
   - Blocks postinstall/preinstall/install script execution
   - Added `validate-lockfile` Makefile target for testing
   - Frontend build tested and confirmed functional

2. **Validation:**
   - Verified npm ci --ignore-scripts completes successfully
   - Confirmed npm run build produces valid artifacts
   - No legitimate dependencies require lifecycle scripts

### Validation

- ✅ Frontend Dockerfile uses `npm ci --ignore-scripts`
- ✅ make validate-lockfile passes
- ✅ Frontend builds successfully with scripts disabled
- ✅ Production deployment unaffected

### Lessons Learned

- **Least privilege for build tools:** Package managers should not execute arbitrary code by default
- **Defensive defaults:** --ignore-scripts should be the norm, not the exception
- **Proactive hardening:** Mitigate attack classes before specific CVEs emerge

### References

- CanisterWorm Analysis: [Link to security blog/paper]
- Tier 1A Implementation: `docs/specs/supply-chain-hardening-spec-v4.md`
- Commit: SHA of Tier 1A implementation

---

## Incident #3: Python Dependency CVEs (Ongoing Monitoring)

**Date Discovered:** April 2026 (Tier 1D pip-audit scan)  
**Severity:** Low-Medium  
**Status:** ⚠️ Partially Mitigated (Python 3.10+ upgrade required for full remediation)

### Summary

Initial pip-audit scan discovered 6 CVEs across 4 Python packages. One CVE was immediately resolved; 5 require Python 3.10+ upgrade.

### Discovered Vulnerabilities

| Package | CVE | Severity | Status |
|---------|-----|----------|--------|
| fastapi 0.109.0 | PYSEC-2024-38 | Medium | ✅ Fixed (→ 0.109.1) |
| requests 2.32.5 | GHSA-gc5v-m9x4-r6x2 | Low | ⚠️ Accepted (requires Py3.10+) |
| filelock 3.19.1 | GHSA-w853-jp5j-5j7f | Low | ⚠️ Accepted (requires Py3.10+) |
| filelock 3.19.1 | GHSA-qmgc-5h2g-mvrw | Low | ⚠️ Accepted (requires Py3.10+) |
| starlette 0.35.1 | GHSA-f96h-pmfr-66vw | Medium | ⚠️ Accepted (transitive) |
| starlette 0.35.1 | GHSA-2c2j-9gv5-cj73 | Low | ⚠️ Accepted (transitive) |

### Remediation Actions

Implemented as part of Supply Chain Hardening Tier 1D:

1. **pip-audit Integration:**
   - Installed pip-audit>=2.7.0
   - Added `make scan-dependencies` target
   - Integrated into CI quality gate
   - Created `.pip-audit-ignore.yaml` to document accepted risks

2. **Immediate Fix:**
   - ✅ Upgraded fastapi 0.109.0 → 0.109.1 (fixes PYSEC-2024-38)

3. **Accepted Risks (documented):**
   - **requests GHSA-gc5v-m9x4-r6x2:** extract_zipped_paths() not used in app
   - **filelock (2 CVEs):** TOCTOU symlink attacks require local filesystem access (low risk in K8s)
   - **starlette (2 CVEs):** Transitive via fastapi; DoS mitigated by reverse proxy limits

### Ongoing Monitoring

- ✅ pip-audit runs on every CI build
- ✅ Dependabot creates weekly PRs for new Python package versions
- ⏳ TODO: Upgrade to Python 3.10+ to resolve remaining CVEs (tracked in GitHub issue #TBD)

### Lessons Learned

- **Continuous scanning essential:** One-time scans are insufficient; automate in CI
- **Transitive dependencies matter:** Vulnerabilities in sub-dependencies require holistic view
- **Risk-based prioritization:** Not all CVEs are equally exploitable; context matters

### References

- Tier 1D Implementation: `docs/specs/supply-chain-hardening-spec-v4.md`
- Risk Assessment: `.pip-audit-ignore.yaml`
- Tracking Issue: #TBD (Python 3.10+ upgrade)

---

## Response Process

Our standard incident response process:

1. **Detection:** Automated scanning (pip-audit, zizmor, Trivy, TruffleHog) + security advisories
2. **Assessment:** CVE severity, exploitability, affected components
3. **Containment:** Immediate mitigation (disable feature, deploy patch, block traffic)
4. **Remediation:** Permanent fix implementation
5. **Validation:** Automated test suites + manual verification
6. **Documentation:** Update this file, create security advisory
7. **Disclosure:** Coordinated disclosure per SECURITY.md SLA

---

## Improvement Actions

Based on incidents documented above:

- [x] Implement SHA-pinned GitHub Actions (Tier 1B)
- [x] Add npm --ignore-scripts hardening (Tier 1A)
- [x] Integrate pip-audit continuous scanning (Tier 1D)
- [x] Deploy zizmor workflow analysis (Tier 1E)
- [x] Configure Dependabot for all ecosystems (Tier 1C)
- [ ] Upgrade to Python 3.10+ (tracked separately)
- [ ] Implement Tier 1I ServiceAccounts (in progress)
- [ ] Deploy Tier 2A NetworkPolicy egress controls (planned)
- [ ] Add Tier 2B prompt injection sanitizer (planned)

---

**Last Updated:** 2026-04-04  
**Document Owner:** OneRing Security AI Team  
**Review Frequency:** Quarterly or post-incident
