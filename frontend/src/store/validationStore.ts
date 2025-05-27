import { create } from "zustand";

export interface ValidationResult {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  timestamp: string;
  apiSpec: string;
  results?: {
    totalTests: number;
    passed: number;
    failed: number;
    errors: string[];
  };
}

interface ValidationStore {
  validations: ValidationResult[];
  isLoading: boolean;
  addValidation: (
    validation: Omit<ValidationResult, "id" | "timestamp">,
  ) => void;
  updateValidation: (id: string, updates: Partial<ValidationResult>) => void;
  setLoading: (loading: boolean) => void;
}

export const useValidationStore = create<ValidationStore>((set) => ({
  validations: [
    {
      id: "1",
      status: "completed",
      timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
      apiSpec: "petstore-api.yaml",
      results: {
        totalTests: 150,
        passed: 145,
        failed: 5,
        errors: ["Invalid response format in /pets endpoint"],
      },
    },
    {
      id: "2",
      status: "running",
      timestamp: new Date(Date.now() - 30 * 1000).toISOString(),
      apiSpec: "user-management-api.yaml",
    },
  ],
  isLoading: false,

  addValidation: (validation) =>
    set((state) => ({
      validations: [
        {
          ...validation,
          id: Date.now().toString(),
          timestamp: new Date().toISOString(),
        },
        ...state.validations,
      ],
    })),

  updateValidation: (id, updates) =>
    set((state) => ({
      validations: state.validations.map((validation) =>
        validation.id === id ? { ...validation, ...updates } : validation,
      ),
    })),

  setLoading: (loading) => set({ isLoading: loading }),
}));
