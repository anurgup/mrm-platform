import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { ControlAssessment } from "../types/api";

export const useControls = (id: string) =>
  useQuery({
    queryKey: ["controls", id],
    queryFn: async () => {
      const { data } = await apiClient.get<ControlAssessment>(`/models/${id}/controls`);
      return data;
    },
  });
