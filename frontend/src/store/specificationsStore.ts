import {
  APISpecification,
  APISpecificationFilters,
  PaginatedResponse,
} from "@/services/api";
import { create } from "zustand";

interface SpecificationsState {
  specifications: APISpecification[];
  loading: boolean;
  error: string | null;
  filters: APISpecificationFilters;
  pagination: {
    page: number;
    size: number;
    total: number;
    pages: number;
  };

  // Actions
  setSpecifications: (data: PaginatedResponse<APISpecification>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setFilters: (filters: Partial<APISpecificationFilters>) => void;
  resetFilters: () => void;
  addSpecification: (spec: APISpecification) => void;
  updateSpecification: (id: number, spec: APISpecification) => void;
  removeSpecification: (id: number) => void;
}

const defaultFilters: APISpecificationFilters = {
  page: 1,
  size: 10,
  sort_by: "created_at",
  sort_order: "desc",
};

export const useSpecificationsStore = create<SpecificationsState>(
  (set, get) => ({
    specifications: [],
    loading: false,
    error: null,
    filters: defaultFilters,
    pagination: {
      page: 1,
      size: 10,
      total: 0,
      pages: 0,
    },

    setSpecifications: (data) => {
      set({
        specifications: data.items,
        pagination: {
          page: data.page,
          size: data.size,
          total: data.total,
          pages: data.pages,
        },
        error: null,
      });
    },

    setLoading: (loading) => set({ loading }),

    setError: (error) => set({ error, loading: false }),

    setFilters: (newFilters) => {
      const currentFilters = get().filters;
      set({
        filters: { ...currentFilters, ...newFilters },
      });
    },

    resetFilters: () => set({ filters: defaultFilters }),

    addSpecification: (spec) => {
      const { specifications } = get();
      set({ specifications: [spec, ...specifications] });
    },

    updateSpecification: (id, updatedSpec) => {
      const { specifications } = get();
      set({
        specifications: specifications.map((spec) =>
          spec.id === id ? updatedSpec : spec,
        ),
      });
    },

    removeSpecification: (id) => {
      const { specifications } = get();
      set({
        specifications: specifications.filter((spec) => spec.id !== id),
      });
    },
  }),
);
