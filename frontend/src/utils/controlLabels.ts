// The API returns control_key ("model_owner", "drift_monitoring", ...) with
// no human-readable label — these are the 9 known keys the control engine
// checks, verified against /models/:id/controls responses across all three
// risk tiers (LOW=0, MEDIUM=4, HIGH=9 required).
export const CONTROL_LABELS: Record<string, string> = {
  model_owner: "Model owner documented",
  risk_owner: "Risk owner assigned",
  documentation: "Documentation on file",
  independent_validation: "Independent validation completed",
  explainability: "Explainability mechanisms in place",
  drift_monitoring: "Drift monitoring enabled",
  human_override: "Human override capability",
  audit_logging: "Audit logging enabled",
  deployment_approval: "Deployment approval recorded",
};

export const controlLabel = (key: string): string => CONTROL_LABELS[key] ?? key;
