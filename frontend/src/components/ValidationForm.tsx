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
import { useApiClient } from "@/hooks/useApiClient";
import type { APISpecification, ValidationRunCreate } from "@/services/api";
import { AuthMethod } from "@/services/api";
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
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

interface ValidationFormData {
  api_specification_id: number | null;
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

export function ValidationForm({
  onValidationTriggered,
  onCancel,
  preselectedSpecificationId,
}: ValidationFormProps) {
  const apiClient = useApiClient();
  const [specifications, setSpecifications] = useState<APISpecification[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [formData, setFormData] = useState<ValidationFormData>({
    api_specification_id: preselectedSpecificationId || null,
    provider_url: "",
    auth_method: AuthMethod.NONE,
    auth_config: {},
    test_strategies: DEFAULT_TEST_STRATEGIES,
    max_examples: 100,
    timeout: 300,
  });

  // Load specifications
  const fetchSpecifications = useCallback(async () => {
    if (!apiClient) return;

    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getSpecifications({ size: 100 });
      setSpecifications(data.items);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load specifications";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    fetchSpecifications();
  }, [fetchSpecifications]);

  const handleInputChange = (
    field: keyof ValidationFormData,
    value: string | number | AuthMethod | null,
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
    if (!formData.provider_url.trim()) {
      return "Please enter a provider URL";
    }
    if (!formData.provider_url.match(/^https?:\/\/.+/)) {
      return "Provider URL must start with http:// or https://";
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
        provider_url: formData.provider_url.trim(),
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

  const renderAuthConfig = () => {
    switch (formData.auth_method) {
      case AuthMethod.API_KEY:
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="api_key">API Key</Label>
              <Input
                id="api_key"
                type="password"
                placeholder="Enter your API key"
                value={formData.auth_config.api_key || ""}
                onChange={(e) =>
                  handleAuthConfigChange("api_key", e.target.value)
                }
              />
            </div>
            <div>
              <Label htmlFor="api_key_header">Header Name (optional)</Label>
              <Input
                id="api_key_header"
                placeholder="X-API-Key"
                value={formData.auth_config.header_name || ""}
                onChange={(e) =>
                  handleAuthConfigChange("header_name", e.target.value)
                }
              />
              <p className="text-sm text-muted-foreground mt-1">
                Default: X-API-Key
              </p>
            </div>
          </div>
        );

      case AuthMethod.BEARER_TOKEN:
        return (
          <div>
            <Label htmlFor="bearer_token">Bearer Token</Label>
            <Input
              id="bearer_token"
              type="password"
              placeholder="Enter your bearer token"
              value={formData.auth_config.token || ""}
              onChange={(e) => handleAuthConfigChange("token", e.target.value)}
            />
          </div>
        );

      case AuthMethod.BASIC_AUTH:
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                placeholder="Enter username"
                value={formData.auth_config.username || ""}
                onChange={(e) =>
                  handleAuthConfigChange("username", e.target.value)
                }
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter password"
                value={formData.auth_config.password || ""}
                onChange={(e) =>
                  handleAuthConfigChange("password", e.target.value)
                }
              />
            </div>
          </div>
        );

      case AuthMethod.OAUTH2:
        return (
          <div>
            <Label htmlFor="access_token">Access Token</Label>
            <Input
              id="access_token"
              type="password"
              placeholder="Enter your OAuth2 access token"
              value={formData.auth_config.access_token || ""}
              onChange={(e) =>
                handleAuthConfigChange("access_token", e.target.value)
              }
            />
          </div>
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading specifications...
          </div>
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
          Run Schemathesis validation against your API provider
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-destructive" />
                <p className="text-destructive text-sm">{error}</p>
              </div>
            </div>
          )}

          {/* API Specification Selection */}
          <div>
            <Label htmlFor="specification">API Specification *</Label>
            <select
              id="specification"
              className="w-full mt-1 px-3 py-2 border border-input rounded-md bg-background"
              value={formData.api_specification_id || ""}
              onChange={(e) =>
                handleInputChange(
                  "api_specification_id",
                  parseInt(e.target.value) || null,
                )
              }
              required
            >
              <option value="">Select a specification...</option>
              {specifications.map((spec) => (
                <option key={spec.id} value={spec.id}>
                  {spec.name} (v{spec.version_string})
                </option>
              ))}
            </select>
          </div>

          {/* Provider URL */}
          <div>
            <Label htmlFor="provider_url">Provider URL *</Label>
            <Input
              id="provider_url"
              type="url"
              placeholder="https://api.example.com"
              value={formData.provider_url}
              onChange={(e) =>
                handleInputChange("provider_url", e.target.value)
              }
              required
            />
            <p className="text-sm text-muted-foreground mt-1">
              The base URL of your API provider to validate against
            </p>
          </div>

          {/* Authentication Method */}
          <div>
            <Label htmlFor="auth_method">Authentication Method</Label>
            <select
              id="auth_method"
              className="w-full mt-1 px-3 py-2 border border-input rounded-md bg-background"
              value={formData.auth_method}
              onChange={(e) =>
                handleInputChange("auth_method", e.target.value as AuthMethod)
              }
            >
              {AUTH_METHODS.map((method) => (
                <option key={method.value} value={method.value}>
                  {method.label} - {method.description}
                </option>
              ))}
            </select>
          </div>

          {/* Authentication Configuration */}
          {formData.auth_method !== AuthMethod.NONE && (
            <div className="space-y-2">
              <Label>Authentication Configuration</Label>
              <div className="border rounded-lg p-4 bg-muted/50">
                {renderAuthConfig()}
              </div>
            </div>
          )}

          {/* Advanced Settings */}
          <div>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 p-0 h-auto"
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
              <div className="mt-4 space-y-4 border rounded-lg p-4 bg-muted/50">
                {/* Test Strategies */}
                <div>
                  <Label>Test Strategies</Label>
                  <div className="mt-2 space-y-2">
                    {DEFAULT_TEST_STRATEGIES.map((strategy) => (
                      <label key={strategy} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={formData.test_strategies.includes(strategy)}
                          onChange={() => handleTestStrategyToggle(strategy)}
                          className="rounded"
                        />
                        <span className="text-sm">
                          {strategy.replace(/_/g, " ")}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Max Examples */}
                <div>
                  <Label htmlFor="max_examples">Max Examples</Label>
                  <Input
                    id="max_examples"
                    type="number"
                    min="1"
                    max="1000"
                    value={formData.max_examples}
                    onChange={(e) =>
                      handleInputChange(
                        "max_examples",
                        parseInt(e.target.value) || 100,
                      )
                    }
                  />
                  <p className="text-sm text-muted-foreground mt-1">
                    Maximum number of test examples to generate (1-1000)
                  </p>
                </div>

                {/* Timeout */}
                <div>
                  <Label htmlFor="timeout">Timeout (seconds)</Label>
                  <Input
                    id="timeout"
                    type="number"
                    min="30"
                    max="3600"
                    value={formData.timeout}
                    onChange={(e) =>
                      handleInputChange(
                        "timeout",
                        parseInt(e.target.value) || 300,
                      )
                    }
                  />
                  <p className="text-sm text-muted-foreground mt-1">
                    Validation timeout in seconds (30-3600)
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={submitting} className="flex-1">
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Triggering Validation...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
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
