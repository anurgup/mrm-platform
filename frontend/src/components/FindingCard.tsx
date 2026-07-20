import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { RegulatoryReference, Severity, FindingStatus } from "../types/api";

interface FindingCardProps {
  title: string;
  severity: Severity;
  regulatoryReference: RegulatoryReference | null;
  status: FindingStatus;
}

const SEVERITY_COLOR: Record<Severity, "info" | "warning" | "error"> = {
  LOW: "info",
  MEDIUM: "warning",
  HIGH: "error",
};

export const FindingCard: React.FC<FindingCardProps> = ({
  title,
  severity,
  regulatoryReference,
  status,
}) => {
  const color = SEVERITY_COLOR[severity];

  return (
    <Card variant="outlined" sx={{ mb: 2, borderColor: `${color}.main`, borderWidth: 2 }}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
          <Typography variant="h6" component="div">
            🔴 {title}
          </Typography>
          <Chip label={severity} color={color} size="small" />
        </Box>

        {regulatoryReference && (
          <Box sx={{ backgroundColor: "action.hover", p: 2, borderRadius: 1, mb: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              📋 {regulatoryReference.regulation_name}
            </Typography>
            <Typography variant="body2" sx={{ mt: 1, fontStyle: "italic" }}>
              "{regulatoryReference.reference_text}"
            </Typography>
            <Chip
              label={regulatoryReference.guidance_type}
              size="small"
              variant="outlined"
              sx={{ mt: 1 }}
            />
          </Box>
        )}

        <Chip label={status} size="small" variant="outlined" />
      </CardContent>
    </Card>
  );
};
