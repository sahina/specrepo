import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useApiClient } from "@/hooks/useApiClient";
import type { Environment, EnvironmentCreate } from "@/services/api";
import { EnvironmentType } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import {
  AlertCircle,
  Bell,
  Globe,
  Key,
  Plus,
  Save,
  Settings as SettingsIcon,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const ENVIRONMENT_TYPE_LABELS: Record<EnvironmentType, string> = {
  [EnvironmentType.PRODUCTION]: "Production",
  [EnvironmentType.STAGING]: "Staging",
  [EnvironmentType.DEVELOPMENT]: "Development",
  [EnvironmentType.CUSTOM]: "Custom",
};

export function Settings() {
  const { apiKey } = useAuthStore();
  const apiClient = useApiClient();
  const [notifications, setNotifications] = useState({
    email: true,
    webhook: false,
    slack: false,
  });
  const [webhookUrl, setWebhookUrl] = useState("");
  const [slackWebhook, setSlackWebhook] = useState("");

  // Environment management state
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loadingEnvironments, setLoadingEnvironments] = useState(false);
  const [environmentError, setEnvironmentError] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [creatingEnvironment, setCreatingEnvironment] = useState(false);
  const [newEnvironment, setNewEnvironment] = useState<EnvironmentCreate>({
    name: "",
    base_url: "",
    description: "",
    environment_type: EnvironmentType.CUSTOM,
  });

  // Load environments
  const fetchEnvironments = useCallback(async () => {
    if (!apiClient) return;

    try {
      setLoadingEnvironments(true);
      setEnvironmentError(null);
      const response = await apiClient.getEnvironments({ size: 100 });
      setEnvironments(response.items);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load environments";
      setEnvironmentError(errorMessage);
    } finally {
      setLoadingEnvironments(false);
    }
  }, [apiClient]);

  useEffect(() => {
    fetchEnvironments();
  }, [fetchEnvironments]);

  const handleSaveSettings = () => {
    // TODO: Implement settings save functionality
    console.log("Saving settings:", {
      notifications,
      webhookUrl,
      slackWebhook,
    });
  };

  const handleCreateEnvironment = async () => {
    if (!apiClient) return;

    try {
      setCreatingEnvironment(true);
      setEnvironmentError(null);

      await apiClient.createEnvironment(newEnvironment);

      // Reset form and close dialog
      setNewEnvironment({
        name: "",
        base_url: "",
        description: "",
        environment_type: EnvironmentType.CUSTOM,
      });
      setShowCreateDialog(false);

      // Refresh environments list
      await fetchEnvironments();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to create environment";
      setEnvironmentError(errorMessage);
    } finally {
      setCreatingEnvironment(false);
    }
  };

  const handleDeleteEnvironment = async (envId: number) => {
    if (!apiClient) return;

    if (!confirm("Are you sure you want to delete this environment?")) {
      return;
    }

    try {
      setEnvironmentError(null);
      await apiClient.deleteEnvironment(envId);
      await fetchEnvironments();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to delete environment";
      setEnvironmentError(errorMessage);
    }
  };

  // Mask the API key for display
  const maskedApiKey = apiKey
    ? `${apiKey.slice(0, 8)}${"*".repeat(
        Math.max(0, apiKey.length - 16),
      )}${apiKey.slice(-8)}`
    : "";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <SettingsIcon className="h-8 w-8" />
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-muted-foreground">
            Manage your application preferences and integrations
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Environment Management */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  Environment Management
                </CardTitle>
                <CardDescription>
                  Manage your API environments for validation testing
                </CardDescription>
              </div>
              <Dialog
                open={showCreateDialog}
                onOpenChange={setShowCreateDialog}
              >
                <DialogTrigger asChild>
                  <Button className="flex items-center gap-2">
                    <Plus className="h-4 w-4" />
                    Add Environment
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create New Environment</DialogTitle>
                    <DialogDescription>
                      Add a new environment for API validation testing.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="env-name">Name</Label>
                      <Input
                        id="env-name"
                        placeholder="e.g., Production API"
                        value={newEnvironment.name}
                        onChange={(e) =>
                          setNewEnvironment((prev) => ({
                            ...prev,
                            name: e.target.value,
                          }))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="env-url">Base URL</Label>
                      <Input
                        id="env-url"
                        placeholder="https://api.example.com"
                        value={newEnvironment.base_url}
                        onChange={(e) =>
                          setNewEnvironment((prev) => ({
                            ...prev,
                            base_url: e.target.value,
                          }))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="env-type">Environment Type</Label>
                      <select
                        id="env-type"
                        value={newEnvironment.environment_type}
                        onChange={(e) =>
                          setNewEnvironment((prev) => ({
                            ...prev,
                            environment_type: e.target.value as EnvironmentType,
                          }))
                        }
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {Object.entries(ENVIRONMENT_TYPE_LABELS).map(
                          ([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ),
                        )}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="env-description">
                        Description (Optional)
                      </Label>
                      <Input
                        id="env-description"
                        placeholder="Brief description of this environment"
                        value={newEnvironment.description}
                        onChange={(e) =>
                          setNewEnvironment((prev) => ({
                            ...prev,
                            description: e.target.value,
                          }))
                        }
                      />
                    </div>
                  </div>
                  {environmentError && (
                    <div className="flex items-center gap-2 text-sm text-red-600">
                      <AlertCircle className="h-4 w-4" />
                      {environmentError}
                    </div>
                  )}
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setShowCreateDialog(false)}
                      disabled={creatingEnvironment}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleCreateEnvironment}
                      disabled={
                        creatingEnvironment ||
                        !newEnvironment.name.trim() ||
                        !newEnvironment.base_url.trim()
                      }
                    >
                      {creatingEnvironment
                        ? "Creating..."
                        : "Create Environment"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </CardHeader>
          <CardContent>
            {loadingEnvironments ? (
              <div className="text-center py-4">Loading environments...</div>
            ) : environments.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Globe className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">
                  No environments configured
                </p>
                <p className="text-sm">
                  Create your first environment to start using predefined API
                  endpoints for validation.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {environments.map((env) => (
                  <div
                    key={env.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{env.name}</h4>
                        <span className="text-xs px-2 py-1 bg-secondary rounded-full">
                          {ENVIRONMENT_TYPE_LABELS[env.environment_type]}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {env.base_url}
                      </p>
                      {env.description && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {env.description}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteEnvironment(env.id)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
            {environmentError && !loadingEnvironments && (
              <div className="flex items-center gap-2 text-sm text-red-600 mt-4">
                <AlertCircle className="h-4 w-4" />
                {environmentError}
              </div>
            )}
          </CardContent>
        </Card>

        {/* API Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Configuration
            </CardTitle>
            <CardDescription>
              Your API key and authentication settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="api-key">API Key</Label>
              <Input
                id="api-key"
                value={maskedApiKey}
                readOnly
                className="font-mono"
              />
              <p className="text-sm text-muted-foreground">
                Your API key is securely stored and cannot be modified here.
                Contact your administrator to update it.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
            <CardDescription>
              Configure how you receive validation results
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="email-notifications">Email Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Receive validation results via email
                </p>
              </div>
              <Switch
                id="email-notifications"
                checked={notifications.email}
                onCheckedChange={(checked: boolean) =>
                  setNotifications((prev) => ({ ...prev, email: checked }))
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="webhook-notifications">
                  Webhook Notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  Send results to a custom webhook URL
                </p>
              </div>
              <Switch
                id="webhook-notifications"
                checked={notifications.webhook}
                onCheckedChange={(checked: boolean) =>
                  setNotifications((prev) => ({ ...prev, webhook: checked }))
                }
              />
            </div>

            {notifications.webhook && (
              <div className="space-y-2">
                <Label htmlFor="webhook-url">Webhook URL</Label>
                <Input
                  id="webhook-url"
                  placeholder="https://your-webhook-url.com/endpoint"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                />
              </div>
            )}

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="slack-notifications">Slack Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Send results to a Slack channel
                </p>
              </div>
              <Switch
                id="slack-notifications"
                checked={notifications.slack}
                onCheckedChange={(checked: boolean) =>
                  setNotifications((prev) => ({ ...prev, slack: checked }))
                }
              />
            </div>

            {notifications.slack && (
              <div className="space-y-2">
                <Label htmlFor="slack-webhook">Slack Webhook URL</Label>
                <Input
                  id="slack-webhook"
                  placeholder="https://hooks.slack.com/services/..."
                  value={slackWebhook}
                  onChange={(e) => setSlackWebhook(e.target.value)}
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Validation Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Validation Settings</CardTitle>
            <CardDescription>
              Default settings for API validations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="max-examples">Max Examples per Endpoint</Label>
              <Input
                id="max-examples"
                type="number"
                placeholder="50"
                min="1"
                max="1000"
              />
              <p className="text-sm text-muted-foreground">
                Maximum number of test examples to generate per endpoint
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeout">Validation Timeout (seconds)</Label>
              <Input
                id="timeout"
                type="number"
                placeholder="300"
                min="30"
                max="3600"
              />
              <p className="text-sm text-muted-foreground">
                Maximum time to wait for validation completion
              </p>
            </div>
          </CardContent>
        </Card>

        {/* System Information */}
        <Card>
          <CardHeader>
            <CardTitle>System Information</CardTitle>
            <CardDescription>
              Application and environment details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="font-medium">Version</p>
                <p className="text-muted-foreground">1.0.0</p>
              </div>
              <div>
                <p className="font-medium">Environment</p>
                <p className="text-muted-foreground">Development</p>
              </div>
              <div>
                <p className="font-medium">API Status</p>
                <p className="text-green-600">Connected</p>
              </div>
              <div>
                <p className="font-medium">Last Updated</p>
                <p className="text-muted-foreground">
                  {new Date().toLocaleDateString()}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleSaveSettings}
          className="flex items-center gap-2"
        >
          <Save className="h-4 w-4" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}
