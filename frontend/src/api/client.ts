import axios from "axios";

export const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export const apiClient = axios.create({ baseURL: API_BASE_URL });
