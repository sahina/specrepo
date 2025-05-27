import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface ValidationRequest {
  apiSpec: string;
  specContent: string;
  notificationEmail?: string;
}

export interface ValidationResponse {
  validationId: string;
  status: string;
  message: string;
}

export const validationApi = {
  // Start a new validation
  startValidation: async (
    request: ValidationRequest,
  ): Promise<ValidationResponse> => {
    const response = await api.post("/api/validation/start", request);
    return response.data;
  },

  // Get validation status
  getValidationStatus: async (validationId: string) => {
    const response = await api.get(`/api/validation/${validationId}/status`);
    return response.data;
  },

  // Get validation results
  getValidationResults: async (validationId: string) => {
    const response = await api.get(`/api/validation/${validationId}/results`);
    return response.data;
  },

  // Get all validations
  getAllValidations: async () => {
    const response = await api.get("/api/validation/history");
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get("/health");
    return response.data;
  },
};

export default api;
