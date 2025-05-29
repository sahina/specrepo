import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import apiClient, {
  HARProcessingArtifactsResponse,
  HARProcessingStatus,
  SaveArtifactRequest,
} from "@/services/api";
import { Editor } from "@monaco-editor/react";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  Clock,
  Download,
  FileText,
  Loader2,
  Save,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface ContractSketchesProps {
  uploadId: number;
  onBack: () => void;
}

interface SaveDialogState {
  isOpen: boolean;
  artifactType: "openapi_specification" | "wiremock_mappings" | null;
  name: string;
  version: string;
  description: string;
}

export function ContractSketches({ uploadId, onBack }: ContractSketchesProps) {
  const [artifacts, setArtifacts] =
    useState<HARProcessingArtifactsResponse | null>(null);
  const [status, setStatus] = useState<HARProcessingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [saveDialog, setSaveDialog] = useState<SaveDialogState>({
    isOpen: false,
    artifactType: null,
    name: "",
    version: "1.0.0",
    description: "",
  });
  const [saving, setSaving] = useState(false);

  const loadArtifacts = useCallback(async () => {
    try {
      setLoading(true);
      const artifactsData = await apiClient.getHARProcessingArtifacts(uploadId);
      setArtifacts(artifactsData);
      setError(null);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load artifacts";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [uploadId]);

  const loadStatus = useCallback(async () => {
    try {
      const statusData = await apiClient.getHARProcessingStatus(uploadId);
      setStatus(statusData);
    } catch (err: unknown) {
      console.warn("Failed to load status:", err);
    }
  }, [uploadId]);

  useEffect(() => {
    loadArtifacts();
    loadStatus();
  }, [uploadId, loadArtifacts, loadStatus]);

  const handleSaveArtifact = async () => {
    if (!saveDialog.artifactType || !saveDialog.name.trim()) return;

    try {
      setSaving(true);
      const request: SaveArtifactRequest = {
        artifact_type: saveDialog.artifactType,
        name: saveDialog.name.trim(),
        version_string: saveDialog.version.trim() || "1.0.0",
        description: saveDialog.description.trim() || undefined,
      };

      await apiClient.saveArtifact(uploadId, request);

      // Close dialog and reset form
      setSaveDialog({
        isOpen: false,
        artifactType: null,
        name: "",
        version: "1.0.0",
        description: "",
      });

      // Show success message (you might want to add a toast notification here)
      alert("Artifact saved successfully!");
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to save artifact";
      alert(`Failed to save artifact: ${errorMessage}`);
    } finally {
      setSaving(false);
    }
  };

  const openSaveDialog = (
    artifactType: "openapi_specification" | "wiremock_mappings",
  ) => {
    const defaultName =
      artifactType === "openapi_specification"
        ? `${artifacts?.file_name?.replace(".har", "") || "API"} Specification`
        : `${artifacts?.file_name?.replace(".har", "") || "API"} Mocks`;

    setSaveDialog({
      isOpen: true,
      artifactType,
      name: defaultName,
      version: "1.0.0",
      description: `Generated from HAR file: ${
        artifacts?.file_name || "unknown"
      }`,
    });
  };

  const downloadArtifact = (
    content: Record<string, unknown> | Array<Record<string, unknown>>,
    filename: string,
  ) => {
    const blob = new Blob([JSON.stringify(content, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "failed":
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case "running":
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "completed":
        return (
          <Badge variant="default" className="bg-green-100 text-green-800">
            Completed
          </Badge>
        );
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      case "running":
        return (
          <Badge variant="secondary" className="bg-blue-100 text-blue-800">
            Processing
          </Badge>
        );
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading contract sketches...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="ghost"
            onClick={onBack}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to HAR Uploads
          </Button>
        </div>

        <Card className="p-6">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              Error Loading Contract Sketches
            </h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadArtifacts}>Try Again</Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!artifacts) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="ghost"
            onClick={onBack}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to HAR Uploads
          </Button>
        </div>

        <Card className="p-6">
          <div className="text-center">
            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              No Contract Sketches Available
            </h3>
            <p className="text-muted-foreground">
              This HAR file hasn't been processed yet or processing failed.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={onBack}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to HAR Uploads
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Contract Sketches</h1>
            <p className="text-muted-foreground">
              AI-generated artifacts from {artifacts.file_name}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {getStatusIcon(status?.status)}
          {getStatusBadge(status?.status)}
        </div>
      </div>

      {/* Main Content */}
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-6"
      >
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="openapi">OpenAPI Spec</TabsTrigger>
          <TabsTrigger value="wiremock">WireMock Stubs</TabsTrigger>
          <TabsTrigger value="metadata">Processing Info</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {artifacts.artifacts.processing_metadata.interactions_count}
                </div>
                <div className="text-sm text-muted-foreground">
                  API Interactions
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {artifacts.artifacts.processing_metadata.openapi_paths_count}
                </div>
                <div className="text-sm text-muted-foreground">
                  OpenAPI Paths
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {artifacts.artifacts.processing_metadata.wiremock_stubs_count}
                </div>
                <div className="text-sm text-muted-foreground">
                  WireMock Stubs
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {
                    artifacts.artifacts.processing_metadata
                      .processed_interactions_count
                  }
                </div>
                <div className="text-sm text-muted-foreground">Processed</div>
              </div>
            </Card>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* OpenAPI Specification Card */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">OpenAPI Specification</h3>
                <Badge variant="outline">
                  {artifacts.artifacts.processing_metadata.openapi_paths_count}{" "}
                  paths
                </Badge>
              </div>
              <p className="text-muted-foreground mb-4">
                Generated API specification based on the captured HTTP
                interactions.
              </p>
              <div className="flex gap-2">
                <Button
                  onClick={() => openSaveDialog("openapi_specification")}
                  className="flex items-center gap-2"
                >
                  <Save className="h-4 w-4" />
                  Save as Specification
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    downloadArtifact(
                      artifacts.artifacts.openapi_specification,
                      `${artifacts.file_name.replace(".har", "")}-openapi.json`,
                    )
                  }
                  className="flex items-center gap-2"
                >
                  <Download className="h-4 w-4" />
                  Download
                </Button>
              </div>
            </Card>

            {/* WireMock Stubs Card */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">WireMock Stubs</h3>
                <Badge variant="outline">
                  {artifacts.artifacts.processing_metadata.wiremock_stubs_count}{" "}
                  stubs
                </Badge>
              </div>
              <p className="text-muted-foreground mb-4">
                Mock server configurations for testing and development.
              </p>
              <div className="flex gap-2">
                <Button
                  onClick={() => openSaveDialog("wiremock_mappings")}
                  className="flex items-center gap-2"
                >
                  <Save className="h-4 w-4" />
                  Save as Mock Config
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    downloadArtifact(
                      artifacts.artifacts.wiremock_mappings,
                      `${artifacts.file_name.replace(
                        ".har",
                        "",
                      )}-wiremock.json`,
                    )
                  }
                  className="flex items-center gap-2"
                >
                  <Download className="h-4 w-4" />
                  Download
                </Button>
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* OpenAPI Specification Tab */}
        <TabsContent value="openapi" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">OpenAPI Specification</h3>
            <div className="flex gap-2">
              <Button
                onClick={() => openSaveDialog("openapi_specification")}
                className="flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                Save as Specification
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  downloadArtifact(
                    artifacts.artifacts.openapi_specification,
                    `${artifacts.file_name.replace(".har", "")}-openapi.json`,
                  )
                }
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Download
              </Button>
            </div>
          </div>

          <Card className="p-0 overflow-hidden">
            <Editor
              height="600px"
              defaultLanguage="json"
              value={JSON.stringify(
                artifacts.artifacts.openapi_specification,
                null,
                2,
              )}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: "on",
                theme: "vs-dark",
              }}
            />
          </Card>
        </TabsContent>

        {/* WireMock Stubs Tab */}
        <TabsContent value="wiremock" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">WireMock Stub Mappings</h3>
            <div className="flex gap-2">
              <Button
                onClick={() => openSaveDialog("wiremock_mappings")}
                className="flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                Save as Mock Config
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  downloadArtifact(
                    artifacts.artifacts.wiremock_mappings,
                    `${artifacts.file_name.replace(".har", "")}-wiremock.json`,
                  )
                }
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Download
              </Button>
            </div>
          </div>

          <Card className="p-0 overflow-hidden">
            <Editor
              height="600px"
              defaultLanguage="json"
              value={JSON.stringify(
                artifacts.artifacts.wiremock_mappings,
                null,
                2,
              )}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: "on",
                theme: "vs-dark",
              }}
            />
          </Card>
        </TabsContent>

        {/* Processing Metadata Tab */}
        <TabsContent value="metadata" className="space-y-4">
          <h3 className="text-lg font-semibold">Processing Information</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="p-6">
              <h4 className="font-semibold mb-4">Processing Statistics</h4>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Total Interactions:
                  </span>
                  <span className="font-medium">
                    {artifacts.artifacts.processing_metadata.interactions_count}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Successfully Processed:
                  </span>
                  <span className="font-medium">
                    {
                      artifacts.artifacts.processing_metadata
                        .processed_interactions_count
                    }
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    OpenAPI Paths Generated:
                  </span>
                  <span className="font-medium">
                    {
                      artifacts.artifacts.processing_metadata
                        .openapi_paths_count
                    }
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    WireMock Stubs Created:
                  </span>
                  <span className="font-medium">
                    {
                      artifacts.artifacts.processing_metadata
                        .wiremock_stubs_count
                    }
                  </span>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h4 className="font-semibold mb-4">File Information</h4>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Original File:</span>
                  <span className="font-medium">{artifacts.file_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Uploaded:</span>
                  <span className="font-medium">
                    {new Date(artifacts.uploaded_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Processed:</span>
                  <span className="font-medium">
                    {new Date(artifacts.processed_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </Card>
          </div>

          <Card className="p-6">
            <h4 className="font-semibold mb-4">Processing Options</h4>
            <Editor
              height="300px"
              defaultLanguage="json"
              value={JSON.stringify(
                artifacts.artifacts.processing_metadata.processing_options,
                null,
                2,
              )}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: "on",
                theme: "vs-dark",
              }}
            />
          </Card>
        </TabsContent>
      </Tabs>

      {/* Save Artifact Dialog */}
      <Dialog
        open={saveDialog.isOpen}
        onOpenChange={(open) =>
          setSaveDialog((prev) => ({ ...prev, isOpen: open }))
        }
      >
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>
              Save{" "}
              {saveDialog.artifactType === "openapi_specification"
                ? "OpenAPI Specification"
                : "WireMock Configuration"}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={saveDialog.name}
                onChange={(e) =>
                  setSaveDialog((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="Enter a name for this artifact"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="version">Version</Label>
              <Input
                id="version"
                value={saveDialog.version}
                onChange={(e) =>
                  setSaveDialog((prev) => ({
                    ...prev,
                    version: e.target.value,
                  }))
                }
                placeholder="1.0.0"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Input
                id="description"
                value={saveDialog.description}
                onChange={(e) =>
                  setSaveDialog((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
                placeholder="Brief description of this artifact"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() =>
                setSaveDialog((prev) => ({ ...prev, isOpen: false }))
              }
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveArtifact}
              disabled={saving || !saveDialog.name.trim()}
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
