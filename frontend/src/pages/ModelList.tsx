import { useQueries } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Link from "@mui/material/Link";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import Alert from "@mui/material/Alert";
import { useModels } from "../hooks/useModels";
import { apiClient } from "../api/client";
import { RiskBadge } from "../components/RiskBadge";
import { GateDecision } from "../components/GateDecision";
import { ControlsProgress } from "../components/ControlsProgress";
import { latestGateDecision } from "../utils/gate";
import type { AuditLog, ControlAssessment, RiskAssessment } from "../types/api";

export const ModelList: React.FC = () => {
  const { data: models, isLoading, error } = useModels();
  const ids = models?.map((m) => m.id) ?? [];

  const riskQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["risk", String(id)],
      queryFn: async () => (await apiClient.get<RiskAssessment>(`/models/${id}/risk`)).data,
      enabled: ids.length > 0,
    })),
  });
  const controlQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["controls", String(id)],
      queryFn: async () => (await apiClient.get<ControlAssessment>(`/models/${id}/controls`)).data,
      enabled: ids.length > 0,
    })),
  });
  const auditQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ["audit", String(id)],
      queryFn: async () =>
        (await apiClient.get<AuditLog[]>("/audit-logs", { params: { model_id: id } })).data.slice(
          0,
          10,
        ),
      enabled: ids.length > 0,
    })),
  });

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Failed to load models: {(error as Error).message}</Alert>;
  }

  return (
    <>
      <Typography variant="h4" component="h1" sx={{ mb: 3 }}>
        Models
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Risk</TableCell>
              <TableCell>Controls</TableCell>
              <TableCell>Gate</TableCell>
              <TableCell>Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {models?.map((model, i) => {
              const risk = riskQueries[i]?.data;
              const controls = controlQueries[i]?.data;
              const gate = latestGateDecision(auditQueries[i]?.data);
              return (
                <TableRow key={model.id} hover>
                  <TableCell>
                    <Link component={RouterLink} to={`/models/${model.id}`} underline="hover">
                      {model.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <RiskBadge risk={risk?.risk_category} />
                  </TableCell>
                  <TableCell>
                    {controls ? (
                      <ControlsProgress
                        passed={controls.controls_passed}
                        required={controls.controls_required}
                        compact
                      />
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>
                    <GateDecision decision={gate} compact />
                  </TableCell>
                  <TableCell>
                    <Link component={RouterLink} to={`/models/${model.id}`} underline="hover">
                      View
                    </Link>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
};
