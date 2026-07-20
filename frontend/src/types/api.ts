// Mirrors the actual backend response shapes — verified against a running
// server (GET /models, /models/:id/risk, /controls, /findings, /audit-logs),
// not assumed from the API's Pydantic schema names.

export type RiskCategory = "LOW" | "MEDIUM" | "HIGH";
export type GateDecisionValue = "ALLOW" | "BLOCKED";
export type ControlStatus = "PASS" | "FAIL";
export type FindingStatus = "OPEN" | "IN_REMEDIATION" | "CLOSED";
export type Severity = "LOW" | "MEDIUM" | "HIGH";

export interface AIModel {
  id: number;
  name: string;
  description: string | null;
  business_function: string;
  model_type: string;
  deployment_stage: string;
  business_owner: string;
  risk_owner: string;
  technical_owner: string;
  data_classification: string;
  vendor_dependency: string;
  vendor_name: string | null;
  llm_provider: string | null;
  llm_model_name: string | null;
  has_documentation: boolean;
  has_independent_validation: boolean;
  has_explainability: boolean;
  has_drift_monitoring: boolean;
  has_human_override: boolean;
  has_audit_logging: boolean;
  has_deployment_approval: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskFactor {
  key: string;
  reason: string;
  points: number;
}

export interface RiskAssessment {
  id: number;
  model_id: number;
  risk_score: number;
  risk_category: RiskCategory;
  assessment_reason: string;
  factor_breakdown: RiskFactor[];
  assessed_at: string;
}

export interface RegulatoryReference {
  regulation_name: string;
  reference_text: string;
  guidance_type: "BINDING" | "EMERGING";
  effective_note: string;
}

export interface FindingDraft {
  control_key: string;
  title: string;
  severity: Severity;
  risk_description: string;
  remediation: string;
  regulatory_reference: RegulatoryReference | null;
}

export interface ControlAssessment {
  id: number;
  model_id: number;
  risk_category: RiskCategory;
  controls_required: number;
  controls_passed: number;
  overall_status: ControlStatus;
  detail: {
    passed_controls: string[];
    finding_drafts: FindingDraft[];
  };
  assessed_at: string;
}

export interface Finding {
  id: number;
  model_id: number;
  title: string;
  severity: Severity;
  risk_description: string;
  remediation: string;
  regulatory_reference: RegulatoryReference | null;
  control_key: string;
  status: FindingStatus;
  created_at: string;
}

export interface AuditLog {
  id: number;
  user: string;
  timestamp: string;
  action: string;
  model_id: number | null;
  llm_provider_used: string | null;
  guardrail_result: GateDecisionValue | null;
  risk_assessment_result: string | null;
  report_generated: string | null;
  detail: Record<string, unknown>;
}
