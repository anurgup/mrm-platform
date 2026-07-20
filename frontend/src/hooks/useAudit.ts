import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { AuditLog } from "../types/api";

// GET /audit-logs?model_id=X already returns newest-first — verified against
// a running server, so no client-side re-sort is needed.
export const useAudit = (id: string) =>
  useQuery({
    queryKey: ["audit", id],
    queryFn: async () => {
      const { data } = await apiClient.get<AuditLog[]>("/audit-logs", {
        params: { model_id: id },
      });
      return data.slice(0, 10);
    },
  });
