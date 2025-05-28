import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useApiClient } from "@/hooks/useApiClient";
import type {
  WireMockGenerateResponse,
  WireMockStatusResponse,
} from "@/services/api";
import {
  AlertCircle,
  CheckCircle,
  ExternalLink,
  Loader2,
  Play,
  RotateCcw,
  Server,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface MockDeploymentProps {
  specificationId: number;
  specificationName: string;
}

interface DeploymentStatus {
  isDeployed: boolean;
  stubCount: number;
  lastDeployed?: string;
  error?: string;
}

const WIREMOCK_BASE_URL = "http://localhost:8081";

export function MockDeployment({
  specificationId,
  specificationName,
}: MockDeploymentProps) {
  const apiClient = useApiClient();
  const [status, setStatus] = useState<DeploymentStatus>({
    isDeployed: false,
    stubCount: 0,
  });
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDeployDialog, setShowDeployDialog] = useState(false);
  const [showResetDialog, setShowResetDialog] = useState(false);
  const [showStatusDialog, setShowStatusDialog] = useState(false);
  const [deploymentHistory, setDeploymentHistory] = useState<
    Array<{
      timestamp: string;
      stubCount: number;
      success: boolean;
      error?: string;
    }>
  >([]);

  // Load current mock status
  const loadMockStatus = useCallback(async () => {
    if (!apiClient) return;

    setLoading(true);
    setError(null);

    try {
      const response: WireMockStatusResponse =
        await apiClient.getWireMockStubs();
      setStatus({
        isDeployed: response.total_stubs > 0,
        stubCount: response.total_stubs,
        lastDeployed:
          response.total_stubs > 0 ? new Date().toISOString() : undefined,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load mock status";
      setError(errorMessage);
      setStatus({
        isDeployed: false,
        stubCount: 0,
        error: errorMessage,
      });
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  // Load status on component mount
  useEffect(() => {
    loadMockStatus();
  }, [loadMockStatus]);

  // Deploy mocks
  const handleDeploy = async (clearExisting: boolean = true) => {
    if (!apiClient) return;

    setDeploying(true);
    setError(null);

    try {
      const response: WireMockGenerateResponse =
        await apiClient.generateWireMockStubs({
          specification_id: specificationId,
          clear_existing: clearExisting,
        });

      // Update status
      setStatus({
        isDeployed: true,
        stubCount: response.stubs_created,
        lastDeployed: new Date().toISOString(),
      });

      // Add to deployment history
      setDeploymentHistory((prev) => [
        {
          timestamp: new Date().toISOString(),
          stubCount: response.stubs_created,
          success: true,
        },
        ...prev.slice(0, 4), // Keep last 5 entries
      ]);

      setShowDeployDialog(false);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to deploy mocks";
      setError(errorMessage);

      // Add failed deployment to history
      setDeploymentHistory((prev) => [
        {
          timestamp: new Date().toISOString(),
          stubCount: 0,
          success: false,
          error: errorMessage,
        },
        ...prev.slice(0, 4),
      ]);
    } finally {
      setDeploying(false);
    }
  };

  // Reset mocks
  const handleReset = async () => {
    if (!apiClient) return;

    setResetting(true);
    setError(null);

    try {
      await apiClient.resetWireMock();

      // Update status
      setStatus({
        isDeployed: false,
        stubCount: 0,
      });

      setShowResetDialog(false);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to reset mocks";
      setError(errorMessage);
    } finally {
      setResetting(false);
    }
  };

  // Open WireMock admin interface
  const openWireMockAdmin = () => {
    window.open(`${WIREMOCK_BASE_URL}/__admin/`, "_blank");
  };

  // Open mock API base URL
  const openMockAPI = () => {
    window.open(WIREMOCK_BASE_URL, "_blank");
  };

  const getStatusBadgeVariant = () => {
    if (loading) return "secondary";
    if (error || status.error) return "destructive";
    if (status.isDeployed) return "default";
    return "secondary";
  };

  const getStatusText = () => {
    if (loading) return "Loading...";
    if (error || status.error) return "Error";
    if (status.isDeployed) return `${status.stubCount} stubs deployed`;
    return "Not deployed";
  };

  return (
    <div className="bg-card border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Server className="h-5 w-5 text-muted-foreground" />
          <h3 className="text-lg font-semibold">Mock Deployment</h3>
        </div>
        <Badge
          variant={getStatusBadgeVariant()}
          className="flex items-center gap-1"
        >
          {loading ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : error || status.error ? (
            <AlertCircle className="h-3 w-3" />
          ) : status.isDeployed ? (
            <CheckCircle className="h-3 w-3" />
          ) : (
            <X className="h-3 w-3" />
          )}
          {getStatusText()}
        </Badge>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-destructive" />
            <p className="text-destructive text-sm font-medium">
              Deployment Error
            </p>
          </div>
          <p className="text-destructive text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Mock URLs */}
      {status.isDeployed && (
        <div className="bg-muted/50 rounded-lg p-4 mb-4">
          <h4 className="text-sm font-medium mb-2">Mock API URLs</h4>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Base URL:</span>
              <div className="flex items-center gap-2">
                <code className="text-xs bg-background px-2 py-1 rounded">
                  {WIREMOCK_BASE_URL}
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={openMockAPI}
                  className="h-6 w-6 p-0"
                >
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Admin UI:</span>
              <div className="flex items-center gap-2">
                <code className="text-xs bg-background px-2 py-1 rounded">
                  {WIREMOCK_BASE_URL}/__admin/
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={openWireMockAdmin}
                  className="h-6 w-6 p-0"
                >
                  <ExternalLink className="h-3 w-3" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Last Deployed Info */}
      {status.lastDeployed && (
        <div className="text-sm text-muted-foreground mb-4">
          Last deployed: {new Date(status.lastDeployed).toLocaleString()}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        <Button
          onClick={() => setShowDeployDialog(true)}
          disabled={deploying || loading}
          className="flex items-center gap-2"
        >
          {deploying ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {deploying ? "Deploying..." : "Deploy Mocks"}
        </Button>

        {status.isDeployed && (
          <Button
            variant="outline"
            onClick={() => setShowResetDialog(true)}
            disabled={resetting || loading}
            className="flex items-center gap-2"
          >
            {resetting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RotateCcw className="h-4 w-4" />
            )}
            {resetting ? "Resetting..." : "Reset Mocks"}
          </Button>
        )}

        <Button
          variant="ghost"
          onClick={() => setShowStatusDialog(true)}
          className="flex items-center gap-2"
        >
          <Server className="h-4 w-4" />
          View Status
        </Button>

        <Button
          variant="ghost"
          onClick={loadMockStatus}
          disabled={loading}
          className="flex items-center gap-2"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RotateCcw className="h-4 w-4" />
          )}
          Refresh
        </Button>
      </div>

      {/* Deploy Confirmation Dialog */}
      <AlertDialog open={showDeployDialog} onOpenChange={setShowDeployDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deploy Mock API</AlertDialogTitle>
            <AlertDialogDescription>
              This will deploy "{specificationName}" to WireMock and create mock
              endpoints based on your OpenAPI specification.
              {status.isDeployed && (
                <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-amber-800 text-sm">
                  <strong>Note:</strong> This will replace the currently
                  deployed mocks ({status.stubCount} stubs).
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleDeploy(true)}
              disabled={deploying}
            >
              {deploying ? "Deploying..." : "Deploy"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reset Confirmation Dialog */}
      <AlertDialog open={showResetDialog} onOpenChange={setShowResetDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reset Mock API</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove all mock endpoints from WireMock. This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleReset}
              disabled={resetting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {resetting ? "Resetting..." : "Reset"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Status Dialog */}
      <Dialog open={showStatusDialog} onOpenChange={setShowStatusDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Mock Deployment Status</DialogTitle>
            <DialogDescription>
              Current status and deployment history for "{specificationName}"
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Current Status */}
            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="font-medium mb-2">Current Status</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Status:</span>
                  <Badge variant={getStatusBadgeVariant()} className="ml-2">
                    {getStatusText()}
                  </Badge>
                </div>
                <div>
                  <span className="text-muted-foreground">Stub Count:</span>
                  <span className="ml-2 font-mono">{status.stubCount}</span>
                </div>
                {status.lastDeployed && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">
                      Last Deployed:
                    </span>
                    <span className="ml-2">
                      {new Date(status.lastDeployed).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Deployment History */}
            {deploymentHistory.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Recent Deployments</h4>
                <div className="space-y-2">
                  {deploymentHistory.map((deployment, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-2 bg-muted/30 rounded text-sm"
                    >
                      <div className="flex items-center gap-2">
                        {deployment.success ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-destructive" />
                        )}
                        <span>
                          {new Date(deployment.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {deployment.success ? (
                          <span className="text-muted-foreground">
                            {deployment.stubCount} stubs created
                          </span>
                        ) : (
                          <span className="text-destructive text-xs">
                            {deployment.error}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* WireMock URLs */}
            <div>
              <h4 className="font-medium mb-2">WireMock URLs</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Mock API:</span>
                  <div className="flex items-center gap-2">
                    <code className="text-xs bg-background px-2 py-1 rounded">
                      {WIREMOCK_BASE_URL}
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={openMockAPI}
                      className="h-6 w-6 p-0"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">
                    Admin Interface:
                  </span>
                  <div className="flex items-center gap-2">
                    <code className="text-xs bg-background px-2 py-1 rounded">
                      {WIREMOCK_BASE_URL}/__admin/
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={openWireMockAdmin}
                      className="h-6 w-6 p-0"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
