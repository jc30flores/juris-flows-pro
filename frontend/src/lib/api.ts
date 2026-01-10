import axios from "axios";

export const API_BASE_URL = window.location.origin;

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const storedUser = localStorage.getItem("auth_user");
  if (storedUser) {
    try {
      const parsed = JSON.parse(storedUser) as { id?: number };
      if (parsed.id) {
        config.headers = config.headers ?? {};
        config.headers["X-Staff-User"] = String(parsed.id);
      }
    } catch (error) {
      console.error("Error parsing auth user for headers", error);
    }
  }
  return config;
});
