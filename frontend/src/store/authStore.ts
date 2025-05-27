import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  apiKey: string | null;
  isAuthenticated: boolean;
  login: (apiKey: string) => void;
  logout: () => void;
  validateApiKey: (apiKey: string) => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      apiKey: null,
      isAuthenticated: false,

      login: (apiKey: string) => {
        if (get().validateApiKey(apiKey)) {
          set({ apiKey, isAuthenticated: true });
          return;
        }
        throw new Error("Invalid API key format");
      },

      logout: () => {
        set({ apiKey: null, isAuthenticated: false });
      },

      validateApiKey: (apiKey: string) => {
        // Basic validation - API key should be a non-empty string
        // In a real app, you might want more sophisticated validation
        return typeof apiKey === "string" && apiKey.trim().length > 0;
      },
    }),
    {
      name: "auth-storage", // localStorage key
      partialize: (state) => ({
        apiKey: state.apiKey,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
