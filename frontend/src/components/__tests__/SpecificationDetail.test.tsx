import { render, screen } from "@testing-library/react";
import { SpecificationDetail } from "../SpecificationDetail";

// Mock the Monaco Editor
jest.mock("@monaco-editor/react", () => ({
  __esModule: true,
  default: ({
    value,
    onChange,
  }: {
    value: string;
    onChange: (value: string) => void;
  }) => (
    <textarea
      data-testid="monaco-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

// Mock the useApiClient hook
jest.mock("../../hooks/useApiClient", () => ({
  useApiClient: () => ({
    getSpecification: jest.fn(),
    createSpecification: jest.fn(),
    updateSpecification: jest.fn(),
  }),
}));

describe("SpecificationDetail", () => {
  const mockOnBack = jest.fn();
  const mockOnSave = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders create mode correctly", () => {
    render(<SpecificationDetail onBack={mockOnBack} onSave={mockOnSave} />);

    expect(screen.getByText("Create API Specification")).toBeInTheDocument();
    expect(screen.getByText("Specification Details")).toBeInTheDocument();
    expect(screen.getByText("OpenAPI Content")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /back/i })).toBeInTheDocument();
  });

  it("renders form fields correctly", () => {
    render(<SpecificationDetail onBack={mockOnBack} onSave={mockOnSave} />);

    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Version")).toBeInTheDocument();
    expect(screen.getByTestId("monaco-editor")).toBeInTheDocument();
  });

  it("shows unsaved changes indicator", () => {
    render(<SpecificationDetail onBack={mockOnBack} onSave={mockOnSave} />);

    // Initially no unsaved changes
    expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
  });

  it("renders edit mode when specificationId is provided", () => {
    render(
      <SpecificationDetail
        specificationId={1}
        onBack={mockOnBack}
        onSave={mockOnSave}
      />,
    );

    expect(screen.getByText("Edit API Specification")).toBeInTheDocument();
  });
});
