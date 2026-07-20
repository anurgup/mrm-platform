import Chip from "@mui/material/Chip";
import type { RiskCategory } from "../types/api";

const COLORS: Record<RiskCategory, "success" | "warning" | "error"> = {
  LOW: "success",
  MEDIUM: "warning",
  HIGH: "error",
};

const DOTS: Record<RiskCategory, string> = {
  LOW: "🟢",
  MEDIUM: "🟡",
  HIGH: "🔴",
};

interface RiskBadgeProps {
  risk: RiskCategory | null | undefined;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ risk }) => {
  if (!risk) return <Chip label="—" size="small" variant="outlined" />;
  return <Chip label={`${DOTS[risk]} ${risk}`} color={COLORS[risk]} size="small" />;
};
