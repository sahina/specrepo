import type {
  APISpecificationCreate,
  APISpecificationUpdate,
} from "@/services/api";
import apiClient from "@/services/api";
import { useSpecificationsStore } from "@/store/specificationsStore";
import { useCallback } from "react";

export const useSpecifications = () => {
  const {
    specifications,
    loading,
    error,
    filters,
    pagination,
    setSpecifications,
    setLoading,
    setError,
    setFilters,
    resetFilters,
    addSpecification,
    updateSpecification,
    removeSpecification,
  } = useSpecificationsStore();

  const fetchSpecifications = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getSpecifications(filters);
      setSpecifications(data);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch specifications";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [filters, setSpecifications, setLoading, setError]);

  const createSpecification = useCallback(
    async (data: APISpecificationCreate) => {
      try {
        setLoading(true);
        setError(null);
        const newSpec = await apiClient.createSpecification(data);
        addSpecification(newSpec);
        return newSpec;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to create specification";
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [addSpecification, setLoading, setError],
  );

  const updateSpecificationById = useCallback(
    async (id: number, data: APISpecificationUpdate) => {
      try {
        setLoading(true);
        setError(null);
        const updatedSpec = await apiClient.updateSpecification(id, data);
        updateSpecification(id, updatedSpec);
        return updatedSpec;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to update specification";
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [updateSpecification, setLoading, setError],
  );

  const deleteSpecification = useCallback(
    async (id: number) => {
      try {
        setLoading(true);
        setError(null);
        await apiClient.deleteSpecification(id);
        removeSpecification(id);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to delete specification";
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [removeSpecification, setLoading, setError],
  );

  const updateFilters = useCallback(
    (newFilters: Partial<typeof filters>) => {
      setFilters(newFilters);
    },
    [setFilters],
  );

  return {
    // State
    specifications,
    loading,
    error,
    filters,
    pagination,

    // Actions
    fetchSpecifications,
    createSpecification,
    updateSpecificationById,
    deleteSpecification,
    updateFilters,
    resetFilters,
  };
};
