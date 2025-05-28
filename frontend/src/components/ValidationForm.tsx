import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useApiClient } from "@/hooks/useApiClient";
import type {
  APISpecification,
  Environment,
  ValidationRunCreate,
} from "@/services/api";
import { AuthMethod, EnvironmentType } from "@/services/api";
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Globe,
  Link,
  Loader2,
  Play,
  Server,
  Settings,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

interface ValidationFormProps {
  onValidationTriggered?: (validationId: number) => void;
  onCancel?: () => void;
  preselectedSpecificationId?: number;
}

type ProviderSelectionMode = "environment" | "custom";

interface ValidationFormData {
  api_specification_id: number | null;
  provider_selection_mode: ProviderSelectionMode;
  environment_id: number | null;
  provider_url: string;
  selected_environment_option: string | null;
  auth_method: AuthMethod;
  auth_config: Record<string, string>;
  test_strategies: string[];
  max_examples: number;
  timeout: number;
}

// Interface for OpenAPI server definitions
interface OpenAPIServer {
  url: string;
  description?: string;
}

// Combined environment option (either user environment, OpenAPI server, or mock deployment)
interface EnvironmentOption {
  id: string;
  name: string;
  url: string;
  type: "user-environment" | "openapi-server" | "mock-deployment";
  description?: string;
  environment_type?: EnvironmentType;
  isAvailable?: boolean; // For mock deployments, indicates if mocks are deployed
}

const AUTH_METHODS: {
  value: AuthMethod;
  label: string;
  description: string;
}[] = [
  {
    value: AuthMethod.NONE,
    label: "None",
    description: "No authentication required",
  },
  {
    value: AuthMethod.API_KEY,
    label: "API Key",
    description: "API key in header or query parameter",
  },
  {
    value: AuthMethod.BEARER_TOKEN,
    label: "Bearer Token",
    description: "Bearer token in Authorization header",
  },
  {
    value: AuthMethod.BASIC_AUTH,
    label: "Basic Auth",
    description: "Username and password authentication",
  },
  {
    value: AuthMethod.OAUTH2,
    label: "OAuth2",
    description: "OAuth2 token-based authentication",
  },
];

const DEFAULT_TEST_STRATEGIES = [
  "path_parameters",
  "query_parameters",
  "headers",
  "request_body",
  "response_validation",
];

const ENVIRONMENT_TYPE_LABELS: Record<EnvironmentType, string> = {
  [EnvironmentType.PRODUCTION]: "Production",
  [EnvironmentType.STAGING]: "Staging",
  [EnvironmentType.DEVELOPMENT]: "Development",
  [EnvironmentType.CUSTOM]: "Custom",
};

export function ValidationForm({
  onValidationTriggered,
  onCancel,
  preselectedSpecificationId,
}: ValidationFormProps) {
  const apiClient = useApiClient();
  const [specifications, setSpecifications] = useState<APISpecification[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [mockDeploymentStatus, setMockDeploymentStatus] = useState<
    Record<number, { isDeployed: boolean; stubCount: number }>
  >({});
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [formData, setFormData] = useState<ValidationFormData>({
    api_specification_id: preselectedSpecificationId || null,
    provider_selection_mode: "environment",
    environment_id: null,
    provider_url: "",
    selected_environment_option: null,
    auth_method: AuthMethod.NONE,
    auth_config: {},
    test_strategies: DEFAULT_TEST_STRATEGIES,
    max_examples: 100,
    timeout: 300,
  });

  // Extract OpenAPI servers from selected specification
  const extractOpenAPIServers = useCallback(
    (spec: APISpecification): OpenAPIServer[] => {
      try {
        const servers = spec.openapi_content?.servers;
        if (Array.isArray(servers)) {
          return servers
            .filter(
              (
                server: unknown,
              ): server is { url: string; description?: string } => {
                if (!server || typeof server !== "object" || server === null)
                  return false;
                const serverObj = server as Record<string, unknown>;
                return "url" in serverObj && typeof serverObj.url === "string";
              },
            )
            .map((server: { url: string; description?: string }) => ({
              url: server.url,
              description: server.description || undefined,
            }));
        }
      } catch (error) {
        console.warn(
          "Failed to extract servers from OpenAPI specification:",
          error,
        );
      }
      return [];
    },
    [],
  );

  // Get combined environment options (OpenAPI servers + user environments + mock deployments)
  const environmentOptions = useMemo((): EnvironmentOption[] => {
    const options: EnvironmentOption[] = [];

    // Add OpenAPI servers from selected specification
    if (formData.api_specification_id) {
      const selectedSpec = specifications.find(
        (spec) => spec.id === formData.api_specification_id,
      );
      if (selectedSpec) {
        const servers = extractOpenAPIServers(selectedSpec);
        servers.forEach((server, index) => {
          options.push({
            id: `openapi-server-${index}`,
            name: server.description || `Server ${index + 1}`,
            url: server.url,
            type: "openapi-server",
            description: server.description,
          });
        });

        // Add mock deployment option if available
        const mockStatus = mockDeploymentStatus[selectedSpec.id];
        if (mockStatus) {
          options.push({
            id: `mock-deployment-${selectedSpec.id}`,
            name: `Mock Server (${mockStatus.stubCount} stubs)`,
            url: "http://localhost:8081", // WireMock base URL
            type: "mock-deployment",
            description: mockStatus.isDeployed
              ? `Deployed mock server with ${mockStatus.stubCount} endpoints`
              : "Mock server not deployed",
            isAvailable: mockStatus.isDeployed,
          });
        }
      }
    }

    // Add user-defined environments
    environments.forEach((env) => {
      options.push({
        id: `user-env-${env.id}`,
        name: env.name,
        url: env.base_url,
        type: "user-environment",
        description: env.description,
        environment_type: env.environment_type,
      });
    });

    return options;
  }, [
    formData.api_specification_id,
    specifications,
    environments,
    extractOpenAPIServers,
    mockDeploymentStatus,
  ]);

  // Reset selected environment when API specification changes
  useEffect(() => {
    if (formData.api_specification_id) {
      setFormData((prev) => ({
        ...prev,
        selected_environment_option: null,
        environment_id: null,
        provider_url: "",
      }));
    }
  }, [formData.api_specification_id]);

  // Load specifications and environments
  const fetchData = useCallback(async () => {
    if (!apiClient) return;

    try {
      setLoading(true);
      setError(null);

      const [specificationsData, environmentsData] = await Promise.all([
        apiClient.getSpecifications({ size: 100 }),
        apiClient.getEnvironments({ size: 100, is_active: "true" }),
      ]);

      setSpecifications(specificationsData.items);
      setEnvironments(environmentsData.items);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load data";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Load mock deployment status for specifications
  const loadMockDeploymentStatus = useCallback(async () => {
    if (!apiClient || specifications.length === 0) return;

    try {
      const statusMap: Record<
        number,
        { isDeployed: boolean; stubCount: number }
      > = {};

      // Check mock deployment status for each specification
      for (const spec of specifications) {
        try {
          const response = await apiClient.getWireMockStubs(spec.id);
          statusMap[spec.id] = {
            isDeployed: response.total_stubs > 0,
            stubCount: response.total_stubs,
          };
        } catch {
          // If we can't get status, assume not deployed
          statusMap[spec.id] = {
            isDeployed: false,
            stubCount: 0,
          };
        }
      }

      setMockDeploymentStatus(statusMap);
    } catch (error) {
      console.warn("Failed to load mock deployment status:", error);
    }
  }, [apiClient, specifications]);

  // Load mock deployment status when specifications change
  useEffect(() => {
    loadMockDeploymentStatus();
  }, [loadMockDeploymentStatus]);

  const handleInputChange = (
    field: keyof ValidationFormData,
    value: string | number | AuthMethod | ProviderSelectionMode | null,
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleAuthConfigChange = (key: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      auth_config: { ...prev.auth_config, [key]: value },
    }));
  };

  const handleTestStrategyToggle = (strategy: string) => {
    setFormData((prev) => ({
      ...prev,
      test_strategies: prev.test_strategies.includes(strategy)
        ? prev.test_strategies.filter((s) => s !== strategy)
        : [...prev.test_strategies, strategy],
    }));
  };

  const validateForm = (): string | null => {
    if (!formData.api_specification_id) {
      return "Please select an API specification";
    }

    if (formData.provider_selection_mode === "environment") {
      if (!formData.selected_environment_option) {
        return "Please select an environment or server";
      }
    } else {
      if (!formData.provider_url.trim()) {
        return "Please enter a provider URL";
      }
      if (!formData.provider_url.match(/^https?:\/\/.+/)) {
        return "Provider URL must start with http:// or https://";
      }
    }

    if (
      formData.auth_method === AuthMethod.API_KEY &&
      !formData.auth_config.api_key
    ) {
      return "API key is required for API key authentication";
    }
    if (
      formData.auth_method === AuthMethod.BEARER_TOKEN &&
      !formData.auth_config.token
    ) {
      return "Bearer token is required for bearer token authentication";
    }
    if (
      formData.auth_method === AuthMethod.BASIC_AUTH &&
      (!formData.auth_config.username || !formData.auth_config.password)
    ) {
      return "Username and password are required for basic authentication";
    }
    if (
      formData.auth_method === AuthMethod.OAUTH2 &&
      !formData.auth_config.access_token
    ) {
      return "Access token is required for OAuth2 authentication";
    }
    return null;
  };

  // Get the selected environment option details
  const getSelectedEnvironmentDetails = useCallback(() => {
    if (!formData.selected_environment_option) return null;
    return environmentOptions.find(
      (option) => option.id === formData.selected_environment_option,
    );
  }, [formData.selected_environment_option, environmentOptions]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    if (!apiClient) {
      setError("API client not available");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      const validationData: ValidationRunCreate = {
        api_specification_id: formData.api_specification_id!,
        auth_method: formData.auth_method,
        auth_config:
          Object.keys(formData.auth_config).length > 0
            ? formData.auth_config
            : undefined,
        test_strategies:
          formData.test_strategies.length > 0
            ? formData.test_strategies
            : undefined,
        max_examples: formData.max_examples,
        timeout: formData.timeout,
      };

      // Handle environment/server selection
      if (formData.provider_selection_mode === "environment") {
        const selectedOption = getSelectedEnvironmentDetails();
        if (selectedOption) {
          if (selectedOption.type === "user-environment") {
            // Extract environment ID from the option ID
            const envId = parseInt(selectedOption.id.replace("user-env-", ""));
            validationData.environment_id = envId;
          } else {
            // For OpenAPI servers and mock deployments, use the URL directly
            validationData.provider_url = selectedOption.url;
          }
        }
      } else {
        validationData.provider_url = formData.provider_url;
      }

      const result = await apiClient.triggerValidation(validationData);
      onValidationTriggered?.(result.id);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to trigger validation";
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const renderProviderSelection = () => {
    return (
      <div className="space-y-4">
        <Label className="text-base font-medium">Provider Selection</Label>

        <RadioGroup
          value={formData.provider_selection_mode}
          onValueChange={(value: ProviderSelectionMode) =>
            handleInputChange("provider_selection_mode", value)
          }
          className="grid grid-cols-2 gap-4"
        >
          <div className="flex items-center space-x-2 rounded-lg border p-4">
            <RadioGroupItem value="environment" id="environment" />
            <div className="grid gap-1.5 leading-none">
              <Label
                htmlFor="environment"
                className="flex items-center gap-2 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                <Globe className="h-4 w-4" />
                Select Environment
              </Label>
              <p className="text-xs text-muted-foreground">
                Choose from predefined environments
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 rounded-lg border p-4">
            <RadioGroupItem value="custom" id="custom" />
            <div className="grid gap-1.5 leading-none">
              <Label
                htmlFor="custom"
                className="flex items-center gap-2 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                <Link className="h-4 w-4" />
                Custom URL
              </Label>
              <p className="text-xs text-muted-foreground">
                Enter a custom provider URL
              </p>
            </div>
          </div>
        </RadioGroup>

        {formData.provider_selection_mode === "environment" ? (
          <div className="space-y-2">
            <Label htmlFor="environment_option">Environment / Server</Label>
            <select
              id="environment_option"
              value={formData.selected_environment_option || ""}
              onChange={(e) =>
                handleInputChange(
                  "selected_environment_option",
                  e.target.value || null,
                )
              }
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={loading}
            >
              <option value="">Select an environment or server...</option>

              {/* Group OpenAPI servers */}
              {environmentOptions.filter(
                (option) => option.type === "openapi-server",
              ).length > 0 && (
                <optgroup label="📋 Specification Servers">
                  {environmentOptions
                    .filter((option) => option.type === "openapi-server")
                    .map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name} - {option.url}
                      </option>
                    ))}
                </optgroup>
              )}

              {/* Group mock deployments */}
              {environmentOptions.filter(
                (option) => option.type === "mock-deployment",
              ).length > 0 && (
                <optgroup label="🔧 Mock Deployments">
                  {environmentOptions
                    .filter((option) => option.type === "mock-deployment")
                    .map((option) => (
                      <option
                        key={option.id}
                        value={option.id}
                        disabled={!option.isAvailable}
                      >
                        {option.name} - {option.url}
                        {!option.isAvailable && " (Not Deployed)"}
                      </option>
                    ))}
                </optgroup>
              )}

              {/* Group user environments */}
              {environmentOptions.filter(
                (option) => option.type === "user-environment",
              ).length > 0 && (
                <optgroup label="🌍 User Environments">
                  {environmentOptions
                    .filter((option) => option.type === "user-environment")
                    .map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name} (
                        {ENVIRONMENT_TYPE_LABELS[option.environment_type!]}) -{" "}
                        {option.url}
                      </option>
                    ))}
                </optgroup>
              )}
            </select>

            {environmentOptions.length === 0 && !loading && (
              <p className="text-sm text-muted-foreground">
                {formData.api_specification_id
                  ? "No servers defined in the specification, no mock deployments available, and no user environments found. You can deploy mocks, create environments in Settings, or use a custom URL."
                  : "Please select an API specification first."}
              </p>
            )}

            {/* Show selected environment details */}
            {formData.selected_environment_option && (
              <div className="mt-2 p-3 bg-muted/50 rounded-lg">
                {(() => {
                  const selectedOption = getSelectedEnvironmentDetails();
                  if (!selectedOption) return null;

                  return (
                    <div className="flex items-start gap-2">
                      {selectedOption.type === "openapi-server" ? (
                        <Server className="h-4 w-4 mt-0.5 text-blue-600" />
                      ) : selectedOption.type === "mock-deployment" ? (
                        <div className="flex items-center gap-1">
                          <Server className="h-4 w-4 mt-0.5 text-orange-600" />
                          {selectedOption.isAvailable ? (
                            <div
                              className="h-2 w-2 bg-green-500 rounded-full"
                              title="Mock server is deployed"
                            />
                          ) : (
                            <div
                              className="h-2 w-2 bg-red-500 rounded-full"
                              title="Mock server not deployed"
                            />
                          )}
                        </div>
                      ) : (
                        <Globe className="h-4 w-4 mt-0.5 text-green-600" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">
                          {selectedOption.name}
                        </p>
                        <p className="text-xs text-muted-foreground break-all">
                          {selectedOption.url}
                        </p>
                        {selectedOption.description && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {selectedOption.description}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                          {selectedOption.type === "openapi-server"
                            ? "From API specification"
                            : selectedOption.type === "mock-deployment"
                            ? selectedOption.isAvailable
                              ? "Deployed mock server (ready for testing)"
                              : "Mock server not deployed (deploy first)"
                            : `User environment (${
                                ENVIRONMENT_TYPE_LABELS[
                                  selectedOption.environment_type!
                                ]
                              })`}
                        </p>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <Label htmlFor="provider_url">Provider URL</Label>
            <Input
              id="provider_url"
              type="url"
              placeholder="https://api.example.com"
              value={formData.provider_url}
              onChange={(e) =>
                handleInputChange("provider_url", e.target.value)
              }
              disabled={submitting}
            />
            <p className="text-sm text-muted-foreground">
              The base URL of your API implementation to validate against the
              specification
            </p>
          </div>
        )}
      </div>
    );
  };

  const renderAuthConfig = () => {
    if (formData.auth_method === AuthMethod.NONE) {
      return null;
    }

    return (
      <div className="space-y-4">
        <Label className="text-base font-medium">
          Authentication Configuration
        </Label>

        {formData.auth_method === AuthMethod.API_KEY && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="api_key">API Key</Label>
              <Input
                id="api_key"
                type="password"
                placeholder="Enter your API key"
                value={formData.auth_config.api_key || ""}
                onChange={(e) =>
                  handleAuthConfigChange("api_key", e.target.value)
                }
                disabled={submitting}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="header_name">Header Name (optional)</Label>
              <Input
                id="header_name"
                placeholder="X-API-Key"
                value={formData.auth_config.header_name || ""}
                onChange={(e) =>
                  handleAuthConfigChange("header_name", e.target.value)
                }
                disabled={submitting}
              />
              <p className="text-sm text-muted-foreground">
                Default: X-API-Key
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="in_query"
                checked={formData.auth_config.in_query === "true"}
                onChange={(e) =>
                  handleAuthConfigChange(
                    "in_query",
                    e.target.checked ? "true" : "false",
                  )
                }
                disabled={submitting}
                className="h-4 w-4 rounded border-gray-300"
              />
              <Label htmlFor="in_query" className="text-sm">
                Send API key as query parameter instead of header
              </Label>
            </div>
            {formData.auth_config.in_query === "true" && (
              <div className="space-y-2">
                <Label htmlFor="param_name">Parameter Name</Label>
                <Input
                  id="param_name"
                  placeholder="api_key"
                  value={formData.auth_config.param_name || ""}
                  onChange={(e) =>
                    handleAuthConfigChange("param_name", e.target.value)
                  }
                  disabled={submitting}
                />
              </div>
            )}
          </div>
        )}

        {formData.auth_method === AuthMethod.BEARER_TOKEN && (
          <div className="space-y-2">
            <Label htmlFor="token">Bearer Token</Label>
            <Input
              id="token"
              type="password"
              placeholder="Enter your bearer token"
              value={formData.auth_config.token || ""}
              onChange={(e) => handleAuthConfigChange("token", e.target.value)}
              disabled={submitting}
            />
          </div>
        )}

        {formData.auth_method === AuthMethod.BASIC_AUTH && (
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                placeholder="Enter username"
                value={formData.auth_config.username || ""}
                onChange={(e) =>
                  handleAuthConfigChange("username", e.target.value)
                }
                disabled={submitting}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter password"
                value={formData.auth_config.password || ""}
                onChange={(e) =>
                  handleAuthConfigChange("password", e.target.value)
                }
                disabled={submitting}
              />
            </div>
          </div>
        )}

        {formData.auth_method === AuthMethod.OAUTH2 && (
          <div className="space-y-2">
            <Label htmlFor="access_token">Access Token</Label>
            <Input
              id="access_token"
              type="password"
              placeholder="Enter your OAuth2 access token"
              value={formData.auth_config.access_token || ""}
              onChange={(e) =>
                handleAuthConfigChange("access_token", e.target.value)
              }
              disabled={submitting}
            />
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-6">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span className="ml-2">Loading...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Play className="h-5 w-5" />
          Trigger Validation
        </CardTitle>
        <CardDescription>
          Validate your API provider implementation against an OpenAPI
          specification
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          {/* API Specification Selection */}
          <div className="space-y-2">
            <Label htmlFor="api_specification_id">API Specification</Label>
            <select
              id="api_specification_id"
              value={formData.api_specification_id || ""}
              onChange={(e) =>
                handleInputChange(
                  "api_specification_id",
                  e.target.value ? parseInt(e.target.value) : null,
                )
              }
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={submitting}
            >
              <option value="">Select a specification...</option>
              {specifications.map((spec) => (
                <option key={spec.id} value={spec.id}>
                  {spec.name} (v{spec.version_string})
                </option>
              ))}
            </select>
          </div>

          {/* Provider Selection */}
          {renderProviderSelection()}

          {/* Authentication Method */}
          <div className="space-y-2">
            <Label htmlFor="auth_method">Authentication Method</Label>
            <select
              id="auth_method"
              value={formData.auth_method}
              onChange={(e) =>
                handleInputChange("auth_method", e.target.value as AuthMethod)
              }
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={submitting}
            >
              {AUTH_METHODS.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label} - {method.description}
                </option>
              ))}
            </select>
          </div>

          {/* Authentication Configuration */}
          {renderAuthConfig()}

          {/* Advanced Settings */}
          <div className="space-y-4">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 p-0 h-auto font-medium"
            >
              <Settings className="h-4 w-4" />
              Advanced Settings
              {showAdvanced ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>

            {showAdvanced && (
              <div className="space-y-4 rounded-lg border p-4">
                {/* Test Strategies */}
                <div className="space-y-2">
                  <Label className="text-base font-medium">
                    Test Strategies
                  </Label>
                  <div className="grid grid-cols-2 gap-2">
                    {DEFAULT_TEST_STRATEGIES.map((strategy) => (
                      <div
                        key={strategy}
                        className="flex items-center space-x-2"
                      >
                        <input
                          type="checkbox"
                          id={strategy}
                          checked={formData.test_strategies.includes(strategy)}
                          onChange={() => handleTestStrategyToggle(strategy)}
                          disabled={submitting}
                          className="h-4 w-4 rounded border-gray-300"
                        />
                        <Label htmlFor={strategy} className="text-sm">
                          {strategy.replace(/_/g, " ")}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Max Examples */}
                <div className="space-y-2">
                  <Label htmlFor="max_examples">Maximum Test Examples</Label>
                  <Input
                    id="max_examples"
                    type="number"
                    min="1"
                    max="1000"
                    value={formData.max_examples}
                    onChange={(e) =>
                      handleInputChange(
                        "max_examples",
                        parseInt(e.target.value),
                      )
                    }
                    disabled={submitting}
                  />
                  <p className="text-sm text-muted-foreground">
                    Number of test cases to generate (1-1000)
                  </p>
                </div>

                {/* Timeout */}
                <div className="space-y-2">
                  <Label htmlFor="timeout">Timeout (seconds)</Label>
                  <Input
                    id="timeout"
                    type="number"
                    min="30"
                    max="3600"
                    value={formData.timeout}
                    onChange={(e) =>
                      handleInputChange("timeout", parseInt(e.target.value))
                    }
                    disabled={submitting}
                  />
                  <p className="text-sm text-muted-foreground">
                    Maximum time to wait for validation completion (30-3600
                    seconds)
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Form Actions */}
          <div className="flex gap-3">
            <Button type="submit" disabled={submitting} className="flex-1">
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Triggering Validation...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Trigger Validation
                </>
              )}
            </Button>
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
