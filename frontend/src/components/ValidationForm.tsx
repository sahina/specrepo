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
  Settings,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

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
  auth_method: AuthMethod;
  auth_config: Record<string, string>;
  test_strategies: string[];
  max_examples: number;
  timeout: number;
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
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [formData, setFormData] = useState<ValidationFormData>({
    api_specification_id: preselectedSpecificationId || null,
    provider_selection_mode: "environment",
    environment_id: null,
    provider_url: "",
    auth_method: AuthMethod.NONE,
    auth_config: {},
    test_strategies: DEFAULT_TEST_STRATEGIES,
    max_examples: 100,
    timeout: 300,
  });

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
      if (!formData.environment_id) {
        return "Please select an environment";
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

      // Add either environment_id or provider_url based on selection mode
      if (formData.provider_selection_mode === "environment") {
        validationData.environment_id = formData.environment_id!;
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
            <Label htmlFor="environment_id">Environment</Label>
            <select
              id="environment_id"
              value={formData.environment_id || ""}
              onChange={(e) =>
                handleInputChange(
                  "environment_id",
                  e.target.value ? parseInt(e.target.value) : null,
                )
              }
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={loading}
            >
              <option value="">Select an environment...</option>
              {environments.map((env) => (
                <option key={env.id} value={env.id}>
                  {env.name} ({ENVIRONMENT_TYPE_LABELS[env.environment_type]}) -{" "}
                  {env.base_url}
                </option>
              ))}
            </select>
            {environments.length === 0 && !loading && (
              <p className="text-sm text-muted-foreground">
                No environments available. You can create environments in the
                Settings page.
              </p>
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
