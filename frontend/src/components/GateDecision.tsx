import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import type { GateDecisionValue } from "../types/api";

interface GateDecisionProps {
  decision: GateDecisionValue | null | undefined;
  message?: string;
  compact?: boolean;
}

export const GateDecision: React.FC<GateDecisionProps> = ({ decision, message, compact }) => {
  if (!decision) {
    return <Alert severity="info" variant="outlined">Not yet checked</Alert>;
  }

  const severity = decision === "ALLOW" ? "success" : "error";

  if (compact) {
    return (
      <Alert severity={severity} sx={{ py: 0 }}>
        <strong>{decision}</strong>
      </Alert>
    );
  }

  return (
    <Alert severity={severity}>
      <AlertTitle>
        <strong>{decision === "ALLOW" ? "✓ ALLOW" : "✗ BLOCKED"}</strong>
      </AlertTitle>
      {message}
    </Alert>
  );
};
