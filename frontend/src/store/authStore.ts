import apiClient from "@/services/api";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  apiKey: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (apiKey: string) => Promise<void>;
  logout: () => void;
  validateApiKey: (apiKey: string) => boolean;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      apiKey: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (apiKey: string) => {
        if (!get().validateApiKey(apiKey)) {
          throw new Error("Invalid API key format");
        }

        set({ isLoading: true, error: null });

        try {
          // Set the API key in the client
          apiClient.setApiKey(apiKey);

          // Try to make an authenticated request to validate the key
          await apiClient.getProfile();

          // If successful, store the API key and mark as authenticated
          set({
            apiKey,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          // Clear the API key from the client
          apiClient.clearApiKey();

          set({
            apiKey: null,
            isAuthenticated: false,
            isLoading: false,
            error:
              error instanceof Error ? error.message : "Authentication failed",
          });
          throw error;
        }
      },

      logout: () => {
        apiClient.clearApiKey();
        set({
          apiKey: null,
          isAuthenticated: false,
          error: null,
        });
      },

      validateApiKey: (apiKey: string) => {
        // Basic format validation - API key should be a non-empty string
        // The actual validation happens in the login method via backend call
        return typeof apiKey === "string" && apiKey.trim().length > 0;
      },

      clearError: () => {
        set({ error: null });
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
