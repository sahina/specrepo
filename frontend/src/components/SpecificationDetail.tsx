import { MockDeployment } from "@/components/MockDeployment";
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
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormItem,
  FormLabel,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useApiClient } from "@/hooks/useApiClient";
import type {
  APISpecification,
  APISpecificationCreate,
  APISpecificationUpdate,
} from "@/services/api";
import Editor from "@monaco-editor/react";
import { AlertCircle, ArrowLeft, Check, Loader2, Save, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface SpecificationDetailProps {
  specificationId?: number;
  onBack: () => void;
  onSave?: (spec: APISpecification) => void;
}

interface FormData {
  name: string;
  version_string: string;
  openapi_content: string;
}

interface ValidationError {
  line?: number;
  column?: number;
  message: string;
}

export function SpecificationDetail({
  specificationId,
  onBack,
  onSave,
}: SpecificationDetailProps) {
  const apiClient = useApiClient();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [specification, setSpecification] = useState<APISpecification | null>(
    null,
  );
  const [formData, setFormData] = useState<FormData>({
    name: "",
    version_string: "",
    openapi_content: "",
  });
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>(
    [],
  );
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false);
  const [editorLanguage, setEditorLanguage] = useState<"json" | "yaml">("json");

  const isCreateMode = !specificationId;

  // Load specification data
  useEffect(() => {
    const loadSpecification = async () => {
      if (!apiClient || !specificationId) return;

      setLoading(true);
      setError(null);

      try {
        const spec = await apiClient.getSpecification(specificationId);
        setSpecification(spec);

        // Convert openapi_content to string for editor
        const contentString =
          typeof spec.openapi_content === "string"
            ? spec.openapi_content
            : JSON.stringify(spec.openapi_content, null, 2);

        setFormData({
          name: spec.name,
          version_string: spec.version_string,
          openapi_content: contentString,
        });

        // Detect if content is YAML or JSON
        try {
          JSON.parse(contentString);
          setEditorLanguage("json");
        } catch {
          setEditorLanguage("yaml");
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load specification",
        );
      } finally {
        setLoading(false);
      }
    };

    if (specificationId && apiClient) {
      loadSpecification();
    } else if (isCreateMode) {
      // Initialize with default OpenAPI structure
      const defaultContent = {
        openapi: "3.0.0",
        info: {
          title: "New API",
          version: "1.0.0",
          description: "A new API specification",
        },
        paths: {},
      };
      setFormData({
        name: "",
        version_string: "1.0.0",
        openapi_content: JSON.stringify(defaultContent, null, 2),
      });
      setEditorLanguage("json");
    }
  }, [specificationId, apiClient, isCreateMode]);

  const validateOpenAPIContent = useCallback(
    (content: string): ValidationError[] => {
      const errors: ValidationError[] = [];

      if (!content.trim()) {
        errors.push({ message: "OpenAPI content cannot be empty" });
        return errors;
      }

      try {
        const parsed = JSON.parse(content);

        // Basic OpenAPI validation
        if (!parsed.openapi && !parsed.swagger) {
          errors.push({ message: "Missing 'openapi' or 'swagger' field" });
        }

        if (!parsed.info) {
          errors.push({ message: "Missing 'info' field" });
        } else {
          if (!parsed.info.title) {
            errors.push({ message: "Missing 'info.title' field" });
          }
          if (!parsed.info.version) {
            errors.push({ message: "Missing 'info.version' field" });
          }
        }

        if (!parsed.paths) {
          errors.push({ message: "Missing 'paths' field" });
        }
      } catch (parseError) {
        if (parseError instanceof SyntaxError) {
          // Try to extract line/column info from error message
          const match = parseError.message.match(/at position (\d+)/);
          if (match) {
            const position = parseInt(match[1]);
            const lines = content.substring(0, position).split("\n");
            errors.push({
              line: lines.length,
              column: lines[lines.length - 1].length + 1,
              message: `JSON syntax error: ${parseError.message}`,
            });
          } else {
            errors.push({
              message: `JSON syntax error: ${parseError.message}`,
            });
          }
        } else {
          errors.push({ message: "Invalid JSON format" });
        }
      }

      return errors;
    },
    [],
  );

  const handleFormChange = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasUnsavedChanges(true);

    // Validate OpenAPI content on change
    if (field === "openapi_content") {
      const errors = validateOpenAPIContent(value);
      setValidationErrors(errors);
    }
  };

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      handleFormChange("openapi_content", value);
    }
  };

  const handleSave = async () => {
    if (!apiClient) return;

    // Validate form
    const errors = validateOpenAPIContent(formData.openapi_content);
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    if (!formData.name.trim()) {
      setError("Name is required");
      return;
    }

    if (!formData.version_string.trim()) {
      setError("Version is required");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      let parsedContent: Record<string, unknown>;
      try {
        parsedContent = JSON.parse(formData.openapi_content);
      } catch {
        setError("Invalid JSON format in OpenAPI content");
        return;
      }

      let savedSpec: APISpecification;

      if (isCreateMode) {
        const createData: APISpecificationCreate = {
          name: formData.name.trim(),
          version_string: formData.version_string.trim(),
          openapi_content: parsedContent,
        };
        savedSpec = await apiClient.createSpecification(createData);
      } else {
        const updateData: APISpecificationUpdate = {
          name: formData.name.trim(),
          version_string: formData.version_string.trim(),
          openapi_content: parsedContent,
        };
        savedSpec = await apiClient.updateSpecification(
          specificationId!,
          updateData,
        );
      }

      setSpecification(savedSpec);
      setHasUnsavedChanges(false);
      onSave?.(savedSpec);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save specification",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    if (hasUnsavedChanges) {
      setShowUnsavedDialog(true);
    } else {
      onBack();
    }
  };

  const handleDiscardChanges = () => {
    setShowUnsavedDialog(false);
    setHasUnsavedChanges(false);
    onBack();
  };

  const toggleEditorLanguage = () => {
    const newLanguage = editorLanguage === "json" ? "yaml" : "json";
    setEditorLanguage(newLanguage);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading specification...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold">
              {isCreateMode
                ? "Create API Specification"
                : "Edit API Specification"}
            </h1>
            {specification && (
              <p className="text-muted-foreground">
                Last updated:{" "}
                {new Date(
                  specification.updated_at || specification.created_at,
                ).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasUnsavedChanges && (
            <span className="text-sm text-muted-foreground flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              Unsaved changes
            </span>
          )}
          <Button
            onClick={handleSave}
            disabled={saving || validationErrors.length > 0}
            className="flex items-center gap-2"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saving ? "Saving..." : "Save"}
          </Button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <p className="text-destructive font-medium">Error</p>
          </div>
          <p className="text-destructive mt-1">{error}</p>
        </div>
      )}

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <X className="h-5 w-5 text-destructive" />
            <p className="text-destructive font-medium">Validation Errors</p>
          </div>
          <ul className="space-y-1">
            {validationErrors.map((error, index) => (
              <li key={index} className="text-destructive text-sm">
                {error.line && error.column && (
                  <span className="font-mono">
                    Line {error.line}, Column {error.column}:{" "}
                  </span>
                )}
                {error.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Success Indicator */}
      {!hasUnsavedChanges && !isCreateMode && validationErrors.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <Check className="h-5 w-5 text-green-600" />
            <p className="text-green-800 font-medium">All changes saved</p>
          </div>
        </div>
      )}

      {/* Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Metadata Form */}
        <div className="lg:col-span-1">
          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">
              Specification Details
            </h2>
            <Form>
              <FormItem>
                <FormLabel htmlFor="name">Name</FormLabel>
                <FormControl>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => handleFormChange("name", e.target.value)}
                    placeholder="Enter specification name"
                  />
                </FormControl>
                <FormDescription>
                  A descriptive name for your API specification
                </FormDescription>
              </FormItem>

              <FormItem>
                <FormLabel htmlFor="version">Version</FormLabel>
                <FormControl>
                  <Input
                    id="version"
                    value={formData.version_string}
                    onChange={(e) =>
                      handleFormChange("version_string", e.target.value)
                    }
                    placeholder="e.g., 1.0.0"
                  />
                </FormControl>
                <FormDescription>Semantic version of your API</FormDescription>
              </FormItem>

              {specification && (
                <div className="space-y-2">
                  <FormLabel>Created</FormLabel>
                  <p className="text-sm text-muted-foreground">
                    {new Date(specification.created_at).toLocaleString()}
                  </p>
                </div>
              )}
            </Form>
          </div>
        </div>

        {/* OpenAPI Editor */}
        <div className="lg:col-span-2">
          <div className="bg-card border rounded-lg overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-xl font-semibold">OpenAPI Content</h2>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={toggleEditorLanguage}
                >
                  {editorLanguage.toUpperCase()}
                </Button>
              </div>
            </div>
            <div className="h-[600px]">
              <Editor
                height="100%"
                language={editorLanguage}
                value={formData.openapi_content}
                onChange={handleEditorChange}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 14,
                  lineNumbers: "on",
                  renderWhitespace: "selection",
                  tabSize: 2,
                  insertSpaces: true,
                  automaticLayout: true,
                  formatOnPaste: true,
                  formatOnType: true,
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Mock Deployment Section */}
      {!isCreateMode && specification && (
        <MockDeployment
          specificationId={specification.id}
          specificationName={specification.name}
        />
      )}

      {/* Unsaved Changes Dialog */}
      <AlertDialog open={showUnsavedDialog} onOpenChange={setShowUnsavedDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Unsaved Changes</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Are you sure you want to leave without
              saving?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setShowUnsavedDialog(false)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDiscardChanges}>
              Discard Changes
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
