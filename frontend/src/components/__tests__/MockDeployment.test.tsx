import { useApiClient } from "@/hooks/useApiClient";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MockDeployment } from "../MockDeployment";

// Mock the entire services/api module
jest.mock("@/services/api", () => ({
  __esModule: true,
  default: {
    setApiKey: jest.fn(),
    clearApiKey: jest.fn(),
    getWireMockStubs: jest.fn(),
    generateWireMockStubs: jest.fn(),
    resetWireMock: jest.fn(),
    healthCheck: jest.fn(),
    getProfile: jest.fn(),
    createSpecification: jest.fn(),
    getSpecifications: jest.fn(),
    getSpecification: jest.fn(),
    updateSpecification: jest.fn(),
    deleteSpecification: jest.fn(),
    triggerValidation: jest.fn(),
    getValidationResults: jest.fn(),
    getValidations: jest.fn(),
    clearWireMockStubs: jest.fn(),
  },
}));

// Mock the useApiClient hook
jest.mock("@/hooks/useApiClient");

const mockApiClient = {
  getWireMockStubs: jest.fn(),
  generateWireMockStubs: jest.fn(),
  resetWireMock: jest.fn(),
  // Add other required methods as no-ops for this test
  setApiKey: jest.fn(),
  clearApiKey: jest.fn(),
  healthCheck: jest.fn(),
  getProfile: jest.fn(),
  createSpecification: jest.fn(),
  getSpecifications: jest.fn(),
  getSpecification: jest.fn(),
  updateSpecification: jest.fn(),
  deleteSpecification: jest.fn(),
  triggerValidation: jest.fn(),
  getValidationResults: jest.fn(),
  getValidations: jest.fn(),
  clearWireMockStubs: jest.fn(),
} as unknown as ReturnType<typeof useApiClient>;

const mockedUseApiClient = useApiClient as jest.MockedFunction<
  typeof useApiClient
>;

describe("MockDeployment", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseApiClient.mockReturnValue(mockApiClient);
  });

  it("renders the component with initial state", async () => {
    (mockApiClient.getWireMockStubs as jest.Mock).mockResolvedValue({
      total_stubs: 0,
      stubs: [],
    });

    render(<MockDeployment specificationId={1} specificationName="Test API" />);

    expect(screen.getByText("Mock Deployment")).toBeInTheDocument();
    expect(screen.getByText("Deploy Mocks")).toBeInTheDocument();

    // Wait for the status to load
    await waitFor(() => {
      expect(screen.getByText("Not deployed")).toBeInTheDocument();
    });
  });

  it("shows deployed status when stubs exist", async () => {
    (mockApiClient.getWireMockStubs as jest.Mock).mockResolvedValue({
      total_stubs: 5,
      stubs: [
        { id: "1", request: {}, response: {} },
        { id: "2", request: {}, response: {} },
        { id: "3", request: {}, response: {} },
        { id: "4", request: {}, response: {} },
        { id: "5", request: {}, response: {} },
      ],
    });

    render(<MockDeployment specificationId={1} specificationName="Test API" />);

    await waitFor(() => {
      expect(screen.getByText("5 stubs deployed")).toBeInTheDocument();
    });

    expect(screen.getByText("Reset Mocks")).toBeInTheDocument();
    expect(screen.getByText("Mock API URLs")).toBeInTheDocument();
  });

  it("opens deploy confirmation dialog when deploy button is clicked", async () => {
    (mockApiClient.getWireMockStubs as jest.Mock).mockResolvedValue({
      total_stubs: 0,
      stubs: [],
    });

    render(<MockDeployment specificationId={1} specificationName="Test API" />);

    await waitFor(() => {
      expect(screen.getByText("Deploy Mocks")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Deploy Mocks"));

    expect(screen.getByText("Deploy Mock API")).toBeInTheDocument();
    expect(
      screen.getByText(/This will deploy "Test API" to WireMock/),
    ).toBeInTheDocument();
  });

  it("handles deployment successfully", async () => {
    (mockApiClient.getWireMockStubs as jest.Mock).mockResolvedValue({
      total_stubs: 0,
      stubs: [],
    });

    (mockApiClient.generateWireMockStubs as jest.Mock).mockResolvedValue({
      message: "Success",
      stubs_created: 3,
      stubs: [
        { id: "1", request: {}, response: {} },
        { id: "2", request: {}, response: {} },
        { id: "3", request: {}, response: {} },
      ],
    });

    render(<MockDeployment specificationId={1} specificationName="Test API" />);

    await waitFor(() => {
      expect(screen.getByText("Deploy Mocks")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Deploy Mocks"));

    // Confirm deployment
    const deployButton = screen.getByRole("button", { name: "Deploy" });
    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(mockApiClient.generateWireMockStubs).toHaveBeenCalledWith({
        specification_id: 1,
        clear_existing: true,
      });
    });
  });

  it("handles deployment errors", async () => {
    (mockApiClient.getWireMockStubs as jest.Mock).mockResolvedValue({
      total_stubs: 0,
      stubs: [],
    });

    (mockApiClient.generateWireMockStubs as jest.Mock).mockRejectedValue(
      new Error("Deployment failed"),
    );

    render(<MockDeployment specificationId={1} specificationName="Test API" />);

    await waitFor(() => {
      expect(screen.getByText("Deploy Mocks")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Deploy Mocks"));

    // Confirm deployment
    const deployButton = screen.getByRole("button", { name: "Deploy" });
    fireEvent.click(deployButton);

    await waitFor(() => {
      expect(screen.getByText("Deployment Error")).toBeInTheDocument();
      expect(screen.getByText("Deployment failed")).toBeInTheDocument();
    });
  });

  it("shows reset confirmation dialog when reset button is clicked", async () => {
    (mockApiClient.getWireMockStubs as jest.Mock).mockResolvedValue({
      total_stubs: 3,
      stubs: [
        { id: "1", request: {}, response: {} },
        { id: "2", request: {}, response: {} },
        { id: "3", request: {}, response: {} },
      ],
    });

    render(<MockDeployment specificationId={1} specificationName="Test API" />);

    await waitFor(() => {
      expect(screen.getByText("Reset Mocks")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Reset Mocks"));

    expect(screen.getByText("Reset Mock API")).toBeInTheDocument();
    expect(
      screen.getByText(/This will remove all mock endpoints/),
    ).toBeInTheDocument();
  });

  it("handles reset successfully", async () => {
    (mockApiClient.getWireMockStubs as jest.Mock).mockResolvedValue({
      total_stubs: 3,
      stubs: [
        { id: "1", request: {}, response: {} },
        { id: "2", request: {}, response: {} },
        { id: "3", request: {}, response: {} },
      ],
    });

    (mockApiClient.resetWireMock as jest.Mock).mockResolvedValue(true);

    render(<MockDeployment specificationId={1} specificationName="Test API" />);

    await waitFor(() => {
      expect(screen.getByText("Reset Mocks")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Reset Mocks"));

    // Confirm reset
    const resetButton = screen.getByRole("button", { name: "Reset" });
    fireEvent.click(resetButton);

    await waitFor(() => {
      expect(mockApiClient.resetWireMock).toHaveBeenCalled();
    });
  });

  it("displays WireMock URLs when deployed", async () => {
    (mockApiClient.getWireMockStubs as jest.Mock).mockResolvedValue({
      total_stubs: 2,
      stubs: [
        { id: "1", request: {}, response: {} },
        { id: "2", request: {}, response: {} },
      ],
    });

    render(<MockDeployment specificationId={1} specificationName="Test API" />);

    await waitFor(() => {
      expect(screen.getByText("Mock API URLs")).toBeInTheDocument();
    });

    expect(screen.getByText("http://localhost:8081")).toBeInTheDocument();
    expect(
      screen.getByText("http://localhost:8081/__admin/"),
    ).toBeInTheDocument();
  });
});
