/**
 * Example usage of the API client
 * This file demonstrates how to use the API client for various operations
 */

import apiClient, {
  APISpecificationCreate,
  AuthMethod,
  ValidationRunCreate,
  WireMockGenerateRequest,
} from "./api";
import {
  extractOpenApiInfo,
  formatApiError,
  getStoredApiKey,
  saveApiKey,
  validateOpenApiContent,
} from "./apiUtils";

// ============================================================================
// Authentication Example
// ============================================================================

export const setupAuthentication = (apiKey: string): void => {
  // Save API key to localStorage
  saveApiKey(apiKey);

  // Set API key in the client
  apiClient.setApiKey(apiKey);
};

export const initializeFromStoredAuth = (): boolean => {
  const storedApiKey = getStoredApiKey();
  if (storedApiKey) {
    apiClient.setApiKey(storedApiKey);
    return true;
  }
  return false;
};

// ============================================================================
// API Specifications Example
// ============================================================================

export const createApiSpecification = async (
  name: string,
  version: string,
  openApiContent: Record<string, unknown>,
): Promise<void> => {
  try {
    // Validate OpenAPI content first
    if (!validateOpenApiContent(openApiContent)) {
      throw new Error("Invalid OpenAPI content");
    }

    // Extract info for logging
    const info = extractOpenApiInfo(openApiContent);
    console.log(
      `Creating specification: ${info.title || name} v${
        info.version || version
      }`,
    );

    const specData: APISpecificationCreate = {
      name,
      version_string: version,
      openapi_content: openApiContent,
    };

    const result = await apiClient.createSpecification(specData);
    console.log("Specification created:", result);
  } catch (error) {
    console.error("Failed to create specification:", formatApiError(error));
    throw error;
  }
};

export const listApiSpecifications = async (): Promise<void> => {
  try {
    const result = await apiClient.getSpecifications({
      page: 1,
      size: 10,
      sort_by: "created_at",
      sort_order: "desc",
    });

    console.log(`Found ${result.total} specifications:`);
    result.items.forEach((spec) => {
      console.log(`- ${spec.name} v${spec.version_string} (ID: ${spec.id})`);
    });
  } catch (error) {
    console.error("Failed to list specifications:", formatApiError(error));
    throw error;
  }
};

// ============================================================================
// Validation Example
// ============================================================================

export const triggerValidation = async (
  specificationId: number,
  providerUrl: string,
): Promise<void> => {
  try {
    const validationData: ValidationRunCreate = {
      api_specification_id: specificationId,
      provider_url: providerUrl,
      auth_method: AuthMethod.NONE,
      max_examples: 50,
      timeout: 300,
    };

    const result = await apiClient.triggerValidation(validationData);
    console.log("Validation triggered:", result);

    // Poll for results (in a real app, you'd use a more sophisticated approach)
    await pollValidationResults(result.id);
  } catch (error) {
    console.error("Failed to trigger validation:", formatApiError(error));
    throw error;
  }
};

const pollValidationResults = async (validationId: number): Promise<void> => {
  const maxAttempts = 30; // 5 minutes with 10-second intervals
  let attempts = 0;

  while (attempts < maxAttempts) {
    try {
      const result = await apiClient.getValidationResults(validationId);

      console.log(`Validation ${validationId} status: ${result.status}`);

      if (result.status === "completed" || result.status === "failed") {
        console.log("Validation finished:", result);
        break;
      }

      // Wait 10 seconds before next poll
      await new Promise((resolve) => setTimeout(resolve, 10000));
      attempts++;
    } catch (error) {
      console.error("Error polling validation results:", formatApiError(error));
      break;
    }
  }
};

// ============================================================================
// WireMock Example
// ============================================================================

export const generateWireMockStubs = async (
  specificationId: number,
): Promise<void> => {
  try {
    const request: WireMockGenerateRequest = {
      specification_id: specificationId,
      clear_existing: true,
    };

    const result = await apiClient.generateWireMockStubs(request);
    console.log(`Generated ${result.stubs_created} WireMock stubs`);

    // List all stubs
    const stubs = await apiClient.getWireMockStubs();
    console.log(`Total stubs in WireMock: ${stubs.total_stubs}`);
  } catch (error) {
    console.error("Failed to generate WireMock stubs:", formatApiError(error));
    throw error;
  }
};

export const resetWireMock = async (): Promise<void> => {
  try {
    await apiClient.resetWireMock();
    console.log("WireMock reset successfully");
  } catch (error) {
    console.error("Failed to reset WireMock:", formatApiError(error));
    throw error;
  }
};

// ============================================================================
// Health Check Example
// ============================================================================

export const checkApiHealth = async (): Promise<boolean> => {
  try {
    const health = await apiClient.healthCheck();
    console.log("API health check:", health);
    return health.status === "ok" || health.status === "healthy";
  } catch (error) {
    console.error("Health check failed:", formatApiError(error));
    return false;
  }
};

// ============================================================================
// Complete Workflow Example
// ============================================================================

export const completeWorkflowExample = async (): Promise<void> => {
  try {
    // 1. Check API health
    const isHealthy = await checkApiHealth();
    if (!isHealthy) {
      throw new Error("API is not healthy");
    }

    // 2. Create a sample OpenAPI specification
    const sampleOpenApi = {
      openapi: "3.0.0",
      info: {
        title: "Sample API",
        version: "1.0.0",
        description: "A sample API for testing",
      },
      paths: {
        "/users": {
          get: {
            summary: "Get users",
            responses: {
              "200": {
                description: "Success",
                content: {
                  "application/json": {
                    schema: {
                      type: "array",
                      items: {
                        type: "object",
                        properties: {
                          id: { type: "integer" },
                          name: { type: "string" },
                        },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      },
    };

    // 3. Create the specification
    await createApiSpecification("Sample API", "1.0.0", sampleOpenApi);

    // 4. List specifications to get the ID
    await listApiSpecifications();

    // 5. Generate WireMock stubs (assuming specification ID 1)
    await generateWireMockStubs(1);

    // 6. Trigger validation (assuming a mock server at localhost:8080)
    await triggerValidation(1, "http://localhost:8080");

    console.log("Complete workflow executed successfully!");
  } catch (error) {
    console.error("Workflow failed:", formatApiError(error));
    throw error;
  }
};
