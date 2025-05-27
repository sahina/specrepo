import { useSpecifications } from "@/hooks/useSpecifications";
import type { APISpecification } from "@/services/api";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SpecificationsList } from "../SpecificationsList";

// Mock the entire services/api module
jest.mock("@/services/api", () => ({
  __esModule: true,
  default: {
    setApiKey: jest.fn(),
    clearApiKey: jest.fn(),
    getSpecifications: jest.fn(),
    createSpecification: jest.fn(),
    updateSpecification: jest.fn(),
    deleteSpecification: jest.fn(),
  },
}));

// Mock the useSpecifications hook
jest.mock("@/hooks/useSpecifications");
const mockUseSpecifications = useSpecifications as jest.MockedFunction<
  typeof useSpecifications
>;

// Mock data
const mockSpecifications: APISpecification[] = [
  {
    id: 1,
    name: "Test API",
    version_string: "1.0.0",
    openapi_content: {},
    user_id: 1,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
  },
  {
    id: 2,
    name: "Another API",
    version_string: "2.1.0",
    openapi_content: {},
    user_id: 1,
    created_at: "2024-01-03T00:00:00Z",
  },
];

const mockFilters = {
  page: 1,
  size: 10,
  sort_by: "created_at" as const,
  sort_order: "desc" as const,
};

const mockHookReturn = {
  specifications: mockSpecifications,
  loading: false,
  error: null,
  filters: mockFilters,
  pagination: {
    page: 1,
    size: 10,
    total: 2,
    pages: 1,
  },
  fetchSpecifications: jest.fn(),
  deleteSpecification: jest.fn(),
  updateFilters: jest.fn(),
  resetFilters: jest.fn(),
  createSpecification: jest.fn(),
  updateSpecificationById: jest.fn(),
};

describe("SpecificationsList", () => {
  beforeEach(() => {
    mockUseSpecifications.mockReturnValue(mockHookReturn);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the specifications list with data", () => {
    render(<SpecificationsList />);

    expect(screen.getByText("API Specifications")).toBeInTheDocument();
    expect(screen.getByText("Test API")).toBeInTheDocument();
    expect(screen.getByText("Another API")).toBeInTheDocument();
    expect(screen.getByText("1.0.0")).toBeInTheDocument();
    expect(screen.getByText("2.1.0")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    mockUseSpecifications.mockReturnValue({
      ...mockHookReturn,
      loading: true,
      specifications: [],
    });

    render(<SpecificationsList />);

    expect(screen.getByText("Loading specifications...")).toBeInTheDocument();
  });

  it("shows error state", () => {
    mockUseSpecifications.mockReturnValue({
      ...mockHookReturn,
      error: "Failed to load specifications",
      specifications: [],
    });

    render(<SpecificationsList />);

    expect(
      screen.getByText("Error Loading Specifications"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Failed to load specifications"),
    ).toBeInTheDocument();
  });

  it("shows empty state when no specifications", () => {
    mockUseSpecifications.mockReturnValue({
      ...mockHookReturn,
      specifications: [],
    });

    render(<SpecificationsList />);

    expect(screen.getByText("No specifications found.")).toBeInTheDocument();
  });

  it("calls onCreateNew when create button is clicked", () => {
    const onCreateNew = jest.fn();
    render(<SpecificationsList onCreateNew={onCreateNew} />);

    fireEvent.click(screen.getByText("Create New Specification"));
    expect(onCreateNew).toHaveBeenCalled();
  });

  it("filters specifications when search term is entered", async () => {
    render(<SpecificationsList />);

    const searchInput = screen.getByPlaceholderText("Search specifications...");
    fireEvent.change(searchInput, { target: { value: "Test" } });

    await waitFor(() => {
      expect(mockHookReturn.updateFilters).toHaveBeenCalledWith({
        name: "Test",
        sort_by: "created_at",
        sort_order: "desc",
        page: 1,
      });
    });
  });

  it("resets filters when clear filters button is clicked", () => {
    render(<SpecificationsList />);

    fireEvent.click(screen.getByText("Clear Filters"));
    expect(mockHookReturn.resetFilters).toHaveBeenCalled();
  });
});
