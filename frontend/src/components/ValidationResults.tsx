import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useApiClient } from "@/hooks/useApiClient";
import type { ValidationRun } from "@/services/api";
import {
  getValidationStatusColor,
  getValidationStatusLabel,
} from "@/services/apiUtils";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  Clock,
  ExternalLink,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface ValidationResultsProps {
  validationId: number;
  onBack?: () => void;
}

interface SchemathesisResults {
  total_tests?: number;
  passed_tests?: number;
  failed_tests?: number;
  error_tests?: number;
  skipped_tests?: number;
  duration?: number;
  error?: string;
  test_results?: Array<{
    endpoint: string;
    method: string;
    status: "passed" | "failed" | "error";
    message?: string;
    response_time?: number;
  }>;
  coverage?: {
    endpoints_tested: number;
    total_endpoints: number;
    percentage: number;
  };
}

export function ValidationResults({
  validationId,
  onBack,
}: ValidationResultsProps) {
  const apiClient = useApiClient();
  const [validation, setValidation] = useState<ValidationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchValidationResults = useCallback(async () => {
    if (!apiClient) return;

    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getValidationResults(validationId);
      setValidation(data);

      // Auto-refresh if validation is still running
      const shouldAutoRefresh =
        data.status === "running" || data.status === "pending";
      setAutoRefresh(shouldAutoRefresh);
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Failed to fetch validation results";
      setError(errorMessage);
      setAutoRefresh(false);
    } finally {
      setLoading(false);
    }
  }, [apiClient, validationId]);

  useEffect(() => {
    fetchValidationResults();
  }, [fetchValidationResults]);

  // Auto-refresh for running validations
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchValidationResults();
    }, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, [autoRefresh, fetchValidationResults]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "—";
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(1)}s`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "failed":
        return <XCircle className="h-5 w-5 text-red-500" />;
      case "running":
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case "pending":
        return <Clock className="h-5 w-5 text-yellow-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getTestStatusIcon = (status: "passed" | "failed" | "error") => {
    switch (status) {
      case "passed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "error":
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
    }
  };

  const renderSummaryStats = (results: SchemathesisResults) => {
    const stats = [
      {
        label: "Total Tests",
        value: results.total_tests || 0,
        color: "text-foreground",
      },
      {
        label: "Passed",
        value: results.passed_tests || 0,
        color: "text-green-600",
      },
      {
        label: "Failed",
        value: results.failed_tests || 0,
        color: "text-red-600",
      },
      {
        label: "Errors",
        value: results.error_tests || 0,
        color: "text-orange-600",
      },
      {
        label: "Skipped",
        value: results.skipped_tests || 0,
        color: "text-gray-600",
      },
    ];

    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="text-center">
            <div className={`text-2xl font-bold ${stat.color}`}>
              {stat.value}
            </div>
            <div className="text-sm text-muted-foreground">{stat.label}</div>
          </div>
        ))}
      </div>
    );
  };

  const renderCoverageInfo = (results: SchemathesisResults) => {
    if (!results.coverage) return null;

    const { endpoints_tested, total_endpoints, percentage } = results.coverage;

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">API Coverage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span>Endpoints Tested</span>
              <span className="font-semibold">
                {endpoints_tested} / {total_endpoints}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <div className="text-center text-sm text-muted-foreground">
              {percentage.toFixed(1)}% coverage
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderTestResults = (results: SchemathesisResults) => {
    if (!results.test_results || results.test_results.length === 0) {
      return null;
    }

    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Test Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {results.test_results.map((test, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  {getTestStatusIcon(test.status)}
                  <div>
                    <div className="font-medium">
                      {test.method.toUpperCase()} {test.endpoint}
                    </div>
                    {test.message && (
                      <div className="text-sm text-muted-foreground">
                        {test.message}
                      </div>
                    )}
                  </div>
                </div>
                {test.response_time && (
                  <div className="text-sm text-muted-foreground">
                    {test.response_time}ms
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  };

  if (loading && !validation) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="outline" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          )}
          <h1 className="text-3xl font-bold">Validation Results</h1>
        </div>

        <Card>
          <CardContent className="flex items-center justify-center py-8">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading validation results...
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="outline" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          )}
          <h1 className="text-3xl font-bold">Validation Results</h1>
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
            onClick={fetchValidationResults}
            className="mt-3"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  if (!validation) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="outline" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          )}
          <h1 className="text-3xl font-bold">Validation Results</h1>
        </div>

        <div className="text-center py-8">
          <p className="text-muted-foreground">Validation not found</p>
        </div>
      </div>
    );
  }

  const results = validation.schemathesis_results as SchemathesisResults | null;
  const statusColor = getValidationStatusColor(validation.status);
  const statusLabel = getValidationStatusLabel(validation.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="outline" size="sm" onClick={onBack}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          )}
          <div>
            <h1 className="text-3xl font-bold">Validation Results</h1>
            <p className="text-muted-foreground">
              Validation #{validation.id} • Triggered{" "}
              {formatDate(validation.triggered_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {autoRefresh && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              Auto-refreshing...
            </div>
          )}
          <Button variant="outline" size="sm" onClick={fetchValidationResults}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Status Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            {getStatusIcon(validation.status)}
            Validation Status
            <Badge variant="secondary" className={statusColor}>
              {statusLabel}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Specification ID</span>
                <span className="font-medium">
                  #{validation.api_specification_id}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Provider URL</span>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{validation.provider_url}</span>
                  <Button variant="ghost" size="sm" asChild>
                    <a
                      href={validation.provider_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </Button>
                </div>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Authentication</span>
                <span className="font-medium">{validation.auth_method}</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max Examples</span>
                <span className="font-medium">
                  {validation.max_examples || "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Timeout</span>
                <span className="font-medium">
                  {validation.timeout ? `${validation.timeout}s` : "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Duration</span>
                <span className="font-medium">
                  {formatDuration(results?.duration)}
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Test Strategies */}
      {validation.test_strategies && validation.test_strategies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Test Strategies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {validation.test_strategies.map((strategy) => (
                <Badge key={strategy} variant="outline">
                  {strategy.replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {results ? (
        <div className="space-y-6">
          {/* Error Message */}
          {results.error && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-destructive" />
                <p className="text-destructive font-medium">Validation Error</p>
              </div>
              <p className="text-destructive mt-1">{results.error}</p>
            </div>
          )}

          {/* Summary Statistics */}
          {results.total_tests && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Test Summary</CardTitle>
              </CardHeader>
              <CardContent>{renderSummaryStats(results)}</CardContent>
            </Card>
          )}

          {/* Coverage Information */}
          {renderCoverageInfo(results)}

          {/* Detailed Test Results */}
          {renderTestResults(results)}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-8">
            <div className="text-muted-foreground">
              {validation.status === "pending" ||
              validation.status === "running"
                ? "Validation is in progress. Results will appear here when available."
                : "No test results available for this validation."}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
