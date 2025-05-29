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
  environment_id?: number;
  provider_url?: string;
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

// Environment types
export enum EnvironmentType {
  PRODUCTION = "production",
  STAGING = "staging",
  DEVELOPMENT = "development",
  CUSTOM = "custom",
}

export interface Environment {
  id: number;
  name: string;
  base_url: string;
  description?: string;
  environment_type: EnvironmentType;
  is_active: string;
  user_id: number;
  created_at: string;
  updated_at?: string;
}

export interface EnvironmentCreate {
  name: string;
  base_url: string;
  description?: string;
  environment_type?: EnvironmentType;
}

export interface EnvironmentUpdate {
  name?: string;
  base_url?: string;
  description?: string;
  environment_type?: EnvironmentType;
  is_active?: string;
}

export interface EnvironmentFilters {
  name?: string;
  environment_type?: EnvironmentType;
  is_active?: string;
  sort_by?: "name" | "environment_type" | "created_at" | "updated_at";
  sort_order?: "asc" | "desc";
  page?: number;
  size?: number;
}

// User types
export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
  updated_at?: string;
}

export interface CreateUserRequest {
  username: string;
  email: string;
}

export interface CreateUserResponse {
  message: string;
  username: string;
  api_key: string;
}

// Mock types
export interface MockDeployRequest {
  specification_id: number;
  clear_existing?: boolean;
}

export interface MockDeployResponse {
  message: string;
  configuration_id: number;
  stubs_created: number;
  status: string;
}

export interface MockStatusResponse {
  total_configurations: number;
  active_configurations: number;
  configurations: Array<{
    id: number;
    api_specification_id: number;
    status: string;
    deployed_at?: string;
    stubs_count: number;
    specification_name?: string;
    specification_version?: string;
  }>;
}

// HAR Upload types
export interface HARUpload {
  id: number;
  file_name: string;
  processed_artifacts_references?: Record<string, unknown>;
  uploaded_at: string;
  user_id: number;
}

export interface HARUploadFilters {
  file_name?: string;
  sort_by?: "file_name" | "uploaded_at";
  sort_order?: "asc" | "desc";
  page?: number;
  size?: number;
}

// Contract Sketches types
export interface HARProcessingMetadata {
  interactions_count: number;
  processed_interactions_count: number;
  openapi_paths_count: number;
  wiremock_stubs_count: number;
  processed_at: string;
  processing_options: Record<string, unknown>;
}

export interface HARProcessingArtifacts {
  openapi_specification: Record<string, unknown>;
  wiremock_mappings: Array<Record<string, unknown>>;
  processing_metadata: HARProcessingMetadata;
}

export interface HARProcessingArtifactsResponse {
  upload_id: number;
  file_name: string;
  artifacts: HARProcessingArtifacts;
  uploaded_at: string;
  processed_at: string;
}

export interface HARProcessingStatus {
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  current_step?: string;
  started_at?: string;
  completed_at?: string;
  failed_at?: string;
  error?: string;
  artifacts_available: boolean;
  interactions_count?: number;
  openapi_paths_count?: number;
  wiremock_stubs_count?: number;
}

export interface SaveArtifactRequest {
  artifact_type: "openapi_specification" | "wiremock_mappings";
  name: string;
  version_string?: string;
  description?: string;
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
  // User Profile
  // ============================================================================

  async getProfile(): Promise<{
    id: number;
    username: string;
    email: string;
    created_at: string;
  }> {
    const response = await this.client.get("/api/profile");
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
  // Environments
  // ============================================================================

  async createEnvironment(data: EnvironmentCreate): Promise<Environment> {
    const response: AxiosResponse<Environment> = await this.client.post(
      "/api/environments",
      data,
    );
    return response.data;
  }

  async getEnvironments(
    filters?: EnvironmentFilters,
  ): Promise<PaginatedResponse<Environment>> {
    const params = new URLSearchParams();

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, value.toString());
        }
      });
    }

    const response: AxiosResponse<PaginatedResponse<Environment>> =
      await this.client.get(`/api/environments?${params.toString()}`);
    return response.data;
  }

  async getEnvironment(id: number): Promise<Environment> {
    const response: AxiosResponse<Environment> = await this.client.get(
      `/api/environments/${id}`,
    );
    return response.data;
  }

  async updateEnvironment(
    id: number,
    data: EnvironmentUpdate,
  ): Promise<Environment> {
    const response: AxiosResponse<Environment> = await this.client.put(
      `/api/environments/${id}`,
      data,
    );
    return response.data;
  }

  async deleteEnvironment(id: number): Promise<void> {
    await this.client.delete(`/api/environments/${id}`);
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

  async getWireMockStubs(
    specificationId?: number,
  ): Promise<WireMockStatusResponse> {
    const params = new URLSearchParams();

    if (specificationId !== undefined) {
      params.append("specification_id", specificationId.toString());
    }

    const url = params.toString()
      ? `/api/wiremock/stubs?${params.toString()}`
      : "/api/wiremock/stubs";

    const response: AxiosResponse<WireMockStatusResponse> =
      await this.client.get(url);
    return response.data;
  }

  async clearWireMockStubs(): Promise<void> {
    await this.client.delete("/api/wiremock/stubs");
  }

  async resetWireMock(): Promise<void> {
    await this.client.post("/api/wiremock/reset");
  }

  // ============================================================================
  // User Management
  // ============================================================================

  async createUser(userData: CreateUserRequest): Promise<CreateUserResponse> {
    const response: AxiosResponse<CreateUserResponse> = await this.client.post(
      "/api/users",
      null,
      {
        params: userData,
      },
    );
    return response.data;
  }

  // ============================================================================
  // Mock Management
  // ============================================================================

  async deployMock(data: MockDeployRequest): Promise<MockDeployResponse> {
    const response: AxiosResponse<MockDeployResponse> = await this.client.post(
      "/api/mocks/deploy",
      data,
    );
    return response.data;
  }

  async getMockStatus(): Promise<MockStatusResponse> {
    const response: AxiosResponse<MockStatusResponse> = await this.client.get(
      "/api/mocks/status",
    );
    return response.data;
  }

  async clearMocks(): Promise<{ message: string; cleared_stubs: number }> {
    const response = await this.client.delete("/api/wiremock/clear");
    return response.data;
  }

  // ============================================================================
  // HAR Upload Methods
  // ============================================================================

  async uploadHARFile(file: File): Promise<HARUpload> {
    const formData = new FormData();

    // Create a new File object with the correct MIME type for HAR files
    const harFile = new File([file], file.name, {
      type: "application/json",
      lastModified: file.lastModified,
    });

    formData.append("file", harFile);

    const response = await this.client.post("/api/har-uploads", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  }

  async getHARUploads(
    filters?: HARUploadFilters,
  ): Promise<PaginatedResponse<HARUpload>> {
    const params = new URLSearchParams();

    if (filters?.file_name) params.append("file_name", filters.file_name);
    if (filters?.sort_by) params.append("sort_by", filters.sort_by);
    if (filters?.sort_order) params.append("sort_order", filters.sort_order);
    if (filters?.page) params.append("page", filters.page.toString());
    if (filters?.size) params.append("size", filters.size.toString());

    const response = await this.client.get(
      `/api/har-uploads?${params.toString()}`,
    );
    return response.data;
  }

  async getHARUpload(id: number): Promise<HARUpload> {
    const response = await this.client.get(`/api/har-uploads/${id}`);
    return response.data;
  }

  async deleteHARUpload(id: number): Promise<void> {
    await this.client.delete(`/api/har-uploads/${id}`);
  }

  async processHARFile(
    id: number,
    options?: Record<string, unknown>,
  ): Promise<{
    success: boolean;
    upload_id: number;
    message: string;
    processing_status: HARProcessingStatus;
  }> {
    const response = await this.client.post(
      `/api/har-uploads/${id}/process`,
      options || {},
    );
    return response.data;
  }

  async getHARProcessingStatus(id: number): Promise<HARProcessingStatus> {
    const response = await this.client.get(`/api/har-uploads/${id}/status`);
    return response.data;
  }

  // ============================================================================
  // Contract Sketches Methods
  // ============================================================================

  async getHARProcessingArtifacts(
    id: number,
  ): Promise<HARProcessingArtifactsResponse> {
    const response = await this.client.get(`/api/har-uploads/${id}/artifacts`);
    return response.data;
  }

  async saveArtifact(
    uploadId: number,
    data: SaveArtifactRequest,
  ): Promise<{ message: string; id: number }> {
    const response = await this.client.post(
      `/api/har-uploads/${uploadId}/save-artifact`,
      data,
    );
    return response.data;
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
