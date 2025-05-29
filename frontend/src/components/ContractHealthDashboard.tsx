import apiClient, {
  type APISpecification,
  type ContractHealthOverview,
  type ContractHealthStatus,
  type ContractValidation,
  type ContractValidationStatus,
  ContractHealthStatus as HealthStatus,
  ContractValidationStatus as ValidationStatus,
} from "@/services/api";
import {
  Activity,
  AlertCircle,
  BarChart3,
  CheckCircle,
  Filter,
  List,
  PieChart as PieChartIcon,
  RefreshCw,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

interface ContractHealthDashboardProps {
  onBack?: () => void;
}

interface HealthMetrics {
  specification_id: number;
  specification_name: string;
  health_score: number;
  health_status: ContractHealthStatus;
  last_validation: string;
  total_validations: number;
}

const HEALTH_COLORS = {
  [HealthStatus.HEALTHY]: "#22c55e",
  [HealthStatus.DEGRADED]: "#f59e0b",
  [HealthStatus.BROKEN]: "#ef4444",
};

const STATUS_ICONS = {
  [HealthStatus.HEALTHY]: CheckCircle,
  [HealthStatus.DEGRADED]: AlertCircle,
  [HealthStatus.BROKEN]: XCircle,
};

export function ContractHealthDashboard({
  onBack,
}: ContractHealthDashboardProps) {
  const [overview, setOverview] = useState<ContractHealthOverview | null>(null);
  const [validations, setValidations] = useState<ContractValidation[]>([]);
  const [specifications, setSpecifications] = useState<APISpecification[]>([]);
  const [healthMetrics, setHealthMetrics] = useState<HealthMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  // Filters
  const [filters, setFilters] = useState({
    healthStatus: "" as ContractHealthStatus | "",
    validationStatus: "" as ContractValidationStatus | "",
    searchTerm: "",
    sortBy: "health_score",
    sortOrder: "desc" as "asc" | "desc",
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load overview data
      const overviewData = await apiClient.getContractHealthOverview();
      setOverview(overviewData);

      // Load validations
      const validationsData = await apiClient.getContractValidations({
        page: 1,
        size: 100,
        sort_by: "triggered_at",
        sort_order: "desc",
      });
      setValidations(validationsData.items);

      // Load specifications
      const specificationsData = await apiClient.getSpecifications({
        page: 1,
        size: 100,
        sort_by: "name",
        sort_order: "asc",
      });
      setSpecifications(specificationsData.items);

      // Calculate health metrics per specification
      const metricsMap = new Map<number, HealthMetrics>();

      for (const spec of specificationsData.items) {
        const specValidations = validationsData.items.filter(
          (v) =>
            v.api_specification_id === spec.id &&
            v.status === ValidationStatus.COMPLETED,
        );

        if (specValidations.length > 0) {
          const latestValidation = specValidations[0]; // Already sorted by triggered_at desc
          metricsMap.set(spec.id, {
            specification_id: spec.id,
            specification_name: spec.name,
            health_score: latestValidation.health_score,
            health_status: latestValidation.contract_health_status,
            last_validation: latestValidation.triggered_at,
            total_validations: specValidations.length,
          });
        } else {
          metricsMap.set(spec.id, {
            specification_id: spec.id,
            specification_name: spec.name,
            health_score: 0,
            health_status: HealthStatus.BROKEN,
            last_validation: "Never",
            total_validations: 0,
          });
        }
      }

      setHealthMetrics(Array.from(metricsMap.values()));
    } catch (err) {
      console.error("Error loading dashboard data:", err);
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredMetrics = healthMetrics
    .filter((metric) => {
      if (
        filters.healthStatus &&
        metric.health_status !== filters.healthStatus
      ) {
        return false;
      }
      if (
        filters.searchTerm &&
        !metric.specification_name
          .toLowerCase()
          .includes(filters.searchTerm.toLowerCase())
      ) {
        return false;
      }
      return true;
    })
    .sort((a, b) => {
      const aValue = a[filters.sortBy as keyof HealthMetrics];
      const bValue = b[filters.sortBy as keyof HealthMetrics];

      if (typeof aValue === "string" && typeof bValue === "string") {
        return filters.sortOrder === "asc"
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === "number" && typeof bValue === "number") {
        return filters.sortOrder === "asc" ? aValue - bValue : bValue - aValue;
      }

      return 0;
    });

  const getHealthBadgeVariant = (status: ContractHealthStatus) => {
    switch (status) {
      case HealthStatus.HEALTHY:
        return "default";
      case HealthStatus.DEGRADED:
        return "secondary";
      case HealthStatus.BROKEN:
        return "destructive";
      default:
        return "outline";
    }
  };

  const formatHealthScore = (score: number) => {
    return `${(score * 100).toFixed(1)}%`;
  };

  const formatDate = (dateString: string) => {
    if (dateString === "Never") return dateString;
    return new Date(dateString).toLocaleDateString();
  };

  // Prepare chart data
  const healthDistributionData = overview
    ? [
        {
          name: "Healthy",
          value: overview.overall_health_distribution.healthy,
          color: HEALTH_COLORS[HealthStatus.HEALTHY],
        },
        {
          name: "Degraded",
          value: overview.overall_health_distribution.degraded,
          color: HEALTH_COLORS[HealthStatus.DEGRADED],
        },
        {
          name: "Broken",
          value: overview.overall_health_distribution.broken,
          color: HEALTH_COLORS[HealthStatus.BROKEN],
        },
      ]
    : [];

  const healthScoreData = filteredMetrics.map((metric) => ({
    name:
      metric.specification_name.length > 15
        ? `${metric.specification_name.substring(0, 15)}...`
        : metric.specification_name,
    score: metric.health_score * 100,
    status: metric.health_status,
  }));

  const recentValidationsData =
    overview?.recent_validations.map((validation) => ({
      date: new Date(validation.triggered_at).toLocaleDateString(),
      score: validation.health_score * 100,
      status: validation.health_status,
    })) || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <XCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
          <p className="text-destructive">{error}</p>
          <Button onClick={loadData} className="mt-4">
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
          <h1 className="text-3xl font-bold">Contract Health Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor the health and validation status of your API contracts
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={loadData} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {onBack && (
            <Button onClick={onBack} variant="outline">
              Back
            </Button>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Specifications
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview?.total_specifications || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              API specifications monitored
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Validations
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview?.total_validations || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Contract validations performed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Average Health Score
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview
                ? formatHealthScore(overview.average_health_score)
                : "0%"}
            </div>
            <p className="text-xs text-muted-foreground">
              Across all specifications
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Healthy Contracts
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {overview?.overall_health_distribution.healthy || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Out of {overview?.total_validations || 0} validations
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs
        defaultValue="overview"
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-4"
      >
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="specifications">Specifications</TabsTrigger>
          <TabsTrigger value="validations">Recent Validations</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Health Distribution Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <PieChartIcon className="h-5 w-5 mr-2" />
                  Health Status Distribution
                </CardTitle>
                <CardDescription>
                  Distribution of contract health across all validations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={healthDistributionData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {healthDistributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Health Score Trends */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <TrendingUp className="h-5 w-5 mr-2" />
                  Recent Validation Trends
                </CardTitle>
                <CardDescription>
                  Health scores from recent validations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={recentValidationsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip
                      formatter={(value) => [`${value}%`, "Health Score"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="#8884d8"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="specifications" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Filter className="h-5 w-5 mr-2" />
                Filters & Search
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <Label htmlFor="search">Search Specifications</Label>
                  <Input
                    id="search"
                    placeholder="Search by name..."
                    value={filters.searchTerm}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        searchTerm: e.target.value,
                      }))
                    }
                  />
                </div>

                <div>
                  <Label>Health Status</Label>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-between"
                      >
                        {filters.healthStatus || "All Statuses"}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({ ...prev, healthStatus: "" }))
                        }
                      >
                        All Statuses
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({
                            ...prev,
                            healthStatus: HealthStatus.HEALTHY,
                          }))
                        }
                      >
                        Healthy
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({
                            ...prev,
                            healthStatus: HealthStatus.DEGRADED,
                          }))
                        }
                      >
                        Degraded
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({
                            ...prev,
                            healthStatus: HealthStatus.BROKEN,
                          }))
                        }
                      >
                        Broken
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div>
                  <Label>Sort By</Label>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-between"
                      >
                        {filters.sortBy === "health_score"
                          ? "Health Score"
                          : filters.sortBy === "specification_name"
                          ? "Name"
                          : "Last Validation"}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({
                            ...prev,
                            sortBy: "health_score",
                          }))
                        }
                      >
                        Health Score
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({
                            ...prev,
                            sortBy: "specification_name",
                          }))
                        }
                      >
                        Name
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({
                            ...prev,
                            sortBy: "last_validation",
                          }))
                        }
                      >
                        Last Validation
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div>
                  <Label>Sort Order</Label>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-between"
                      >
                        {filters.sortOrder === "asc"
                          ? "Ascending"
                          : "Descending"}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({ ...prev, sortOrder: "asc" }))
                        }
                      >
                        Ascending
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() =>
                          setFilters((prev) => ({ ...prev, sortOrder: "desc" }))
                        }
                      >
                        Descending
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Health Scores Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <BarChart3 className="h-5 w-5 mr-2" />
                Health Scores by Specification
              </CardTitle>
              <CardDescription>
                Current health scores for all API specifications
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart
                  data={healthScoreData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="name"
                    angle={-45}
                    textAnchor="end"
                    height={100}
                  />
                  <YAxis domain={[0, 100]} />
                  <Tooltip
                    formatter={(value) => [`${value}%`, "Health Score"]}
                  />
                  <Bar dataKey="score">
                    {healthScoreData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={HEALTH_COLORS[entry.status]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Specifications Table */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <List className="h-5 w-5 mr-2" />
                Specifications Details
              </CardTitle>
              <CardDescription>
                Detailed view of all API specifications and their health status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Specification</th>
                      <th className="text-left p-2">Health Status</th>
                      <th className="text-left p-2">Health Score</th>
                      <th className="text-left p-2">Total Validations</th>
                      <th className="text-left p-2">Last Validation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMetrics.map((metric) => {
                      const StatusIcon = STATUS_ICONS[metric.health_status];
                      return (
                        <tr
                          key={metric.specification_id}
                          className="border-b hover:bg-muted/50"
                        >
                          <td className="p-2 font-medium">
                            {metric.specification_name}
                          </td>
                          <td className="p-2">
                            <div className="flex items-center space-x-2">
                              <StatusIcon
                                className="h-4 w-4"
                                style={{
                                  color: HEALTH_COLORS[metric.health_status],
                                }}
                              />
                              <Badge
                                variant={getHealthBadgeVariant(
                                  metric.health_status,
                                )}
                              >
                                {metric.health_status}
                              </Badge>
                            </div>
                          </td>
                          <td className="p-2">
                            <div className="flex items-center space-x-2">
                              <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all"
                                  style={{
                                    width: `${metric.health_score * 100}%`,
                                    backgroundColor:
                                      HEALTH_COLORS[metric.health_status],
                                  }}
                                />
                              </div>
                              <span className="text-sm font-medium">
                                {formatHealthScore(metric.health_score)}
                              </span>
                            </div>
                          </td>
                          <td className="p-2">{metric.total_validations}</td>
                          <td className="p-2 text-muted-foreground">
                            {formatDate(metric.last_validation)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {filteredMetrics.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No specifications match the current filters
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="validations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Activity className="h-5 w-5 mr-2" />
                Recent Validations
              </CardTitle>
              <CardDescription>
                Latest contract validation results across all specifications
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Validation ID</th>
                      <th className="text-left p-2">Specification</th>
                      <th className="text-left p-2">Status</th>
                      <th className="text-left p-2">Health Status</th>
                      <th className="text-left p-2">Health Score</th>
                      <th className="text-left p-2">Triggered At</th>
                      <th className="text-left p-2">Completed At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {validations.slice(0, 20).map((validation) => {
                      const spec = specifications.find(
                        (s) => s.id === validation.api_specification_id,
                      );
                      const StatusIcon =
                        STATUS_ICONS[validation.contract_health_status];

                      return (
                        <tr
                          key={validation.id}
                          className="border-b hover:bg-muted/50"
                        >
                          <td className="p-2 font-mono text-sm">
                            {validation.id}
                          </td>
                          <td className="p-2">{spec?.name || "Unknown"}</td>
                          <td className="p-2">
                            <Badge
                              variant={
                                validation.status === ValidationStatus.COMPLETED
                                  ? "default"
                                  : validation.status ===
                                    ValidationStatus.FAILED
                                  ? "destructive"
                                  : "secondary"
                              }
                            >
                              {validation.status}
                            </Badge>
                          </td>
                          <td className="p-2">
                            <div className="flex items-center space-x-2">
                              <StatusIcon
                                className="h-4 w-4"
                                style={{
                                  color:
                                    HEALTH_COLORS[
                                      validation.contract_health_status
                                    ],
                                }}
                              />
                              <Badge
                                variant={getHealthBadgeVariant(
                                  validation.contract_health_status,
                                )}
                              >
                                {validation.contract_health_status}
                              </Badge>
                            </div>
                          </td>
                          <td className="p-2 font-medium">
                            {formatHealthScore(validation.health_score)}
                          </td>
                          <td className="p-2 text-muted-foreground">
                            {new Date(validation.triggered_at).toLocaleString()}
                          </td>
                          <td className="p-2 text-muted-foreground">
                            {validation.completed_at
                              ? new Date(
                                  validation.completed_at,
                                ).toLocaleString()
                              : "In Progress"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {validations.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No validations found
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
