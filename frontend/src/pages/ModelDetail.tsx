import { useParams, Link as RouterLink } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Divider from "@mui/material/Divider";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useModel } from "../hooks/useModel";
import { useRisk } from "../hooks/useRisk";
import { useControls } from "../hooks/useControls";
import { useFindings } from "../hooks/useFindings";
import { useAudit } from "../hooks/useAudit";
import { RiskBadge } from "../components/RiskBadge";
import { GateDecision } from "../components/GateDecision";
import { FindingCard } from "../components/FindingCard";
import { AuditTrail } from "../components/AuditTrail";
import { controlLabel } from "../utils/controlLabels";
import { latestGateDecision } from "../utils/gate";

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <Paper sx={{ p: 3, mb: 3 }}>
    <Typography variant="h6" sx={{ mb: 2 }}>
      {title}
    </Typography>
    {children}
  </Paper>
);

export const ModelDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const modelId = id ?? "";

  const { data: model, isLoading: modelLoading, error: modelError } = useModel(modelId);
  const { data: risk } = useRisk(modelId);
  const { data: controls } = useControls(modelId);
  const { data: findings } = useFindings(modelId);
  const { data: audit } = useAudit(modelId);

  if (modelLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (modelError || !model) {
    return <Alert severity="error">Failed to load model {modelId}.</Alert>;
  }

  const gate = latestGateDecision(audit);
  const openFindings = findings?.filter((f) => f.status === "OPEN") ?? [];

  const gateMessage =
    gate === "ALLOW"
      ? "All controls satisfied"
      : gate === "BLOCKED" && openFindings.length > 0
        ? `${openFindings.length} open finding${openFindings.length === 1 ? "" : "s"} (see below)`
        : undefined;

  const passedKeys = new Set(controls?.detail.passed_controls ?? []);
  const failedDrafts = controls?.detail.finding_drafts ?? [];

  return (
    <>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4" component="h1">
          {model.name}
        </Typography>
        <Button component={RouterLink} to="/" startIcon={<ArrowBackIcon />}>
          Back
        </Button>
      </Box>

      <Section title="📊 Risk Assessment">
        {risk ? (
          <>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
              <Typography variant="h5">Score: {risk.risk_score}</Typography>
              <RiskBadge risk={risk.risk_category} />
            </Box>
            <List dense disablePadding>
              {risk.factor_breakdown.map((factor) => (
                <ListItem key={factor.key} disableGutters>
                  <ListItemText primary={`${factor.reason} (+${factor.points})`} />
                </ListItem>
              ))}
            </List>
          </>
        ) : (
          <Typography color="text.secondary">No risk assessment yet.</Typography>
        )}
      </Section>

      <Section title="🛡️ Control Assessment">
        {controls ? (
          <>
            <Typography sx={{ mb: 2 }} color={controls.overall_status === "PASS" ? "success.main" : "error.main"}>
              {controls.overall_status === "PASS" ? "✓" : "✗"} {controls.controls_passed} of{" "}
              {controls.controls_required} controls required
            </Typography>
            <List dense disablePadding>
              {[...passedKeys].map((key) => (
                <ListItem key={key} disableGutters>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <CheckCircleIcon color="success" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText primary={controlLabel(key)} />
                </ListItem>
              ))}
              {failedDrafts.map((draft) => (
                <ListItem key={draft.control_key} disableGutters>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <CancelIcon color="error" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText
                    primary={controlLabel(draft.control_key)}
                    secondary={
                      <Typography variant="body2" color="error.main" component="span">
                        NOT COMPLETE
                      </Typography>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </>
        ) : (
          <Typography color="text.secondary">No control assessment yet.</Typography>
        )}
      </Section>

      <Section title="🚀 Deployment Gate">
        <GateDecision decision={gate} message={gateMessage} />
      </Section>

      <Section title={`📋 Open Findings (${openFindings.length})`}>
        {openFindings.length === 0 ? (
          <Typography color="text.secondary">None.</Typography>
        ) : (
          openFindings.map((finding) => (
            <FindingCard
              key={finding.id}
              title={finding.title}
              severity={finding.severity}
              regulatoryReference={finding.regulatory_reference}
              status={finding.status}
            />
          ))
        )}
      </Section>

      <Divider sx={{ my: 3 }} />

      <Section title="🔍 Recent Audit Trail">
        <AuditTrail logs={audit} />
      </Section>
    </>
  );
};
