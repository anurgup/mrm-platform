import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import type { AuditLog } from "../types/api";

interface AuditTrailProps {
  logs: AuditLog[] | undefined;
}

const describe = (log: AuditLog): string => {
  switch (log.action) {
    case "DEPLOYMENT_GATE_CHECKED":
      return `Gate decision: ${log.guardrail_result}`;
    case "RISK_ASSESSED":
      return `Risk score computed: ${log.risk_assessment_result}`;
    case "CONTROL_ASSESSED":
      return `Controls assessed: ${log.risk_assessment_result}`;
    case "MODEL_REGISTERED":
      return "Model registered";
    default:
      return log.action;
  }
};

export const AuditTrail: React.FC<AuditTrailProps> = ({ logs }) => {
  if (!logs || logs.length === 0) {
    return <Typography color="text.secondary">No audit history.</Typography>;
  }

  return (
    <List dense disablePadding>
      {logs.map((log) => (
        <ListItem key={log.id} disableGutters divider>
          <ListItemText
            primary={describe(log)}
            secondary={`${new Date(log.timestamp).toLocaleString()} · by ${log.user}`}
          />
        </ListItem>
      ))}
    </List>
  );
};
