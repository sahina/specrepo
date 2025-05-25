# SpecRepo

A project for managing and collaborating on specifications using a web interface and AI-powered task management.

## Architecture Overview

(A placeholder for an architecture diagram or description)

## Getting Started

### Prerequisites

- Node.js (with pnpm)
- Python (with uv)
- Git

### Installation

1. Clone the repo

   ```sh
   git clone https://github.com/sahina/specrepo.git # Replace with actual repo URL
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
