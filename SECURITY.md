# Security Policy

## Reporting a Vulnerability

The OneRing Security AI team takes security vulnerabilities seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:
- **Email:** security@oneringsecurityai.com
- **Subject:** [SECURITY] Brief description of the vulnerability

### What to Include

When reporting a vulnerability, please include:

1. **Type of vulnerability** (e.g., injection, authentication bypass, privilege escalation)
2. **Affected component** (e.g., backend API, frontend, adversarial detector, K8s deployment)
3. **Steps to reproduce** (detailed PoC if possible)
4. **Impact assessment** (what an attacker could achieve)
5. **Suggested remediation** (if you have recommendations)
6. **Your contact information** for follow-up

### What to Expect

- **Acknowledgment:** We will acknowledge receipt within **48 hours**
- **Initial assessment:** We will provide an initial assessment within **5 business days**
- **Status updates:** We will keep you informed as we investigate and remediate
- **Fix timeline:** Critical vulnerabilities will be addressed within **30 days** (severity-dependent)
- **Public disclosure:** We follow coordinated disclosure practices and will work with you on timing

### Our Commitment

- We will not take legal action against security researchers who report vulnerabilities in good faith
- We will credit researchers in our security advisories (unless anonymity is preferred)
- We will provide regular updates on remediation progress

### Scope

**In scope:**
- AI SOC Agent backend (FastAPI, Python)
- Frontend (React, TypeScript)
- Kubernetes manifests and Helm charts
- GitHub Actions CI/CD workflows
- Adversarial detection system
- LLM prompt injection vulnerabilities
- Historical note poisoning attacks
- Supply chain vulnerabilities

**Out of scope:**
- Third-party dependencies (report directly to the upstream project)
- Social engineering attacks
- Physical attacks
- Denial of service via resource exhaustion (unless exploitable logic flaw)

### Security Advisories

Published security advisories can be found at:
- https://github.com/OneRingOSS/ai-soc-agent/security/advisories

### Security Features

This project implements:
- **Supply chain hardening:** npm --ignore-scripts, SHA-pinned actions, pip-audit, zizmor
- **Secret scanning:** TruffleHog in CI pipeline
- **Dependency scanning:** Dependabot automated updates (pip, npm, GitHub Actions)
- **Image scanning:** Trivy for Docker images
- **Adversarial detection:** LLM manipulation detection (prompt injection, historical note poisoning)
- **Least-privilege:** Kubernetes ServiceAccounts with automountServiceAccountToken: false
- **Network isolation:** NetworkPolicy egress controls (blocks AWS IMDS, allows OpenAI/VirusTotal)
- **Input sanitization:** Prompt injection pattern detection

### Security Response Timeline (SLA)

| Severity | First Response | Remediation Target | Public Disclosure |
|----------|---------------|-------------------|-------------------|
| **Critical** | 24 hours | 7 days | 30 days post-fix |
| **High** | 48 hours | 14 days | 60 days post-fix |
| **Medium** | 5 business days | 30 days | 90 days post-fix |
| **Low** | 10 business days | Best effort | Discretionary |

### Past Incidents

See [SECURITY-INCIDENT-RESPONSE.md](./SECURITY-INCIDENT-RESPONSE.md) for documented security incidents and responses.

### Bug Bounty

We currently do not offer a bug bounty program, but we deeply appreciate responsible disclosure and will publicly acknowledge researchers who help improve our security.

### Contact

For security-related questions (not vulnerability reports):
- **General security:** security@oneringsecurityai.com
- **GitHub Security Tab:** https://github.com/OneRingOSS/ai-soc-agent/security

---

**Thank you for helping keep OneRing Security AI and our users safe!**
