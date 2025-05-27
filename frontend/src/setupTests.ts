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
