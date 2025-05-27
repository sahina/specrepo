import { useEffect } from "react";
import apiClient from "../services/api";
import { useAuthStore } from "../store/authStore";

export function useApiClient() {
  const { apiKey, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated && apiKey) {
      apiClient.setApiKey(apiKey);
    } else {
      apiClient.clearApiKey();
    }
  }, [apiKey, isAuthenticated]);

  return apiClient;
}
