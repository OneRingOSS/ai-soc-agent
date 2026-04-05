# JP Harvey Demo Guide — SecOps Interview
## DTEX Systems | Director Engineering | April 2026

**Audience:** JP Harvey, VP Security & Infrastructure
**Total session time:** 60 min — Demo 30 min | His questions 15 min | Your questions 10 min | Buffer 5 min
**Core message:** You care deeply about security, you act on it systematically, and you would make JP's job easier — not harder. You set the strategy; I make it impossible to violate at the engineering layer.

**Ruby's intel on JP:** "He's not always looking for the most senior person. He looks for the person that cares the most — that has more weight for him in security. He cares about what you're actually doing, not certifications." He appreciates honesty. He will call bullshit if something doesn't ring true. He's been at DTEX through multiple security generations and takes DTEX's own protection seriously — they just published DPRK attribution research.

**The narrative arc:**
> **Act 1** → I've solved the alert noise problem that's costing your SRE team engineering capacity right now
> **Act 2** → I think like an attacker — and built defenses that think like one too
> **Act 3** → When a real threat hit my pipeline, I responded like a security leader AND kept going
> **Closing** → Here's how this serves DTEX's scaling challenge — and here's my role vs. yours

---

## Table of Contents

1. [Pre-Demo Checklist](#1-pre-demo-checklist)
2. [Opening Frame](#2-opening-frame)
3. [Act 1 — AI SOC Agent: Solving the Alert Noise Problem (7 min)](#3-act-1--ai-soc-agent-solving-the-alert-noise-problem)
4. [Act 2 — Adversarial Attack Detection (8 min)](#4-act-2--adversarial-attack-detection)
5. [Act 3 — Trivy Response + Security Practice Progression (12 min)](#5-act-3--trivy-response--security-practice-progression)
6. [Closing Bridge: Scaling DTEX Sustainably (3 min)](#6-closing-bridge-scaling-dtex-sustainably)
7. [Questions to Ask JP](#7-questions-to-ask-jp)
8. [Handling Tough Follow-Up Questions](#8-handling-tough-follow-up-questions)
9. [Key Numbers — Memorize These](#9-key-numbers--memorize-these)
10. [If Things Go Wrong](#10-if-things-go-wrong)

---

## 1. Pre-Demo Checklist

Complete before leaving home. Never troubleshoot live.

### 🔄 **CRITICAL FIRST STEP: Reset Demo State**

**⚠️ MUST RUN BEFORE EVERY DEMO SESSION:**

```bash
# Reset demo state (prevents historical note poisoning false positives)
bash soc-agent-system/k8s/reset-demo-state.sh

# Wait for completion (shows cleanup + pod restart)
# Expected: ✅ Demo State Reset Complete!
```

**What this does:**
- ✅ Clears all threat data from Redis
- ✅ Clears historical incident data
- ✅ Regenerates MockDataStore (fresh random data)
- ✅ Restarts backend pods for clean state
- ✅ Preserves VT cache (3 malware packages for enrichment)

**Why this is critical:**
- Prevents false "HISTORICAL NOTE FABRICATION" detections on clean threats
- Ensures dashboard starts empty (no stale demo data)
- Provides consistent baseline for all demo scenarios

**⚠️ Forgetting this step will cause demo failures!**

---

### System state
- [ ] **Demo state reset** ← **DONE ABOVE - VERIFY!**
- [ ] Backend running: `cd soc-agent-system/backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- [ ] Frontend running: `cd soc-agent-system/frontend && npm run dev`
- [ ] Dashboard loads clean at http://localhost:5173/ (should show "No recent threats")
- [ ] Kind cluster running: `kubectl cluster-info --context kind-soc-agent-cluster`
- [ ] NetworkPolicy applied: `kubectl get networkpolicy -n soc-agent-demo`
- [ ] Sealed Secrets controller running: `kubectl get pods -n kube-system | grep sealed-secrets`
- [ ] OPA Gatekeeper running: `kubectl get pods -n gatekeeper-system`
- [ ] Bad pod spec YAML staged at `/tmp/bad-pod.yaml` (see below)
- [ ] Last GitHub Actions CI run shows SBOM artifact attached

### VS Code tabs staged (left to right)
1. `.github/workflows/ci.yml` — SHA-pinned actions + SBOM step visible
2. `soc-agent-system/Makefile` — quality-gate target
3. `SECURITY-INCIDENT-RESPONSE.md` — incident response doc
4. `k8s/secrets-encryption/README.md` — Sealed Secrets comparison matrix
5. `THREAT_MODEL.md` — open to Section 7 TODO table (updated statuses)

### Terminal tabs staged
- Tab 1: `git log --oneline -20` — pre-typed, not run
- Tab 2: `make quality-gate` — pre-typed, not run
- Tab 3: kubectl OPA rejection + egress commands — pre-typed

### Bad pod spec for OPA live rejection — save as `/tmp/bad-pod.yaml`
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
  namespace: soc-agent-demo
spec:
  automountServiceAccountToken: true    # violates constraint 1
  containers:
  - name: bad-container
    image: nginx:latest
    # no securityContext.seccompProfile  # violates constraint 2
    # no resources.limits                # violates constraint 3
```

### Verify clean state
```bash
curl http://localhost:8000/health               # Expected: healthy
kubectl get pods -n soc-agent-demo              # Expected: all Running
kubectl get networkpolicy -n soc-agent-demo     # Expected: soc-backend-egress listed
kubectl get pods -n gatekeeper-system           # Expected: controller running
kubectl get sealedsecret -n soc-agent-demo      # Expected: sealed secret listed
```

---

## 2. Opening Frame

> Say this BEFORE opening the laptop. Keep it under 2 minutes.

**Script:**
> "Before I open anything — I want to frame what you're about to see, because context matters on two levels.

> First, the technical context: this is my personal development environment, not a staged demo. I had to personally respond to the CERT-EU Trivy advisory last week because Trivy runs in my own CI pipeline. I'm going to walk you through what I built, how I responded to a real threat, and what I kept building over this weekend once the immediate response was done.

> Second — and more important — the business context. DTEX is at a genuine inflection point right now. The Alphabet investment, the ARR trajectory, the TCV growth — that kind of scaling puts enormous pressure on the SRE function. Not just reliability pressure, but customer demand pressure: faster POC environment deployments, faster onboarding, zero tolerance for field issues that damage enterprise credibility at exactly the moment you're trying to land larger deals. The SRE team I'd be inheriting is excellent at what they do today. My job isn't to change what they do — it's to help them do it at 3x the scale without 3x the headcount. Automation, agent-assisted operations, and shifting security left are how you get there. That's the lens for everything I'm about to show you.

> And one more thing I want to be explicit about before we start: the demo is heavy on SecOps tooling. I'm not proposing to define DTEX's security strategy — that's your mandate. What I'm proposing is that the SRE function becomes the execution layer that makes your strategy stick at engineering scale, automatically and deterministically. You set the direction; I make it impossible to accidentally violate at the engineering layer. Let me show you what that looks like in practice."

**Why this framing works:**
- The business context (inflection point, scaling pressure) establishes why the work matters now — not just that it's interesting
- Explicitly naming JP's mandate as separate from yours removes the territorial concern before it forms
- "3x the scale without 3x the headcount" is a CFO-level argument that resonates with a VP who lives with budget constraints
- Sets up the entire demo as evidence of a leadership approach, not a skills showcase

---

## 3. Act 1 — AI SOC Agent: Solving the Alert Noise Problem

**Time:** 7 minutes
**Goal:** Show you've already solved the operational problem DTEX's SRE team has right now — and that the architecture is portable. Establish the asymmetric impact argument early.

### The framing before you open the laptop
> "The problem I built this for is one I lived at Oscilar — and from what Andre shared, it's the same problem your SRE team is dealing with today. Alert volume that exceeds human review capacity. Engineers spending their best hours triaging noise instead of doing the engineering work that moves the platform forward. I measured the impact at Oscilar: analyst workload down 70%, MTTR from about a day to 15-20 minutes. Let me show you how it works."

### What to show
1. Open dashboard at http://localhost:5173/
2. Android Studio emulator — malware APK side-load, privilege escalation
3. SOC dashboard — alert fires with MITRE tagging + false positive score
4. Jaeger trace — 5 agent spans, parallel execution, ~120ms total

### Talking points
> "Five agents run in parallel — 120ms total. Historical Agent pattern-matches past incidents. Priority Agent maps to MITRE ATT&CK and scores severity. Context Agent provides business context. Config Agent validates against policy thresholds. DevOps Agent correlates infrastructure events. The analyst gets a verdict with reasoning — not a raw alert to investigate from scratch."

> "The key architectural insight is the DevOps Agent as the trust anchor. It reads from infrastructure sources that can't be tampered with by external data — that's what makes the system adversarially robust, which I'll come back to in Act 2."

### The SRE bridge — say this before moving on
> "Now — the reason this matters for the Director SRE role specifically. The five-agent architecture I built for security alert triage is directly portable to infrastructure reliability. Noisy monitoring is the same problem in a different domain. Too many alerts, too little signal, engineers who've learned to ignore pages because the false positive rate destroys trust in the system.

> The same multi-agent correlation pattern — one agent on metrics, one on logs, one on deployment events, one on resource utilization, synthesis layer correlating across all four — produces the same result: the on-call engineer gets a prioritized hypothesis rather than a blank dashboard. I'd target a 40-50% reduction in page volume in the first quarter. That's a conservative number based on what I measured in the security domain.

> Here's why that number matters at DTEX's current scale: every hour an SRE engineer spends triaging alert noise is an hour not spent on the automation work that lets the team scale. Cutting page volume by 40-50% doesn't just reduce burnout — it frees the engineering capacity that makes POC environment automation, faster customer onboarding, and the shift-left work all possible. That's the kind of asymmetric leverage that matters at an inflection point.

> And if Andre is already evaluating AWS Agent Core for the AI roadmap, this architecture ports cleanly. The agent logic is plain Python. Two-week migration, contingent on validating Agent Core's per-agent observability fidelity — I'd want to confirm I can get span-level traces equivalent to what Jaeger gives me here before committing."

### Bridge to Act 2
> "The more interesting question is what happens when an attacker targets the AI itself — rather than the systems it's monitoring."

---

## 4. Act 2 — Adversarial Attack Detection

**Time:** 8 minutes
**Goal:** Show you think like an attacker. This maps directly to DTEX's insider risk detection philosophy — and demonstrates the security depth JP is evaluating.

### Context before running
> "I'm modeling MITRE ATT&CK TA0005 — Defense Evasion. A trusted insider with SIEM write access poisons the AI's historical data to suppress detection of their own activity. This is Rajan's lethal trifecta applied to a non-human actor — the AI agent has sensitive data access, external API communication capability, and untrusted content exposure. I'll show the attack working first, then the defense catching it."

### Act 2a — Attack succeeds (run first)
```bash
curl -X POST http://localhost:8000/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_bypass", "adversarial_detector_enabled": false}'
```
> "18 fabricated Jira tickets pre-injected, all marking this SQL injection signature as a known false positive. The AI sees 65% FP score. Analyst gets a low-priority verdict and moves on. Attack succeeds — the system has been trained to ignore this attacker.

> Why can't rule-based systems catch this? Every individual field is technically valid. Service accounts can resolve tickets. Fast resolutions happen. Generic language is normal. Only the combination of six indicators — identical structure, service account authorship, 3-minute resolutions for complex threats, no JIRA cross-references, generic team names, exactly one note per day for 18 days — reveals the fabrication. That cross-field semantic reasoning requires an LLM."

### Act 2b — Defense catches it (run second)
```bash
curl -X POST http://localhost:8000/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_catch", "adversarial_detector_enabled": true}'
```
> "Same attack, same poisoned data, detector enabled. Red badge fires. Notice the FP score is still 65% — the notes successfully tricked the FP analyzer. That's proof the attack was working. But the adversarial detector overrides it: 'This FP score is unreliable — investigate anyway.'

> The 40-second deep analysis is gated on inter-agent disagreement above a threshold — normal cases still run at 120ms. The performance tradeoff is explicit and documented."

### Bridge to Act 3
> "That's the adversarial threat inside the application layer. Now let me show you the supply chain threat that hit my actual CI pipeline last week — and what I did about it, both immediately and in the days that followed."

---

## 5. Act 3 — Trivy Response + Security Practice Progression

**Time:** 12 minutes
**Goal:** Demonstrate that you treat security as a living practice — response, hardening, enforcement, compliance evidence. Show the leadership pattern, not just the technical output.

### Phase 1: The incident (3 min)

> "I run Trivy v0.69.1 in my CI pipeline. When the CERT-EU advisory dropped on March 27th, I had to personally respond."

**Walk the attack chain — 90 seconds, tell it as a story:**
> "Five phases. Attacker gets valid Aqua Security credentials. Force-pushes malicious commit to 75 of 76 Trivy version tags — including mine. Malicious binary reads CI runner secrets from `/proc/pid/mem` — raw memory access, no file system artifacts. Exfiltrates via HTTPS to `scan.aquasecurtiy.org` — transposed letters, domain registered days before the attack. CanisterWorm then spreads to 47 downstream npm packages via postinstall hooks.

> The thing that makes this class dangerous: zero CVEs generated. Dependabot is completely clean. The detection surface is runtime behavior, not version strings — which is exactly why behavioral monitoring matters more than version databases for this threat class."

**Show the immediate response — VS Code, 90 seconds:**

- **Tab 1 — SHA-pinned workflow:**
> "Before: `actions/checkout@v4` — mutable tag, can be force-pushed. After: 40-character commit SHA. Cryptographically immutable. The exact change that would have protected Aqua Security's own pipeline."

- **Tab 2 — run `make quality-gate` live:**
```bash
cd soc-agent-system && make quality-gate
```
> "SHA pinning, `--ignore-scripts` blocking postinstall hooks, TruffleHog secret scanning, pip-audit, Trivy image scan — 8 automated gates on every commit, about 100 seconds total. Walk through each check as it passes. This is the security baseline I'd establish for DTEX's CI pipelines in the first 30 days — not a proposal, a working implementation I can demonstrate."

- **Tab 3 — `SECURITY-INCIDENT-RESPONSE.md`:**
> "Documented. Exposure assessment, which vectors applied to my pipeline, what changed, why. In a team environment this is how you close the loop — a structured record that the next engineer reads and trusts, rather than institutional knowledge that lives only in someone's head."

### Phase 2: The pivot question — show git log

```bash
git log --oneline -20
```
> "Here's the full picture. These commits are the Trivy response — Friday. But look at Saturday and Sunday. The incident was a forcing function. After the immediate response, I asked myself one question: how much of my security posture is documented intent versus enforced reality? That question is what separates a one-time incident response from a security practice. Let me show you what I found — and I want to frame this explicitly before I do."

**Positioning statement — say this before the OPA demo:**
> "What I'm about to show you isn't me defining a SecOps strategy. That's your mandate and I wouldn't presume to do it for you. What I'm doing is taking security principles — zero-trust, least-privilege, supply chain integrity — and making them executable at the engineering layer so enforcement is automatic. You define the policy. I make the infrastructure enforce it so no individual engineer's judgment call can override it. The strategy stays with you. The automation that makes it stick is what I bring. With that framing — let me show you the one thing that matters most."

### Phase 3: From response to enforcement (5 min)

**OPA Gatekeeper — the enforcement gate (3 min):**
```bash
# Show Gatekeeper running
kubectl get pods -n gatekeeper-system

# Show the three active constraints
kubectl get constraints

# Live rejection
kubectl apply -f /tmp/bad-pod.yaml
```
> "Admission denied. Three constraints: no auto-mounted ServiceAccount tokens, seccomp RuntimeDefault required on every pod, resource limits required on every container. The cluster refuses non-compliant specs at the API server level before scheduling. This is the key insight: everything in a YAML file is configuration — a misconfigured deployment or a rushed engineer can override it. An admission gate cannot be overridden accidentally. It's the difference between a security guideline and a security control.

> And I'll draw the parallel directly to DTEX's product: InTERCEPT is a policy enforcement engine for human behavior. What I just showed you is the same philosophy applied to infrastructure behavior. Enforce at the gate. Don't trust the self-attestation."

**Sealed Secrets — 60 seconds:**
```bash
kubectl get sealedsecret -n soc-agent-demo
```
> "Secret management — evaluated three approaches against each other in a comparison matrix. Chose Sealed Secrets because it solves the GitOps problem the others don't: you can safely commit the encrypted SealedSecret to Git because the private key never leaves the cluster. Auto-rotates every 30 days. In production on AWS I'd pair it with KMS envelope encryption for etcd-at-rest — documented tradeoff, explicit production trigger."

**SBOM + Compliance evidence — 60 seconds:**

*Open GitHub Actions last run in browser, point at the Artifacts section:*
> "Compliance evidence layer. Every CI run automatically produces a CycloneDX SBOM — Syft generates it, Grype scans it against an independent vulnerability database separate from Trivy's feed. SLSA Level 1 provenance attests who built it, from what commit, on what runner. Your compliance team pulls these artifacts from CI directly. No engineering tickets, no manual evidence collection, no audit prep scramble. That's the answer to the manual audit burden problem — built into the pipeline from the start, not bolted on before an audit."

### Phase 4: The threat model as leadership artifact (1 min)

**Open Tab 5: THREAT_MODEL.md — Section 7 TODO table:**
> "Last thing — not a feature, a process artifact. This threat model has been updated this weekend to reflect every change. Statuses moved from Planned to Implemented, code evidence linked. Current overall posture: MEDIUM, not LOW. Five residual gaps are documented with explicit effort estimates and production trigger criteria.

> I'm not claiming LOW risk. I'm claiming I know exactly where the residual risk is, why I've accepted it at this stage, and what closes it. A security leader who tells you their system is fully hardened before completing P1 controls isn't looking hard enough — or isn't being honest. I'd rather show you a documented MEDIUM with a clear, credible path to LOW."

---

## 6. Closing Bridge: Scaling DTEX Sustainably

**Time:** 3 minutes — deliver this with conviction, it's your leadership pitch

> "Let me close with what I'd actually do — and I want to be explicit about the 'why now' before I get to the 'what.'

> DTEX is at an inflection point that most companies only get one shot at. The Alphabet investment, the ARR trajectory, the TCV growth — you're transitioning from a company that wins deals to a company that has to deliver at enterprise scale, repeatedly and predictably. At that inflection, the SRE team's current model — service-heavy, reactive, dependent on individual expertise — will break before the product does. Not because the team isn't good. Because the model doesn't scale.

> The answer isn't hiring more SREs. It's making the existing team asymmetrically more capable through automation and agent-assisted operations. Here's what I'd focus on:

> **First — the monitoring noise problem, in the first 30 days.** The five-agent alert triage architecture I showed you in Act 1 is directly applicable to the infrastructure reliability domain. I'd target a 40-50% reduction in on-call page volume in the first quarter. That single change frees the engineering capacity that makes everything else possible — faster POC environment deployments, faster customer onboarding, the shift-left automation work.

> **Second — embedding the security practice I demonstrated today as a team-wide standard.** OPA Gatekeeper policies as admission gates for all new services — not manual YAML review, automatic enforcement. SBOM and provenance generation in every CI pipeline — not just mine. A threat model template that every new service produces before its first deployment. That's how you build a security-first engineering culture without making security a bottleneck. You embed it in the process so it happens automatically.

> **Third — the longer-term vision, which I'd want to build collaboratively with you.** If we're building AI-assisted SRE operations on Agent Core, the same agent coordination pattern naturally extends to security signal correlation. Egress violations, admission gate failures, SBOM deltas between releases — all of these are signals that belong in the same reasoning layer as infrastructure metrics. That's where AI-native SecOps starts to look fundamentally different from traditional SIEM. And DTEX, with both the product expertise and the platform investment, is uniquely positioned to lead that.

> But I want to be clear about what I'm offering and what I'm not. I'm not proposing to own DTEX's security strategy — that's your mandate and I'd be a poor fit if I tried to define it for you. What I'm offering is an SRE function that executes your security strategy automatically, at engineering scale, without requiring your team to audit every deployment. You set the direction. I make it stick. That's the partnership I'd want to build with you."

---

## 7. Questions to Ask JP

Ask after the demo — before he pivots to behavioral questions.

**Q1 — The monitoring noise problem (highest value, reference Andre):**
> "Andre mentioned the SRE team is losing significant bandwidth to alert noise in the current monitoring setup. From your perspective as the security leader — is that problem compounded on the security signal side as well? Are security events going uninvestigated because they're buried in operational noise, or are those two streams reasonably separated today?"

**Q2 — The partnership question (most important for cultural fit):**
> "How do you currently think about the boundary between the security engineering mandate and the SRE mandate at DTEX? I want to understand where you'd want the SRE leader to take ownership versus where you'd want to stay in the driver's seat — because getting that boundary right from day one matters a lot for how effective we'd be together."

**Q3 — CI/CD security maturity:**
> "Given the threat research DTEX publishes — the DPRK attribution work, the level of adversary attention your company attracts — how mature is behavioral monitoring on your own build and deployment infrastructure today? Is CI/CD security an active engineering priority or has it been deprioritized against product delivery?"

**Q4 — The AI agent insider risk surface:**
> "As Ai3 scales and you add agentic SOC capabilities — how are you thinking about the insider risk surface the agents themselves create? Rajan's lethal trifecta was designed for human insiders, but your own Ai3 agents satisfy all three properties simultaneously: customer SIEM telemetry access, external OpenAI API calls, and untrusted analyst note ingestion. Is mitigating that at the infrastructure level on the roadmap, or still conceptual?"

**Q5 — His personal security lens:**
> "You've been in security through pre-cloud, cloud-native, and now AI-native generations. What's the threat class you think is most underestimated right now — is it the AI agent attack surface, or something else entirely?"

---

## 8. Handling Tough Follow-Up Questions

### "The JD is heavy on SRE — you seem more AI/product focused"
> "SRE at a startup isn't a pure infra discipline — at F5 and Oscilar I owned the SRE function because you build it and you run it. The operational fundamentals are there: 99.99% uptime for the top 5 US banks over four years, on-call reduced from 8-10 pages a week to 2-3 after runbook discipline. The AI work I showed you today is SRE work — analyst burnout was a reliability problem, the adversarial detector was an availability problem. The alert noise your SRE team is dealing with right now is exactly the kind of operational problem I've solved before, and I'd make it the first thing I address."

### "You're showing a lot of SecOps work — are you trying to own that agenda?"
> "No — and I want to be direct about that. Everything I showed you is in service of making your security strategy executable at the engineering layer, not defining it. OPA Gatekeeper enforces the policies you set. The SBOM pipeline produces the compliance evidence your team needs. The threat model tracks the posture against the standard you'd define for production. I build the execution layer. You own the strategy. That's the right division of labor and I'd push back hard if I ever felt that line was blurring the wrong way."

### "Is Sealed Secrets sufficient for production — what about etcd encryption?"
> "Sealed Secrets closes the primary real-world exposure vector — secrets in Git in plaintext, which is where the majority of K8s secret leaks actually originate. In production on AWS I'd pair it with KMS envelope encryption for etcd-at-rest. I didn't implement etcd encryption here because Kind's control plane makes it a cluster rebuild exercise. The decision is explicit in the threat model — Git exposure addressed, etcd layer is the production trigger item."

### "What does OPA add beyond what's in the YAML specs?"
> "It changes the control from configuration to enforcement. A misconfigured deployment or a time-pressured engineer can override YAML — the cluster accepts it without complaint. OPA means the cluster refuses non-compliant specs at admission time, and the rejection tells the engineer exactly which policy fired and why. It also protects every future workload added to the namespace — not just today's pods, but every service the team adds going forward. That matters especially as the team scales and you can't personally review every deployment."

### "How would you detect if the prompt injection sanitizer was bypassed?"
> "Two ways. First, an LLM output scanning layer — run responses through a classifier before persistence, flagging env var patterns, IP addresses, Base64 blobs in unexpected positions. Second, the adversarial detector does cross-agent semantic validation independent of the sanitizer — an unusually long or structured Historical Agent response triggers the contradiction check regardless of what the input layer saw. Bypassing the input sanitizer doesn't bypass the output semantic layer."

### "What about DNS rebinding against your NetworkPolicy?"
> "Correct — FQDN-based NetworkPolicy has a rebinding gap. The attacker registers a domain resolving to a legitimate IP initially, then rebinds after TTL expiry. Defense at the policy layer is certificate pinning at an egress proxy — the typosquatted domain won't have the same CA chain as the real vendor. At the application layer, outbound URL allowlisting in the agent code before any HTTP call based on external input. It's in the threat model as P2 with a production trigger and a 3-5 day effort estimate."

### "What would you do in the first 90 days?"
> "Days 1-30: listening tour — 1:1s with every engineer, no proposals. I track after-hours commits and PTO as burn signals. Days 31-60: one quick win in each area Ruby described — reliability, AI velocity, team health. For reliability, the monitoring noise problem is the fastest path to visible impact. Days 61-90: present a 6-month roadmap prioritized against what I heard in month one, including where the SRE and SecOps boundary sits and what the right handoff model looks like with your team. The mistake I've seen new leaders make is proposing solutions before diagnosing the actual pain — and proposing org structures before building trust."

### "Your project uses mock data — is the adversarial detection production-validated?"
> "The adversarial detection and multi-agent coordination are production-validated at Oscilar — different stack, same architectural patterns. The open source project is a clean-room reimplementation I can discuss publicly without NDA concerns. The production numbers — 70% analyst workload reduction, MTTR from a day to 15-20 minutes — came from real customer data across 30 customers representing 10% of ARR."

### "You haven't built with AWS Agent Core — how fast can you get up to speed?"
> "Two weeks to port the LangGraph implementation — the agent logic is plain Python that runs on any runtime. The question I'd want to answer first is observability fidelity: can I get per-agent spans equivalent to these Jaeger traces in Agent Core's CloudWatch model? That determines whether I can debug which specific agent produced a bad hypothesis. If yes, it's a straightforward migration. If CloudWatch only surfaces aggregate pipeline latency, I'd evaluate the tradeoff before committing."

---

## 9. Key Numbers — Memorize These

Do not read from notes. These must be conversational.

| Claim | Number | Context |
|---|---|---|
| Analyst workload reduction | 70% | Oscilar production deployment |
| MTTR improvement | ~1 day → 15-20 min | Oscilar, 30 customers |
| F5 uptime | 99.99% for 4 years | Top 5 US banks |
| On-call improvement | 8-10 pages/week → 2-3 | After runbook discipline at Shape |
| F5 event volume | 4B security events/week | Shape Security scale |
| Oscilar scale | 30 customers, 10% of ARR | Production deployment |
| Demo test coverage | 47 automated tests, 100% pass | Current repo |
| CI pipeline runtime | ~100 seconds | 8 automated security gates |
| Trivy poisoned tags | 75 of 76 version tags | CERT-EU advisory |
| Trivy downstream spread | 47 npm packages | CanisterWorm |
| Adversarial detector — normal | ~120ms | Gated on inter-agent disagreement |
| Adversarial detector — deep | ~40 seconds | Full corpus analysis |
| Fabricated notes in demo | 18 Jira tickets | Note poisoning scenario |
| OPA constraints enforced | 3 policies | ServiceAccount, seccomp, resource limits |
| Sealed Secrets key rotation | Every 30 days | Automated |
| SRE MTTR target (K8s) | 40-50% reduction | Conservative from security domain analog |
| DTEX ARR | ~$100M | Current scale |
| DTEX TCV growth | ~200% | Inflection point context |

---

## 10. If Things Go Wrong

| Problem | Recovery |
|---|---|
| Backend won't start | `lsof -ti:8000 \| xargs kill -9` then restart. Show Grafana screenshots instead. |
| Frontend blank | Open http://localhost:8000/api/threats directly. "Let me show you the API response — the dashboard is a visualization layer on top of this." |
| Android emulator not showing | Skip it. "The emulator shows the endpoint compromise — let me jump straight to the detection output which is the interesting part." |
| Adversarial demo not firing | Check backend logs. Fall back to THREAT_MODEL.md adversarial section. "Let me walk you through the detection logic — the code evidence is linked here." |
| OPA rejection doesn't fire | Show the ConstraintTemplate YAML. "The policy spec is here — Kind's admission webhook has timing quirks on fresh clusters. What the webhook does is intercept every pod spec at the API server, evaluate it against these Rego policies, and return a structured rejection if any constraint fires. The enforcement model is the point — not the specific implementation." |
| Sealed Secrets not showing | Show the encrypted YAML in Git. "Here's what lives in version control — a ciphertext blob. The controller in the cluster holds the private key. The property that matters is what's safe to commit." |
| NetworkPolicy timeout not working | Show NetworkPolicy YAML. "Kind's CNI enforces differently than production Cilium. Let me show you the seccomp profile that closes the same attack class at the pod level — defense-in-depth means NetworkPolicy and seccomp address the same attack vector from two independent layers." |
| SBOM not visible in CI artifacts | Show the CI workflow YAML syft step. "The step is here — runs on every push. Let me pull up the last green run." |
| make quality-gate fails | If minor: fix it live — demonstrates debugging discipline. If severe: run individual checks: `make lint`, `make test`, `make scan-secrets`. Each is a demoable gate. |
| JP cuts demo short | "What would be most useful — the security controls, the agent architecture, or the monitoring noise problem I mentioned at the start?" Let him drive. |
| JP seems disengaged during agent demo | Skip to Act 3 immediately. "Let me jump to the part most directly relevant to your world — the supply chain incident response and the enforcement layer I built afterward." |
| JP challenges the role boundary directly | "You're right to push on that. My view: you own the security strategy and standards. My job is to make the engineering organization execute them automatically — so your team is never in the position of chasing engineering for compliance evidence or hoping engineers remembered the security policy. The SRE function should reduce your operational burden, not create more of it." |

---

*Demo guide v5 — April 5, 2026*
*Audience: JP Harvey, VP Security & Infrastructure, DTEX Systems*

*Key changes from v4:*
*— Added business inflection point context to opening frame (Alphabet investment, ARR, TCV growth, scaling pressure)*
*— Added explicit role boundary positioning in opening frame and before the OPA demo*
*— Added asymmetric impact argument to Act 1 SRE bridge*
*— Added AWS Agent Core forward roadmap connection in Act 1*
*— Restructured closing bridge to lead with "why now" inflection argument before the three deliverables*
*— Added Q2 on partnership boundary — most important cultural fit question*
*— Added failure recovery for JP challenging the role boundary directly*
*— Added DTEX ARR and TCV numbers to key numbers table*
