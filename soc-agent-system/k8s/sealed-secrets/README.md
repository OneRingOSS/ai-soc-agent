# Sealed Secrets - Decision Matrix & Implementation

## Executive Summary

**Chosen Solution:** Bitnami Sealed Secrets  
**Primary Reason:** GitOps-compatible secret encryption with cluster-scoped private keys

---

## Comparison Matrix

| Criterion | Sealed Secrets | External Secrets Operator | Native K8s Secrets + etcd Encryption |
|-----------|----------------|---------------------------|--------------------------------------|
| **GitOps Safe** | ✅ **YES** - Encrypted secrets committable to Git | ⚠️ **PARTIAL** - Config only, not actual secrets | ❌ **NO** - Plaintext in Git is breach risk |
| **Private Key Location** | ✅ **Cluster-scoped** - Never leaves cluster | ⚠️ **External** - AWS/GCP/Vault | ⚠️ **etcd** - Requires KMS for true encryption |
| **Zero-Trust Posture** | ✅ **Strong** - Asymmetric encryption | ✅ **Strong** - Centralized secret store | ❌ **Weak** - Base64 encoding not encryption |
| **Rotation** | ✅ **Automatic** - Every 30 days | ✅ **Policy-driven** - External store controls | ⚠️ **Manual** - No built-in rotation |
| **Audit Trail** | ✅ **Git commits** - Full change history | ✅ **External audit log** - Centralized | ⚠️ **K8s audit log** - Not secret-specific |
| **Operational Complexity** | ✅ **Low** - Single controller pod | ⚠️ **Medium** - External dependency + sync | ✅ **None** - Native K8s |
| **Multi-Cluster** | ⚠️ **Per-cluster keys** - Requires re-encryption | ✅ **Shared store** - Single source of truth | ❌ **No** - Cluster-local only |
| **Air-Gapped Support** | ✅ **YES** - Self-contained | ❌ **NO** - Requires external connectivity | ✅ **YES** - Fully offline |
| **Cost** | ✅ **$0** - Open source | ⚠️ **Variable** - Vault/AWS license costs | ✅ **$0** - Native |
| **Production Readiness** | ✅ **Mature** - 7+ years, CNCF Sandbox | ✅ **Mature** - Wide adoption | ⚠️ **Partial** - Needs KMS integration |

---

## Decision Rationale

### Why Sealed Secrets Won

1. **GitOps Workflow Alignment** ✅
   - The encrypted `SealedSecret` YAML can be safely committed to Git
   - Solves the #1 K8s secret leak vector (plaintext secrets in repos)
   - Development workflow: seal secret locally → commit → deploy

2. **Zero External Dependencies** ✅
   - No AWS KMS, no Vault, no GCP Secret Manager required
   - Self-contained within the cluster
   - Reduces attack surface and operational complexity

3. **Audit Trail Built-In** ✅
   - Every secret change is a Git commit
   - Full history, blame, and rollback capability
   - Compliance teams love Git-based auditability

4. **Automatic Key Rotation** ✅
   - Controller rotates encryption keys every 30 days
   - Old keys retained for decryption (grace period)
   - No manual intervention required

### Why External Secrets Operator Didn't Win

**Pros:**
- Centralized secret management (good for multi-cluster)
- Integration with enterprise secret stores (Vault, AWS Secrets Manager)
- Secret sync automation

**Cons:**
- ❌ **Doesn't solve the Git problem** - Configs still reference external secrets, doesn't encrypt them
- ❌ **External dependency** - Vault/AWS/GCP outage breaks secret sync
- ❌ **Operational complexity** - Another system to maintain
- ❌ **Not GitOps-native** - Secrets live outside version control

### Why Native K8s Secrets Didn't Win

**Pros:**
- Zero additional components
- Universal support

**Cons:**
- ❌ **Base64 is not encryption** - Trivially decodable
- ❌ **Plaintext in Git** - The primary breach vector
- ❌ **No audit trail** - Can't track who changed what secret when
- ❌ **etcd encryption requires KMS** - Adds complexity back

---

## Production Considerations

### Current Implementation (Demo/Dev)

```yaml
Sealed Secrets controller: v0.24.5
Key rotation: Every 30 days (automatic)
Scope: Cluster-wide (single private key)
Backup: Key exported and stored securely offline
```

### Production Enhancements (AWS Deployment)

**Add:**
1. **etcd Encryption at Rest** - KMS envelope encryption for defense-in-depth
2. **Key Backup to S3** - Encrypted controller key backup for disaster recovery
3. **Multi-Cluster Strategy** - Shared or per-cluster keys (decision needed)
4. **Secret Scanning** - TruffleHog pre-commit hook to catch accidental plaintext commits

**Why not implemented here:**
- Kind cluster doesn't support etcd encryption without full rebuild
- Documented in THREAT_MODEL.md as production trigger item

---

## Implementation Guide

### 1. Install Sealed Secrets Controller

```bash
bash soc-agent-system/k8s/sealed-secrets/deploy-sealed-secrets.sh
```

This installs:
- Controller deployment (kube-system namespace)
- CRD (sealedsecrets.bitnami.com)
- RBAC roles and service account

### 2. Install kubeseal CLI

```bash
brew install kubeseal
```

### 3. Create and Seal a Secret

```bash
# Create plaintext secret (dry-run, not applied)
kubectl create secret generic my-secret \
    --from-literal=api-key=supersecret \
    --namespace=my-namespace \
    --dry-run=client -o yaml \
    > plaintext-secret.yaml

# Encrypt it with cluster's public key
kubeseal -o yaml < plaintext-secret.yaml > sealed-secret.yaml

# Commit the encrypted version to Git
git add sealed-secret.yaml
git commit -m "Add API key (encrypted)"

# Deploy to cluster
kubectl apply -f sealed-secret.yaml
```

### 4. Verify Secret Was Unsealed

```bash
kubectl get sealedsecret my-secret -n my-namespace
kubectl get secret my-secret -n my-namespace
```

The controller automatically decrypts `SealedSecret` → `Secret`.

---

## Security Properties

| Property | Implementation |
|----------|----------------|
| **Encryption Algorithm** | AES-256-GCM (authenticated encryption) |
| **Key Size** | 4096-bit RSA |
| **Scope** | Cluster-wide or namespace-scoped |
| **Private Key Storage** | Kubernetes Secret in kube-system |
| **Public Key Distribution** | Fetched from controller service |
| **Replay Protection** | Namespace + name binding |
| **Rotation** | Automatic every 30 days |

---

## Demo Artifacts

**Files:**
- `deploy-sealed-secrets.sh` - Automated deployment
- `demo-sealed-secret.yaml` - Encrypted secret (safe to commit)
- `README.md` - This document

**Validation:**
```bash
kubectl get sealedsecret -n soc-agent-demo
# Expected: demo-api-key listed

kubectl get secret demo-api-key -n soc-agent-demo
# Expected: Unsealed secret exists with 2 data keys
```

---

## References

- [Sealed Secrets Official Docs](https://github.com/bitnami-labs/sealed-secrets)
- [CNCF Sandbox Project](https://www.cncf.io/projects/sealed-secrets/)
- [GitOps Workflow Guide](https://github.com/bitnami-labs/sealed-secrets#usage)

---

**Decision Date:** April 6, 2026  
**Implemented By:** SRE/SecOps Demo  
**Status:** ✅ Production-ready for Git-based workflows
