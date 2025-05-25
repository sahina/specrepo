# Project Title

A brief description of the project.

## Architecture Overview

(A placeholder for an architecture diagram or description)

## Getting Started

### Prerequisites

- Prerequisite 1
- Prerequisite 2

### Installation

1. Clone the repo

   ```sh
   git clone https://example.com/your_project.git
   ```

2. Install dependencies

   ```sh
   # Root (if applicable, e.g., for monorepo tools)
   # pnpm install

   # Frontend
   cd frontend
   pnpm install

   # Backend
   cd backend
   uv venv  # Create .venv if it doesn't exist
   uv pip sync requirements.lock # Install dependencies
   ```

### Running the Application

- Frontend: `cd frontend && pnpm dev`
- Backend: `cd backend && uv run uvicorn main:app --reload`
