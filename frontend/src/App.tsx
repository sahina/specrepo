import { Dashboard } from "@/components/Dashboard";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useApiClient } from "@/hooks/useApiClient";
import "./index.css";

function App() {
  // Initialize API client with auth
  useApiClient();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    </div>
  );
}

export default App;
