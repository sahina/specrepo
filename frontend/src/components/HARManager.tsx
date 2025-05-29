import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import apiClient from "@/services/api";
import { ArrowLeft, List, Upload } from "lucide-react";
import { useState } from "react";
import { HARFileUpload } from "./HARFileUpload";
import { HARUploadsList } from "./HARUploadsList";

type HARManagerView = "upload" | "list";

interface HARManagerProps {
  onBack?: () => void;
}

export function HARManager({ onBack }: HARManagerProps) {
  const [currentView, setCurrentView] = useState<HARManagerView>("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setUploadError(null);
    setUploadSuccess(false);
  };

  const handleFileRemove = () => {
    setSelectedFile(null);
    setUploadError(null);
    setUploadSuccess(false);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setIsUploading(true);
      setUploadError(null);

      await apiClient.uploadHARFile(selectedFile);

      setUploadSuccess(true);
      setSelectedFile(null);
      setRefreshTrigger((prev) => prev + 1);

      // Auto-switch to list view after successful upload
      setTimeout(() => {
        setCurrentView("list");
        setUploadSuccess(false);
      }, 2000);
    } catch (error) {
      console.error("Upload failed:", error);
      setUploadError("Failed to upload HAR file. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {onBack && (
            <Button variant="ghost" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          )}
          <div>
            <h1 className="text-2xl font-bold">HAR File Management</h1>
            <p className="text-muted-foreground">
              Upload and manage HTTP Archive (HAR) files for API analysis
            </p>
          </div>
        </div>
      </div>

      {/* View Toggle */}
      <Card className="p-4">
        <div className="flex items-center space-x-4">
          <Button
            variant={currentView === "upload" ? "default" : "outline"}
            onClick={() => setCurrentView("upload")}
            className="flex items-center space-x-2"
          >
            <Upload className="h-4 w-4" />
            <span>Upload HAR</span>
          </Button>
          <Button
            variant={currentView === "list" ? "default" : "outline"}
            onClick={() => setCurrentView("list")}
            className="flex items-center space-x-2"
          >
            <List className="h-4 w-4" />
            <span>Manage Uploads</span>
          </Button>
        </div>
      </Card>

      {/* Content */}
      {currentView === "upload" && (
        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Upload HAR File</h2>
            <div className="space-y-4">
              <HARFileUpload
                onFileSelect={handleFileSelect}
                onFileRemove={handleFileRemove}
                selectedFile={selectedFile}
                isUploading={isUploading}
                error={uploadError || undefined}
              />

              {selectedFile && (
                <div className="flex items-center justify-between pt-4 border-t">
                  <div className="text-sm text-muted-foreground">
                    Ready to upload: {selectedFile.name}
                  </div>
                  <Button
                    onClick={handleUpload}
                    disabled={isUploading}
                    className="min-w-[120px]"
                  >
                    {isUploading ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        <span>Uploading...</span>
                      </div>
                    ) : (
                      "Upload File"
                    )}
                  </Button>
                </div>
              )}

              {uploadSuccess && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-md">
                  <div className="flex items-center space-x-2">
                    <div className="h-4 w-4 bg-green-500 rounded-full"></div>
                    <p className="text-green-800 font-medium">
                      HAR file uploaded successfully!
                    </p>
                  </div>
                  <p className="text-green-700 text-sm mt-1">
                    Switching to file management view...
                  </p>
                </div>
              )}
            </div>
          </Card>

          {/* Upload Instructions */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-3">
              How to Generate HAR Files
            </h3>
            <div className="space-y-4 text-sm">
              <div>
                <h4 className="font-medium mb-2">Chrome DevTools:</h4>
                <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                  <li>Open Chrome DevTools (F12)</li>
                  <li>Go to the Network tab</li>
                  <li>Perform the API requests you want to capture</li>
                  <li>
                    Right-click in the Network tab and select "Save all as HAR"
                  </li>
                </ol>
              </div>
              <div>
                <h4 className="font-medium mb-2">Firefox DevTools:</h4>
                <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                  <li>Open Firefox DevTools (F12)</li>
                  <li>Go to the Network tab</li>
                  <li>Perform the API requests you want to capture</li>
                  <li>Click the gear icon and select "Save All As HAR"</li>
                </ol>
              </div>
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <p className="text-yellow-800 text-sm">
                  <strong>Security Note:</strong> HAR files may contain
                  sensitive data like API keys, tokens, and personal
                  information. Review and sanitize your HAR files before
                  uploading.
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {currentView === "list" && (
        <HARUploadsList
          onRefresh={() => setRefreshTrigger((prev) => prev + 1)}
          refreshTrigger={refreshTrigger}
        />
      )}
    </div>
  );
}
