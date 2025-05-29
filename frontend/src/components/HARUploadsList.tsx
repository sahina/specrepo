import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  HARUpload,
  HARUploadFilters,
  PaginatedResponse,
} from "@/services/api";
import apiClient from "@/services/api";
import { Calendar, FileText, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface HARUploadsListProps {
  onRefresh?: () => void;
  refreshTrigger?: number;
}

export function HARUploadsList({
  onRefresh,
  refreshTrigger,
}: HARUploadsListProps) {
  const [uploads, setUploads] = useState<HARUpload[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [pagination, setPagination] = useState({
    page: 1,
    size: 10,
    total: 0,
    pages: 0,
  });

  const loadUploads = useCallback(
    async (filters?: HARUploadFilters) => {
      try {
        setLoading(true);
        setError(null);

        const response: PaginatedResponse<HARUpload> =
          await apiClient.getHARUploads({
            file_name: searchTerm || undefined,
            sort_by: "uploaded_at",
            sort_order: "desc",
            page: filters?.page || 1,
            size: filters?.size || 10,
            ...filters,
          });

        setUploads(response.items);
        setPagination({
          page: response.page,
          size: response.size,
          total: response.total,
          pages: response.pages,
        });
      } catch (err) {
        console.error("Error loading HAR uploads:", err);
        setError("Failed to load HAR uploads");
      } finally {
        setLoading(false);
      }
    },
    [searchTerm],
  );

  useEffect(() => {
    loadUploads();
  }, [loadUploads, refreshTrigger]);

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this HAR upload?")) {
      return;
    }

    try {
      await apiClient.deleteHARUpload(id);
      await loadUploads({ page: pagination.page });
      onRefresh?.();
    } catch (err) {
      console.error("Error deleting HAR upload:", err);
      setError("Failed to delete HAR upload");
    }
  };

  const handlePageChange = (newPage: number) => {
    loadUploads({ page: newPage });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading && uploads.length === 0) {
    return (
      <Card className="p-6">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Loading HAR uploads...</p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search and Filters */}
      <div className="flex items-center space-x-4">
        <div className="flex-1">
          <Input
            placeholder="Search by filename..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-sm"
          />
        </div>
        <Button
          variant="outline"
          onClick={() => loadUploads({ page: 1 })}
          disabled={loading}
        >
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="p-4 border-destructive">
          <p className="text-destructive">{error}</p>
        </Card>
      )}

      {/* Uploads Table */}
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">HAR Uploads</h3>
            <Badge variant="secondary">
              {pagination.total} upload{pagination.total !== 1 ? "s" : ""}
            </Badge>
          </div>

          {uploads.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">
                No HAR uploads found
              </h3>
              <p className="text-muted-foreground">
                {searchTerm
                  ? "No uploads match your search criteria"
                  : "Upload your first HAR file to get started"}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>File Name</TableHead>
                    <TableHead>Uploaded</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {uploads.map((upload) => (
                    <TableRow key={upload.id}>
                      <TableCell>
                        <div className="flex items-center space-x-3">
                          <FileText className="h-4 w-4 text-primary" />
                          <div>
                            <p className="font-medium">{upload.file_name}</p>
                            <p className="text-sm text-muted-foreground">
                              ID: {upload.id}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">
                            {formatDate(upload.uploaded_at)}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            upload.processed_artifacts_references
                              ? "default"
                              : "secondary"
                          }
                        >
                          {upload.processed_artifacts_references
                            ? "Processed"
                            : "Uploaded"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(upload.id)}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {pagination.pages > 1 && (
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Showing {(pagination.page - 1) * pagination.size + 1} to{" "}
                    {Math.min(
                      pagination.page * pagination.size,
                      pagination.total,
                    )}{" "}
                    of {pagination.total} uploads
                  </p>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(pagination.page - 1)}
                      disabled={pagination.page <= 1}
                    >
                      Previous
                    </Button>
                    <span className="text-sm">
                      Page {pagination.page} of {pagination.pages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(pagination.page + 1)}
                      disabled={pagination.page >= pagination.pages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
