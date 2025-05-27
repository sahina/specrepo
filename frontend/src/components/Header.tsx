import { useAuthStore } from "../store/authStore";

export function Header() {
  const { logout, apiKey } = useAuthStore();

  const handleLogout = () => {
    logout();
  };

  // Mask the API key for display (show only first 4 and last 4 characters)
  const maskedApiKey = apiKey
    ? `${apiKey.slice(0, 4)}${"*".repeat(
        Math.max(0, apiKey.length - 8),
      )}${apiKey.slice(-4)}`
    : "";

  return (
    <header className="bg-card border-b border-border">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">
              Schemathesis Validation Platform
            </h1>
            <p className="text-muted-foreground text-sm">
              Automated API testing and validation
            </p>
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-sm text-muted-foreground">
              <span className="font-medium">API Key:</span> {maskedApiKey}
            </div>
            <button
              onClick={handleLogout}
              className="bg-secondary text-secondary-foreground px-3 py-1 rounded-md hover:bg-secondary/90 transition-colors text-sm"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
