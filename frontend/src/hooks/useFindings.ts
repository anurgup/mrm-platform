import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { Finding } from "../types/api";

export const useFindings = (id: string) =>
  useQuery({
    queryKey: ["findings", id],
    queryFn: async () => {
      const { data } = await apiClient.get<Finding[]>(`/models/${id}/findings`);
      return data;
    },
  });
