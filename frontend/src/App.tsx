import { useState } from "react";
import "./index.css";

function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-4">
            Schemathesis Validation Platform
          </h1>
          <p className="text-muted-foreground text-lg">
            Automated API testing and validation with Schemathesis
          </p>
        </header>

        <main className="max-w-4xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-card border rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-3">API Validation</h2>
              <p className="text-muted-foreground mb-4">
                Upload and validate your OpenAPI specifications
              </p>
              <button
                className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                onClick={() => setCount((count) => count + 1)}
              >
                Start Validation ({count})
              </button>
            </div>

            <div className="bg-card border rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-3">Test Results</h2>
              <p className="text-muted-foreground mb-4">
                View detailed validation reports and test outcomes
              </p>
              <button className="bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/90 transition-colors">
                View Reports
              </button>
            </div>

            <div className="bg-card border rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-3">Notifications</h2>
              <p className="text-muted-foreground mb-4">
                Configure email notifications for validation results
              </p>
              <button className="bg-accent text-accent-foreground px-4 py-2 rounded-md hover:bg-accent/90 transition-colors">
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

export default App;
