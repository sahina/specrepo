import { Dashboard } from "@/components/Dashboard";
import { Header } from "@/components/Header";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useApiClient } from "@/hooks/useApiClient";
import "./index.css";

function App() {
  // Initialize API client with auth
  useApiClient();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <ProtectedRoute>
        <Header />
        <Dashboard />
      </ProtectedRoute>
    </div>
  );
}

export default App;
