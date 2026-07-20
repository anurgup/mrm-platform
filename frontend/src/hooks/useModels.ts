import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { AIModel } from "../types/api";

export const useModels = () =>
  useQuery({
    queryKey: ["models"],
    queryFn: async () => {
      const { data } = await apiClient.get<AIModel[]>("/models");
      return data;
    },
  });
