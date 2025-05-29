import "@testing-library/jest-dom";

// Mock import.meta.env for Jest
Object.defineProperty(globalThis, "import", {
  value: {
    meta: {
      env: {
        VITE_API_BASE_URL: "http://localhost:8000",
      },
    },
  },
});

// Suppress act() warnings for async operations in useEffect
// These warnings are common when testing components with async operations
// and don't indicate actual test failures
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: unknown[]) => {
    if (
      typeof args[0] === "string" &&
      (args[0].includes("Warning: An update to") ||
        args[0].includes("An update to")) &&
      args[0].includes("inside a test was not wrapped in act")
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});
