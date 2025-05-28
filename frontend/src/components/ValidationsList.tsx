import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useApiClient } from "@/hooks/useApiClient";
import type { ValidationRun } from "@/services/api";
import {
  getValidationStatusColor,
  getValidationStatusLabel,
} from "@/services/apiUtils";
import {
  AlertCircle,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
  Play,
  RefreshCw,
  Search,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface ValidationsListProps {
  onViewResults?: (validation: ValidationRun) => void;
  onTriggerValidation?: () => void;
}

export function ValidationsList({
  onViewResults,
  onTriggerValidation,
}: ValidationsListProps) {
  const apiClient = useApiClient();
  const [validations, setValidations] = useState<ValidationRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"triggered_at" | "status">(
    "triggered_at",
  );
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [pagination, setPagination] = useState({
    page: 1,
    size: 10,
    total: 0,
    pages: 0,
  });

  const fetchValidations = useCallback(async () => {
    if (!apiClient) return;

    try {
      setLoading(true);
      setError(null);

      const filters = {
        page: pagination.page,
        size: pagination.size,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      const data = await apiClient.getValidations(filters);
      setValidations(data.items);
      setPagination({
        page: data.page,
        size: data.size,
        total: data.total,
        pages: data.pages,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch validations";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [apiClient, pagination.page, pagination.size, sortBy, sortOrder]);

  useEffect(() => {
    fetchValidations();
  }, [fetchValidations]);

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("asc");
    }
  };

  const handlePageChange = (newPage: number) => {
    setPagination((prev) => ({ ...prev, page: newPage }));
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getSortIcon = (column: string) => {
    if (sortBy !== column) return <ArrowUpDown className="h-4 w-4" />;
    return sortOrder === "asc" ? "↑" : "↓";
  };

  const getStatusBadge = (status: string) => {
    const colorClass = getValidationStatusColor(
      status as ValidationRun["status"],
    );
    const label = getValidationStatusLabel(status as ValidationRun["status"]);

    return (
      <Badge variant="secondary" className={colorClass}>
        {label}
      </Badge>
    );
  };

  const getResultsSummary = (validation: ValidationRun) => {
    if (!validation.schemathesis_results) return "—";

    const results = validation.schemathesis_results as Record<string, unknown>;
    if (results.error) return "Error";

    if (results.total_tests) {
      return `${results.passed_tests || 0}/${results.total_tests} passed`;
    }

    return "—";
  };

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Validations</h1>
          <Button onClick={onTriggerValidation}>
            <Play className="h-4 w-4 mr-2" />
            New Validation
          </Button>
        </div>

        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <p className="text-destructive font-medium">Error</p>
          </div>
          <p className="text-destructive mt-1">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchValidations}
            className="mt-3"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Validations</h1>
          <p className="text-muted-foreground">
            View and manage API validation runs and results
          </p>
        </div>
        <Button onClick={onTriggerValidation}>
          <Play className="h-4 w-4 mr-2" />
          New Validation
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
          <Input
            placeholder="Search validations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button variant="outline" onClick={fetchValidations}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Table */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Specification</TableHead>
              <TableHead>Provider URL</TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  onClick={() => handleSort("status")}
                  className="h-auto p-0 font-semibold"
                >
                  Status {getSortIcon("status")}
                </Button>
              </TableHead>
              <TableHead>Results</TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  onClick={() => handleSort("triggered_at")}
                  className="h-auto p-0 font-semibold"
                >
                  Triggered {getSortIcon("triggered_at")}
                </Button>
              </TableHead>
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading validations...
                  </div>
                </TableCell>
              </TableRow>
            ) : validations.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  <div className="text-muted-foreground">
                    {searchTerm
                      ? "No validations found matching your search."
                      : "No validations found. Start by creating a new validation."}
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              validations.map((validation) => (
                <TableRow key={validation.id}>
                  <TableCell className="font-medium">
                    Spec #{validation.api_specification_id}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {validation.provider_url}
                  </TableCell>
                  <TableCell>{getStatusBadge(validation.status)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {getResultsSummary(validation)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(validation.triggered_at)}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onViewResults?.(validation)}
                    >
                      <Eye className="h-4 w-4 mr-2" />
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {pagination.pages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {(pagination.page - 1) * pagination.size + 1} to{" "}
            {Math.min(pagination.page * pagination.size, pagination.total)} of{" "}
            {pagination.total} validations
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <div className="flex items-center gap-1">
              {Array.from({ length: pagination.pages }, (_, i) => i + 1)
                .filter((page) => {
                  const current = pagination.page;
                  return (
                    page === 1 ||
                    page === pagination.pages ||
                    (page >= current - 1 && page <= current + 1)
                  );
                })
                .map((page, index, array) => (
                  <div key={page} className="flex items-center">
                    {index > 0 && array[index - 1] !== page - 1 && (
                      <span className="px-2 text-muted-foreground">...</span>
                    )}
                    <Button
                      variant={page === pagination.page ? "default" : "outline"}
                      size="sm"
                      onClick={() => handlePageChange(page)}
                    >
                      {page}
                    </Button>
                  </div>
                ))}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(pagination.page + 1)}
              disabled={pagination.page >= pagination.pages}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
