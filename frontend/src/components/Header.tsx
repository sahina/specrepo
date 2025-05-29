import { useAuthStore } from "../store/authStore";

interface HeaderProps {
  currentView: string;
  onNavigate: (view: string) => void;
}

export function Header({ currentView, onNavigate }: HeaderProps) {
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

  const navigationItems = [
    { id: "overview", label: "Overview" },
    { id: "specifications", label: "Specifications" },
    { id: "validations", label: "Validations" },
    { id: "contract-health", label: "Contract Health" },
    { id: "har-uploads", label: "HAR Uploads" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <header className="bg-card border-b border-border">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <div>
              <h1 className="text-2xl font-bold">SpecRepo</h1>
              <p className="text-muted-foreground text-sm">
                API Lifecycle Management Platform
              </p>
            </div>

            {/* Navigation Menu */}
            <nav className="hidden md:flex space-x-6">
              {navigationItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    currentView === item.id ||
                    (item.id === "specifications" &&
                      (currentView === "specification-detail" ||
                        currentView === "specification-view" ||
                        currentView === "specification-create")) ||
                    (item.id === "validations" &&
                      (currentView === "validation-trigger" ||
                        currentView === "validation-results"))
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>
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
