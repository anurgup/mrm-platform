# MRM Platform Demo Walkthrough

Audience: NBFC CRO/CCO (compliance officer)
Setup: running locally, `uvicorn app.main:app --reload`
Time: 10–12 minutes, pure curl (no UI)

The story: three models in an NBFC. Show risk scoring, control checking, and
RBI-anchored governance decisions — not marketing, real governance.

Every number and response shape below was run against the real server and
verified, not guessed. Re-run it yourself before presenting — behavior can
drift as the platform grows.

====================================================
## SETUP (one-time, before demo)

```bash
cd backend
rm -f mrm.db
alembic upgrade head
uvicorn app.main:app --reload
# In another terminal, run the demo below
```

====================================================
## Scene 1: Register three models

Narrator: "We have three AI models in production. Let me register them."

**Model 1: Credit Underwriting Scorecard v3** (internal ML model, all controls in place)

```bash
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Credit Underwriting Scorecard v3",
    "business_function": "Loan Underwriting",
    "model_type": "Machine Learning",
    "deployment_stage": "Production",
    "data_classification": "Restricted",
    "vendor_dependency": "Internal",
    "business_owner": "Anuj Sharma",
    "risk_owner": "Priya Verma",
    "technical_owner": "Vikram Singh",
    "has_documentation": true,
    "has_independent_validation": true,
    "has_explainability": true,
    "has_drift_monitoring": true,
    "has_human_override": true,
    "has_audit_logging": true,
    "has_deployment_approval": true
  }'
```
Response: `201`, model saved with `id=1`.

**Model 2: Fraud Detection Vendor API** (external vendor, missing four controls)

```bash
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Fraud Detection Vendor API",
    "business_function": "Fraud Detection",
    "model_type": "Third Party AI API",
    "deployment_stage": "Production",
    "data_classification": "Restricted",
    "vendor_dependency": "External Vendor",
    "vendor_name": "FraudShield Inc",
    "business_owner": "Ravinder Patel",
    "risk_owner": "Neha Kapoor",
    "technical_owner": "Amit Kumar",
    "has_documentation": true,
    "has_independent_validation": false,
    "has_explainability": false,
    "has_drift_monitoring": false,
    "has_human_override": true,
    "has_audit_logging": true,
    "has_deployment_approval": false
  }'
```
Response: `201`, model saved with `id=2`.

**Model 3: Customer Support Assistant** (GenAI, partial controls)

```bash
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support Assistant",
    "business_function": "Customer Service",
    "model_type": "Generative AI",
    "deployment_stage": "Testing",
    "data_classification": "Internal",
    "vendor_dependency": "External Vendor",
    "vendor_name": "Anthropic",
    "llm_provider": "Anthropic",
    "llm_model_name": "Claude 3.5 Sonnet",
    "business_owner": "Rajesh Menon",
    "risk_owner": "Divya Iyer",
    "technical_owner": "Suresh Desai",
    "has_documentation": true,
    "has_independent_validation": false,
    "has_explainability": true,
    "has_drift_monitoring": false,
    "has_human_override": true,
    "has_audit_logging": true,
    "has_deployment_approval": false
  }'
```
Response: `201`, model saved with `id=3`.

====================================================
## Scene 2: Assess risk (deterministic scoring)

Narrator: "Now we assess risk. The score is computed from business function,
model type, data sensitivity, and vendor dependence — deterministically, the
same inputs always produce the same score, and every point is explained."

**Model 1 — real result: score 60, MEDIUM**

```bash
curl -X POST http://localhost:8000/models/1/assess
```
```json
{
  "risk_score": 60,
  "risk_category": "MEDIUM",
  "factor_breakdown": [
    {"key": "business_impact_financial", "reason": "financial decision", "points": 30},
    {"key": "data_sensitivity_financial_customer", "reason": "financial/customer data", "points": 20},
    {"key": "complexity_traditional_ml", "reason": "traditional ML complexity", "points": 10}
  ],
  "assessment_reason": "Score 60 (MEDIUM): financial decision (+30), financial/customer data (+20), traditional ML complexity (+10)"
}
```
CRO reads: "Medium risk — it's a financial decision on sensitive data, but a
well-understood ML model, internally built, not a black box."

**Model 2 — real result: score 70, HIGH**

```bash
curl -X POST http://localhost:8000/models/2/assess
```
```json
{
  "risk_score": 70,
  "risk_category": "HIGH",
  "factor_breakdown": [
    {"key": "business_impact_financial", "reason": "financial decision", "points": 30},
    {"key": "data_sensitivity_financial_customer", "reason": "financial/customer data", "points": 20},
    {"key": "vendor_blackbox_external", "reason": "black-box external model", "points": 20}
  ],
  "assessment_reason": "Score 70 (HIGH): financial decision (+30), financial/customer data (+20), black-box external model (+20)"
}
```
CRO reads: "High risk — it's a financial decision, it's external, it's opaque.
This model needs serious scrutiny." (Note: a third-party API contributes
nothing extra for "complexity" on top of the vendor flag — the platform
doesn't double-count opacity.)

**Model 3 — real result: score 45, MEDIUM**

```bash
curl -X POST http://localhost:8000/models/3/assess
```
```json
{
  "risk_score": 45,
  "risk_category": "MEDIUM",
  "factor_breakdown": [
    {"key": "business_impact_customer_facing", "reason": "customer facing", "points": 25},
    {"key": "complexity_llm_genai", "reason": "LLM complexity", "points": 20}
  ],
  "assessment_reason": "Score 45 (MEDIUM): customer facing (+25), LLM complexity (+20)"
}
```
CRO reads: "Medium risk. Customer-facing, so it matters. Generative, so it
can hallucinate. But internal data only, no financial exposure."

====================================================
## Scene 3: Check controls (tier-based requirements)

Narrator: "Now the system checks which controls are mandatory for each
model's risk tier, and what's missing. HIGH tier requires all 9 governance
controls; MEDIUM requires 4; LOW requires 2."

**Model 1 — real result: MEDIUM tier, 4/4 passed, PASS**

```bash
curl -X POST http://localhost:8000/models/1/assess-controls
```
```json
{
  "control_assessment": {
    "risk_category": "MEDIUM",
    "controls_required": 4,
    "controls_passed": 4,
    "overall_status": "PASS"
  },
  "findings": []
}
```
CRO reads: "Green light. Everything required for its risk tier is in place."

**Model 2 — real result: HIGH tier, 5/9 passed, FAIL, 4 open findings**

```bash
curl -X POST http://localhost:8000/models/2/assess-controls
```
```json
{
  "control_assessment": {
    "risk_category": "HIGH",
    "controls_required": 9,
    "controls_passed": 5,
    "overall_status": "FAIL"
  },
  "findings": [
    {"control_key": "independent_validation", "severity": "HIGH",
     "regulatory_reference": {"regulation_name": "RBI Scale Based Regulation (SBR) Framework", "guidance_type": "BINDING", ...}},
    {"control_key": "explainability", "severity": "HIGH",
     "regulatory_reference": {"regulation_name": "RBI FREE-AI Committee — Framework for Responsible and Ethical Enablement of AI", "guidance_type": "EMERGING", ...}},
    {"control_key": "drift_monitoring", "severity": "HIGH",
     "regulatory_reference": {"regulation_name": "RBI FREE-AI Committee — Framework for Responsible and Ethical Enablement of AI", "guidance_type": "EMERGING", ...}},
    {"control_key": "deployment_approval", "severity": "HIGH", "regulatory_reference": null}
  ]
}
```
CRO reads: "Four gaps, not two — it's a third-party black box that skipped
validation, explainability, drift monitoring, and formal deployment
sign-off. Each one is tied to a specific RBI expectation, not a vague
'best practice.'" (`deployment_approval` has no RBI mapping — it's an
internal process control, so its reference is correctly `null`, not a
crash.)

**Model 3 — real result: MEDIUM tier, 2/4 passed, FAIL, 2 open findings**

```bash
curl -X POST http://localhost:8000/models/3/assess-controls
```
```json
{
  "control_assessment": {
    "risk_category": "MEDIUM",
    "controls_required": 4,
    "controls_passed": 2,
    "overall_status": "FAIL"
  },
  "findings": [
    {"control_key": "independent_validation", "severity": "MEDIUM",
     "regulatory_reference": {"regulation_name": "RBI Scale Based Regulation (SBR) Framework", ...}},
    {"control_key": "drift_monitoring", "severity": "MEDIUM",
     "regulatory_reference": {"regulation_name": "RBI FREE-AI Committee — Framework for Responsible and Ethical Enablement of AI", ...}}
  ]
}
```
CRO reads: "Two gaps at MEDIUM severity — validation and drift monitoring.
Lower stakes than Model 2, but still tracked, still cited."

**Important:** `assess-controls` reports `overall_status: "PASS"/"FAIL"` —
it does NOT return an `ALLOW`/`BLOCKED` decision. That decision comes from
the deployment gate in Scene 3b.

====================================================
## Scene 3b: The deployment gate — ALLOW / BLOCKED

Narrator: "Controls tell you what's missing. The gate tells you whether the
model can actually deploy — combining risk tier, control status, and every
open finding into one decision."

**Model 1 — ALLOW**
```bash
curl -X POST http://localhost:8000/models/1/deployment-check
```
```json
{
  "decision": "ALLOW",
  "risk_category": "MEDIUM", "risk_score": 60,
  "overall_status": "PASS", "open_findings_count": 0,
  "blocking_findings": [],
  "message": "All controls satisfied. Deployment allowed."
}
```

**Model 2 — BLOCKED, four RBI-cited reasons**
```bash
curl -X POST http://localhost:8000/models/2/deployment-check
```
```json
{
  "decision": "BLOCKED",
  "risk_category": "HIGH", "risk_score": 70,
  "overall_status": "FAIL", "open_findings_count": 4,
  "message": "BLOCKED: 4 HIGH-severity control gaps (deployment approval, drift monitoring, explainability, independent validation) per RBI FREE-AI Committee — Framework for Responsible and Ethical Enablement of AI, RBI Scale Based Regulation (SBR) Framework."
}
```
CRO reads: "Blocked, and the message names the actual RBI frameworks. This
is what an examiner wants to see — not a score, a citation." (Note:
`deployment_approval` has no RBI mapping of its own — it still blocks and
appears by name in the finding list, it just doesn't add a regulation
citation the message can cite.)

**Model 3 — BLOCKED, MEDIUM-severity reasons**
```bash
curl -X POST http://localhost:8000/models/3/deployment-check
```
```json
{
  "decision": "BLOCKED",
  "risk_category": "MEDIUM", "risk_score": 45,
  "overall_status": "FAIL", "open_findings_count": 2,
  "message": "BLOCKED: 2 open control gaps (drift monitoring, independent validation) per RBI FREE-AI Committee — Framework for Responsible and Ethical Enablement of AI, RBI Scale Based Regulation (SBR) Framework."
}
```

====================================================
## Scene 4: View audit trail (immutable proof)

Narrator: "Every action is logged, append-only. This is our evidence trail
for regulators."

```bash
curl "http://localhost:8000/audit-logs?model_id=2"
```
```json
[
  {"id": 11, "action": "DEPLOYMENT_GATE_CHECKED", "model_id": 2, "user": "gate",
   "guardrail_result": "BLOCKED"},
  {"id": 8, "action": "CONTROL_ASSESSED", "model_id": 2, "user": "governance_analyst",
   "risk_assessment_result": "FAIL"},
  {"id": 5, "action": "RISK_ASSESSED", "model_id": 2, "user": "risk_analyst",
   "risk_assessment_result": "HIGH"},
  {"id": 2, "action": "MODEL_REGISTERED", "model_id": 2, "user": "system",
   "detail": {"name": "Fraud Detection Vendor API"}}
]
```
Four rows, not three — this trail is captured *after* Scene 3b's gate check,
which is itself an audited event (`DEPLOYMENT_GATE_CHECKED`, newest first).

CRO reads: "Every decision is timestamped and immutable — newest first,
including the gate check itself. If an auditor asks 'why was this model
blocked,' we show exactly what the system found, when, and why. Nothing
here can be edited or deleted — that's enforced structurally, not by
policy."

====================================================
## Scene 5: Remediation (close the findings, fix all four gaps)

Narrator: "Say the vendor fixes everything we flagged. We close the
findings, patch the model's attestations, and re-check the gate."

Model 2 has **four** open findings (ids will vary per run — list them first):

```bash
curl http://localhost:8000/models/2/findings
# -> ids 1 (independent_validation), 2 (explainability),
#    3 (drift_monitoring), 4 (deployment_approval)

for id in 1 2 3 4; do
  curl -X PATCH http://localhost:8000/findings/$id \
    -H "Content-Type: application/json" -d '{"status": "CLOSED"}'
done

curl -X PATCH http://localhost:8000/models/2 \
  -H "Content-Type: application/json" \
  -d '{
    "has_independent_validation": true,
    "has_explainability": true,
    "has_drift_monitoring": true,
    "has_deployment_approval": true
  }'

curl -X POST http://localhost:8000/models/2/assess-controls
curl -X POST http://localhost:8000/models/2/deployment-check
```

Real result — gate now returns:
```json
{
  "decision": "ALLOW",
  "risk_category": "HIGH", "risk_score": 70,
  "overall_status": "PASS", "open_findings_count": 0,
  "blocking_findings": [],
  "message": "All controls satisfied. Deployment allowed."
}
```
CRO reads: "Vendor fixed all four gaps. System re-assessed. Gate opens.
Model can deploy — and the whole before/after is on the audit trail."

====================================================
## Scene 6: The key insight

Narrator: "Here's what makes this different from a generic 'AI governance' tool.

1. **Risk is deterministic, not magic.** Every point in the score is
   explained. You can see why fraud detection scores higher than customer
   service.
2. **Controls are tied to actual regulation.** Not 'best practices' — RBI
   Scale Based Regulation, RBI FREE-AI Committee, RBI Guidelines on Digital
   Lending. When an auditor asks 'why do you require this,' the response
   carries the citation.
3. **Decisions are reproducible.** Run the gate check again on unchanged
   state: identical decision. Auditable, not a black box.
4. **The audit trail is immutable.** Every decision, every timestamp, every
   change is recorded — structurally append-only, not by convention.
5. **It scales.** Run the gate check on 50 models. High-risk ones with open
   gaps are BLOCKED. Clean ones are ALLOWED. All with regulatory evidence."

CRO says: "This is what RBI is asking for. Not marketing. Governance."

====================================================
## Time estimate

Live walkthrough: 10–12 minutes (three model registrations, three risk
assessments, three control checks, three gate checks, one audit review, one
remediation cycle).

Pre-populate the three models beforehand and just show Scenes 3b–6 to save
~5 minutes.

## What this demo shows (no UI)

✓ Deterministic risk scoring with factor breakdown
✓ Tier-based control checking (HIGH=9, MEDIUM=4, LOW=2)
✓ RBI regulatory references embedded in findings
✓ BLOCKED decisions with cited regulations (not just "bad score")
✓ Immutable, queryable audit trail
✓ Reproducible decisions (determinism)
✓ Remediation workflow (close findings, re-assess, re-gate, ALLOW)

This is the demo a CRO understands: not "we built a cool AI thing," but
"we built something that enforces RBI regulations and proves it."
