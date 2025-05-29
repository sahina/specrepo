import type { APISpecification, ValidationRun } from "@/services/api";
import { useState } from "react";
import { ContractHealthDashboard } from "./ContractHealthDashboard";
import { ContractSketches } from "./ContractSketches";
import { HARManager } from "./HARManager";
import { Header } from "./Header";
import { Settings } from "./Settings";
import { SpecificationDetail } from "./SpecificationDetail";
import { SpecificationsList } from "./SpecificationsList";
import { ValidationForm } from "./ValidationForm";
import { ValidationResults } from "./ValidationResults";
import { ValidationsList } from "./ValidationsList";

type DashboardView =
  | "overview"
  | "specifications"
  | "validations"
  | "har-uploads"
  | "contract-sketches"
  | "contract-health"
  | "settings"
  | "specification-detail"
  | "specification-view"
  | "specification-create"
  | "validation-results"
  | "validation-trigger";

interface DashboardState {
  view: DashboardView;
  selectedSpecificationId?: number;
  selectedValidationId?: number;
  selectedHARUploadId?: number;
}

export function Dashboard() {
  const [state, setState] = useState<DashboardState>({ view: "overview" });

  const handleViewSpecification = (spec: APISpecification) => {
    setState({
      view: "specification-view",
      selectedSpecificationId: spec.id,
    });
  };

  const handleEditSpecification = (spec: APISpecification) => {
    setState({
      view: "specification-detail",
      selectedSpecificationId: spec.id,
    });
  };

  const handleEditFromView = () => {
    setState((prev) => ({
      ...prev,
      view: "specification-detail",
    }));
  };

  const handleCreateNewSpecification = () => {
    setState({ view: "specification-create" });
  };

  const handleBackToSpecifications = () => {
    setState({ view: "specifications" });
  };

  const handleSpecificationSaved = (spec: APISpecification) => {
    // After saving, go back to specifications list
    // The spec parameter contains the saved specification data
    console.log("Specification saved:", spec.name);
    setState({ view: "specifications" });
  };

  const handleViewValidationResults = (validation: ValidationRun) => {
    setState({
      view: "validation-results",
      selectedValidationId: validation.id,
    });
  };

  const handleTriggerValidation = () => {
    setState({ view: "validation-trigger" });
  };

  const handleValidationTriggered = (validationId: number) => {
    setState({
      view: "validation-results",
      selectedValidationId: validationId,
    });
  };

  const handleBackToValidations = () => {
    setState({ view: "validations" });
  };

  const handleViewContractSketches = (uploadId: number) => {
    setState({
      view: "contract-sketches",
      selectedHARUploadId: uploadId,
    });
  };

  const handleBackToHARUploads = () => {
    setState({ view: "har-uploads" });
  };

  const handleNavigate = (view: string) => {
    setState({ view: view as DashboardView });
  };

  // Contract Sketches View
  if (state.view === "contract-sketches" && state.selectedHARUploadId) {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <ContractSketches
            uploadId={state.selectedHARUploadId}
            onBack={handleBackToHARUploads}
          />
        </div>
      </div>
    );
  }

  // HAR Uploads View
  if (state.view === "har-uploads") {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <HARManager
            onBack={() => setState({ view: "overview" })}
            onViewContractSketches={handleViewContractSketches}
          />
        </div>
      </div>
    );
  }

  // Validation Trigger View
  if (state.view === "validation-trigger") {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <ValidationForm
            onValidationTriggered={handleValidationTriggered}
            onCancel={handleBackToValidations}
          />
        </div>
      </div>
    );
  }

  // Validation Results View
  if (state.view === "validation-results" && state.selectedValidationId) {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <ValidationResults
            validationId={state.selectedValidationId}
            onBack={handleBackToValidations}
          />
        </div>
      </div>
    );
  }

  // Specification Detail View (Edit)
  if (state.view === "specification-detail" && state.selectedSpecificationId) {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <SpecificationDetail
            specificationId={state.selectedSpecificationId}
            onBack={handleBackToSpecifications}
            onSave={handleSpecificationSaved}
          />
        </div>
      </div>
    );
  }

  // Specification View (Read-only)
  if (state.view === "specification-view" && state.selectedSpecificationId) {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <SpecificationDetail
            specificationId={state.selectedSpecificationId}
            onBack={handleBackToSpecifications}
            onSave={handleSpecificationSaved}
            onEdit={handleEditFromView}
            readOnly={true}
          />
        </div>
      </div>
    );
  }

  // Specification Create View
  if (state.view === "specification-create") {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <SpecificationDetail
            onBack={handleBackToSpecifications}
            onSave={handleSpecificationSaved}
          />
        </div>
      </div>
    );
  }

  // Specifications List View
  if (state.view === "specifications") {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <SpecificationsList
            onCreateNew={handleCreateNewSpecification}
            onView={handleViewSpecification}
            onEdit={handleEditSpecification}
          />
        </div>
      </div>
    );
  }

  // Validations List View
  if (state.view === "validations") {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <ValidationsList
            onViewResults={handleViewValidationResults}
            onTriggerValidation={handleTriggerValidation}
          />
        </div>
      </div>
    );
  }

  // Settings View
  if (state.view === "settings") {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <Settings />
        </div>
      </div>
    );
  }

  // Contract Health View
  if (state.view === "contract-health") {
    return (
      <div className="min-h-screen bg-background">
        <Header currentView={state.view} onNavigate={handleNavigate} />
        <div className="container mx-auto px-4 py-8">
          <ContractHealthDashboard />
        </div>
      </div>
    );
  }

  // Overview/Dashboard View
  return (
    <div className="min-h-screen bg-background">
      <Header currentView={state.view} onNavigate={handleNavigate} />
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
                onClick={() => setState({ view: "specifications" })}
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
                onClick={() => setState({ view: "validations" })}
              >
                View Reports
              </button>
            </div>

            <div className="bg-card border rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-3">Contract Health</h2>
              <p className="text-muted-foreground mb-4">
                Monitor contract health and validation status across all APIs
              </p>
              <button
                className="bg-accent text-accent-foreground px-4 py-2 rounded-md hover:bg-accent/90 transition-colors"
                onClick={() => setState({ view: "contract-health" })}
              >
                View Dashboard
              </button>
            </div>

            <div className="bg-card border rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-3">HAR Uploads</h2>
              <p className="text-muted-foreground mb-4">
                Upload and analyze HTTP Archive files to generate API specs
              </p>
              <button
                className="bg-accent text-accent-foreground px-4 py-2 rounded-md hover:bg-accent/90 transition-colors"
                onClick={() => setState({ view: "har-uploads" })}
              >
                Manage HAR Files
              </button>
            </div>

            <div className="bg-card border rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-3">Notifications</h2>
              <p className="text-muted-foreground mb-4">
                Configure email notifications for validation results
              </p>
              <button
                className="bg-accent text-accent-foreground px-4 py-2 rounded-md hover:bg-accent/90 transition-colors"
                onClick={() => setState({ view: "settings" })}
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
                <span className="text-sm text-muted-foreground">
                  1 hour ago
                </span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span>Email notification sent</span>
                <span className="text-sm text-muted-foreground">
                  3 hours ago
                </span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
