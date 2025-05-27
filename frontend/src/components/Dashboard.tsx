import type { APISpecification } from "@/services/api";
import { useState } from "react";
import { SpecificationsList } from "./SpecificationsList";

type DashboardView = "overview" | "specifications" | "validations" | "settings";

export function Dashboard() {
  const [currentView, setCurrentView] = useState<DashboardView>("overview");

  const handleViewSpecification = (spec: APISpecification) => {
    // TODO: Navigate to specification detail view
    console.log("View specification:", spec);
  };

  const handleEditSpecification = (spec: APISpecification) => {
    // TODO: Navigate to specification edit view
    console.log("Edit specification:", spec);
  };

  const handleCreateNewSpecification = () => {
    // TODO: Navigate to specification create view
    console.log("Create new specification");
  };

  if (currentView === "specifications") {
    return (
      <div className="container mx-auto px-4 py-8">
        <SpecificationsList
          onCreateNew={handleCreateNewSpecification}
          onView={handleViewSpecification}
          onEdit={handleEditSpecification}
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <main className="max-w-4xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-3">API Specifications</h2>
            <p className="text-muted-foreground mb-4">
              Manage your OpenAPI specifications and run validations
            </p>
            <button
              className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
              onClick={() => setCurrentView("specifications")}
            >
              Manage Specifications
            </button>
          </div>

          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-3">Test Results</h2>
            <p className="text-muted-foreground mb-4">
              View detailed validation reports and test outcomes
            </p>
            <button
              className="bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/90 transition-colors"
              onClick={() => setCurrentView("validations")}
            >
              View Reports
            </button>
          </div>

          <div className="bg-card border rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-3">Notifications</h2>
            <p className="text-muted-foreground mb-4">
              Configure email notifications for validation results
            </p>
            <button
              className="bg-accent text-accent-foreground px-4 py-2 rounded-md hover:bg-accent/90 transition-colors"
              onClick={() => setCurrentView("settings")}
            >
              Settings
            </button>
          </div>
        </div>

        <div className="mt-12 bg-muted rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-3">Recent Activity</h3>
          <div className="space-y-2">
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span>API validation completed</span>
              <span className="text-sm text-muted-foreground">
                2 minutes ago
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span>New test suite uploaded</span>
              <span className="text-sm text-muted-foreground">1 hour ago</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span>Email notification sent</span>
              <span className="text-sm text-muted-foreground">3 hours ago</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
