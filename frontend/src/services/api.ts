import axios, { AxiosError, AxiosInstance, AxiosResponse } from "axios";

// Base configuration
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

// ============================================================================
// Type Definitions
// ============================================================================

// Common types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  version?: string;
}

// API Specification types
export interface APISpecification {
  id: number;
  name: string;
  version_string: string;
  openapi_content: Record<string, unknown>;
  user_id: number;
  created_at: string;
  updated_at?: string;
}

export interface APISpecificationCreate {
  name: string;
  version_string: string;
  openapi_content: Record<string, unknown>;
}

export interface APISpecificationUpdate {
  name?: string;
  version_string?: string;
  openapi_content?: Record<string, unknown>;
}

export interface APISpecificationFilters {
  name?: string;
  version_string?: string;
  sort_by?: "name" | "version_string" | "created_at" | "updated_at";
  sort_order?: "asc" | "desc";
  page?: number;
  size?: number;
}

// Validation types
export enum ValidationRunStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

export enum AuthMethod {
  NONE = "none",
  API_KEY = "api_key",
  BEARER_TOKEN = "bearer_token",
  BASIC_AUTH = "basic_auth",
  OAUTH2 = "oauth2",
}

export interface ValidationRun {
  id: number;
  api_specification_id: number;
  provider_url: string;
  status: ValidationRunStatus;
  auth_method: AuthMethod;
  test_strategies?: string[];
  max_examples?: number;
  timeout?: number;
  schemathesis_results?: Record<string, unknown>;
  triggered_at: string;
  user_id: number;
}

export interface ValidationRunCreate {
  api_specification_id: number;
  provider_url: string;
  auth_method?: AuthMethod;
  auth_config?: Record<string, unknown>;
  test_strategies?: string[];
  max_examples?: number;
  timeout?: number;
}

export interface ValidationRunFilters {
  api_specification_id?: number;
  status?: ValidationRunStatus;
  provider_url?: string;
  sort_by?: "triggered_at" | "status" | "provider_url";
  sort_order?: "asc" | "desc";
  page?: number;
  size?: number;
}

// WireMock types
export interface WireMockStub {
  id: string;
  request: Record<string, unknown>;
  response: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface WireMockGenerateRequest {
  specification_id: number;
  clear_existing?: boolean;
}

export interface WireMockGenerateResponse {
  message: string;
  stubs_created: number;
  stubs: WireMockStub[];
}

export interface WireMockStatusResponse {
  total_stubs: number;
  stubs: WireMockStub[];
}

// ============================================================================
// API Client Class
// ============================================================================

class ApiClient {
  private client: AxiosInstance;
  private apiKey: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: DEFAULT_TIMEOUT,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.setupInterceptors();
  }

  // ============================================================================
  // Configuration & Authentication
  // ============================================================================

  setApiKey(apiKey: string): void {
    this.apiKey = apiKey;
  }

  clearApiKey(): void {
    this.apiKey = null;
  }

  private setupInterceptors(): void {
    // Request interceptor for authentication
    this.client.interceptors.request.use(
      (config) => {
        if (this.apiKey) {
          config.headers["X-API-Key"] = this.apiKey;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as typeof error.config & {
          _retry?: boolean;
          _retryCount?: number;
        };

        // Handle authentication errors
        if (error.response?.status === 401) {
          this.clearApiKey();
          throw new Error("Authentication failed. Please check your API key.");
        }

        // Retry logic for transient failures (5xx errors)
        if (
          error.response?.status &&
          error.response.status >= 500 &&
          originalRequest &&
          !originalRequest._retry &&
          (originalRequest._retryCount || 0) < MAX_RETRIES
        ) {
          originalRequest._retry = true;
          const retryCount = (originalRequest._retryCount || 0) + 1;
          originalRequest._retryCount = retryCount;

          await this.delay(RETRY_DELAY * retryCount);
          return this.client(originalRequest);
        }

        // Transform error response
        const errorData = error.response?.data as
          | { detail?: string }
          | undefined;
        const apiError: ApiError = {
          detail: errorData?.detail || error.message || "An error occurred",
          status_code: error.response?.status,
        };

        throw apiError;
      },
    );
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // ============================================================================
  // Health Check
  // ============================================================================

  async healthCheck(): Promise<HealthCheckResponse> {
    const response = await this.client.get("/health");
    return response.data;
  }

  // ============================================================================
  // API Specifications
  // ============================================================================

  async createSpecification(
    data: APISpecificationCreate,
  ): Promise<APISpecification> {
    const response: AxiosResponse<APISpecification> = await this.client.post(
      "/api/specifications",
      data,
    );
    return response.data;
  }

  async getSpecifications(
    filters?: APISpecificationFilters,
  ): Promise<PaginatedResponse<APISpecification>> {
    const params = new URLSearchParams();

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString());
        }
      });
    }

    const response: AxiosResponse<PaginatedResponse<APISpecification>> =
      await this.client.get(`/api/specifications?${params.toString()}`);
    return response.data;
  }

  async getSpecification(id: number): Promise<APISpecification> {
    const response: AxiosResponse<APISpecification> = await this.client.get(
      `/api/specifications/${id}`,
    );
    return response.data;
  }

  async updateSpecification(
    id: number,
    data: APISpecificationUpdate,
  ): Promise<APISpecification> {
    const response: AxiosResponse<APISpecification> = await this.client.put(
      `/api/specifications/${id}`,
      data,
    );
    return response.data;
  }

  async deleteSpecification(id: number): Promise<void> {
    await this.client.delete(`/api/specifications/${id}`);
  }

  // ============================================================================
  // Validations (Schemathesis)
  // ============================================================================

  async triggerValidation(data: ValidationRunCreate): Promise<ValidationRun> {
    const response: AxiosResponse<ValidationRun> = await this.client.post(
      "/api/validations",
      data,
    );
    return response.data;
  }

  async getValidationResults(id: number): Promise<ValidationRun> {
    const response: AxiosResponse<ValidationRun> = await this.client.get(
      `/api/validations/${id}`,
    );
    return response.data;
  }

  async getValidations(
    filters?: ValidationRunFilters,
  ): Promise<PaginatedResponse<ValidationRun>> {
    const params = new URLSearchParams();

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString());
        }
      });
    }

    const response: AxiosResponse<PaginatedResponse<ValidationRun>> =
      await this.client.get(`/api/validations?${params.toString()}`);
    return response.data;
  }

  // ============================================================================
  // WireMock Integration
  // ============================================================================

  async generateWireMockStubs(
    data: WireMockGenerateRequest,
  ): Promise<WireMockGenerateResponse> {
    const response: AxiosResponse<WireMockGenerateResponse> =
      await this.client.post("/api/wiremock/generate", data);
    return response.data;
  }

  async getWireMockStubs(): Promise<WireMockStatusResponse> {
    const response: AxiosResponse<WireMockStatusResponse> =
      await this.client.get("/api/wiremock/stubs");
    return response.data;
  }

  async clearWireMockStubs(): Promise<void> {
    await this.client.delete("/api/wiremock/stubs");
  }

  async resetWireMock(): Promise<void> {
    await this.client.post("/api/wiremock/reset");
  }
}

// ============================================================================
// Singleton Instance & Legacy API
// ============================================================================

// Create singleton instance
const apiClient = new ApiClient();

// Legacy API for backward compatibility
interface LegacyValidationRequest {
  apiSpec?: string;
  specContent?: string;
  notificationEmail?: string;
}

export const validationApi = {
  startValidation: async (
    request: LegacyValidationRequest,
  ): Promise<ValidationRun> => {
    // Map legacy request to new format
    const validationRequest: ValidationRunCreate = {
      api_specification_id: 1, // This would need to be determined from the request
      provider_url: request.apiSpec || "http://localhost:8080",
      auth_method: AuthMethod.NONE,
    };
    return apiClient.triggerValidation(validationRequest);
  },

  getValidationStatus: async (validationId: string): Promise<ValidationRun> => {
    return apiClient.getValidationResults(parseInt(validationId));
  },

  getValidationResults: async (
    validationId: string,
  ): Promise<ValidationRun> => {
    return apiClient.getValidationResults(parseInt(validationId));
  },

  getAllValidations: async (): Promise<ValidationRun[]> => {
    const result = await apiClient.getValidations();
    return result.items;
  },

  healthCheck: async (): Promise<HealthCheckResponse> => {
    return apiClient.healthCheck();
  },
};

// Export the client instance and types
export default apiClient;
export { ApiClient };
