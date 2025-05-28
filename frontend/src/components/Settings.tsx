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
import { Switch } from "@/components/ui/switch";
import { useAuthStore } from "@/store/authStore";
import { Bell, Key, Save, Settings as SettingsIcon } from "lucide-react";
import { useState } from "react";

export function Settings() {
  const { apiKey } = useAuthStore();
  const [notifications, setNotifications] = useState({
    email: true,
    webhook: false,
    slack: false,
  });
  const [webhookUrl, setWebhookUrl] = useState("");
  const [slackWebhook, setSlackWebhook] = useState("");

  const handleSaveSettings = () => {
    // TODO: Implement settings save functionality
    console.log("Saving settings:", {
      notifications,
      webhookUrl,
      slackWebhook,
    });
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
