import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";

interface ControlsProgressProps {
  passed: number;
  required: number;
  compact?: boolean;
}

export const ControlsProgress: React.FC<ControlsProgressProps> = ({
  passed,
  required,
  compact,
}) => {
  const percentage = required > 0 ? (passed / required) * 100 : 0;
  const ok = passed === required;

  if (compact) {
    return (
      <Typography variant="body2" color={ok ? "success.main" : "error.main"}>
        {passed}/{required} {ok ? "✓" : "✗"}
      </Typography>
    );
  }

  return (
    <Box>
      <LinearProgress
        variant="determinate"
        value={percentage}
        color={ok ? "success" : "error"}
        sx={{ height: 8, borderRadius: 4, mb: 0.5 }}
      />
      <Typography variant="body2" color="text.secondary">
        {passed} of {required} controls passed
      </Typography>
    </Box>
  );
};
