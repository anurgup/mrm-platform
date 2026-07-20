import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { AIModel } from "../types/api";

export const useModel = (id: string) =>
  useQuery({
    queryKey: ["model", id],
    queryFn: async () => {
      const { data } = await apiClient.get<AIModel>(`/models/${id}`);
      return data;
    },
  });
