import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { RiskAssessment } from "../types/api";

export const useRisk = (id: string) =>
  useQuery({
    queryKey: ["risk", id],
    queryFn: async () => {
      const { data } = await apiClient.get<RiskAssessment>(`/models/${id}/risk`);
      return data;
    },
  });
