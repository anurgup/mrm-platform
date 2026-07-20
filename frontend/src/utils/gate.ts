import type { AuditLog, GateDecisionValue } from "../types/api";

// Reads the decision off the audit trail (a GET, no side effects) instead of
// POSTing /models/:id/deployment-check, which writes a new audit log entry
// on every call — calling it just to render a page would spam the trail
// with entries that don't correspond to a real gate check.
export const latestGateDecision = (logs: AuditLog[] | undefined): GateDecisionValue | null => {
  const entry = logs?.find((log) => log.action === "DEPLOYMENT_GATE_CHECKED");
  return entry?.guardrail_result ?? null;
};
