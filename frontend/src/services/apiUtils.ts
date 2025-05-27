import { ApiError, AuthMethod, ValidationRunStatus } from "./api";

// ============================================================================
// Error Handling Utilities
// ============================================================================

export const formatApiError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }

  if (typeof error === "object" && error !== null && "detail" in error) {
    const apiError = error as ApiError;
    return apiError.detail;
  }

  return "An unexpected error occurred";
};

export const isApiError = (error: unknown): error is ApiError => {
  return (
    typeof error === "object" &&
    error !== null &&
    "detail" in error &&
    typeof (error as ApiError).detail === "string"
  );
};

// ============================================================================
// Authentication Utilities
// ============================================================================

const API_KEY_STORAGE_KEY = "specrepo_api_key";

export const saveApiKey = (apiKey: string): void => {
  localStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
};

export const getStoredApiKey = (): string | null => {
  return localStorage.getItem(API_KEY_STORAGE_KEY);
};

export const clearStoredApiKey = (): void => {
  localStorage.removeItem(API_KEY_STORAGE_KEY);
};

// ============================================================================
// Validation Status Utilities
// ============================================================================

export const getValidationStatusColor = (
  status: ValidationRunStatus,
): string => {
  switch (status) {
    case ValidationRunStatus.PENDING:
      return "text-yellow-600 bg-yellow-50";
    case ValidationRunStatus.RUNNING:
      return "text-blue-600 bg-blue-50";
    case ValidationRunStatus.COMPLETED:
      return "text-green-600 bg-green-50";
    case ValidationRunStatus.FAILED:
      return "text-red-600 bg-red-50";
    case ValidationRunStatus.CANCELLED:
      return "text-gray-600 bg-gray-50";
    default:
      return "text-gray-600 bg-gray-50";
  }
};

export const getValidationStatusLabel = (
  status: ValidationRunStatus,
): string => {
  switch (status) {
    case ValidationRunStatus.PENDING:
      return "Pending";
    case ValidationRunStatus.RUNNING:
      return "Running";
    case ValidationRunStatus.COMPLETED:
      return "Completed";
    case ValidationRunStatus.FAILED:
      return "Failed";
    case ValidationRunStatus.CANCELLED:
      return "Cancelled";
    default:
      return "Unknown";
  }
};

export const isValidationComplete = (status: ValidationRunStatus): boolean => {
  return [
    ValidationRunStatus.COMPLETED,
    ValidationRunStatus.FAILED,
    ValidationRunStatus.CANCELLED,
  ].includes(status);
};

// ============================================================================
// Auth Method Utilities
// ============================================================================

export const getAuthMethodLabel = (method: AuthMethod): string => {
  switch (method) {
    case AuthMethod.NONE:
      return "No Authentication";
    case AuthMethod.API_KEY:
      return "API Key";
    case AuthMethod.BEARER_TOKEN:
      return "Bearer Token";
    case AuthMethod.BASIC_AUTH:
      return "Basic Authentication";
    case AuthMethod.OAUTH2:
      return "OAuth 2.0";
    default:
      return "Unknown";
  }
};

// ============================================================================
// URL Validation Utilities
// ============================================================================

export const isValidUrl = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

export const normalizeUrl = (url: string): string => {
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    return `http://${url}`;
  }
  return url;
};

// ============================================================================
// OpenAPI Content Validation
// ============================================================================

export const validateOpenApiContent = (content: unknown): boolean => {
  if (typeof content !== "object" || content === null) {
    return false;
  }

  const obj = content as Record<string, unknown>;

  // Check for required OpenAPI fields
  if (!("openapi" in obj || "swagger" in obj)) {
    return false;
  }

  if (!("info" in obj)) {
    return false;
  }

  return true;
};

export const extractOpenApiInfo = (
  content: Record<string, unknown>,
): {
  title?: string;
  version?: string;
  description?: string;
} => {
  const info = content.info as Record<string, unknown> | undefined;

  if (!info || typeof info !== "object") {
    return {};
  }

  return {
    title: typeof info.title === "string" ? info.title : undefined,
    version: typeof info.version === "string" ? info.version : undefined,
    description:
      typeof info.description === "string" ? info.description : undefined,
  };
};

// ============================================================================
// Pagination Utilities
// ============================================================================

export const calculateTotalPages = (
  total: number,
  pageSize: number,
): number => {
  return Math.ceil(total / pageSize);
};

export const getPageNumbers = (
  currentPage: number,
  totalPages: number,
  maxVisible: number = 5,
): number[] => {
  const pages: number[] = [];
  const half = Math.floor(maxVisible / 2);

  let start = Math.max(1, currentPage - half);
  const end = Math.min(totalPages, start + maxVisible - 1);

  // Adjust start if we're near the end
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1);
  }

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  return pages;
};

// ============================================================================
// Date Formatting Utilities
// ============================================================================

export const formatDateTime = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return date.toLocaleString();
  } catch {
    return "Invalid date";
  }
};

export const formatRelativeTime = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) {
      return "Just now";
    } else if (diffMins < 60) {
      return `${diffMins} minute${diffMins === 1 ? "" : "s"} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
    } else {
      return formatDateTime(dateString);
    }
  } catch {
    return "Invalid date";
  }
};
