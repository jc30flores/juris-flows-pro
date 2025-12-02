import axios from "axios";

export const API_BASE_URL = window.location.origin;

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  withCredentials: true,
});
