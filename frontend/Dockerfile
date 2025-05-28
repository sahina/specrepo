# Use an official Node runtime as a parent image
FROM --platform=linux/arm64 node:20-bookworm-slim

# Install build tools that might be needed for native modules
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install and setup pnpm
RUN npm install -g pnpm
ENV ROLLUP_NO_NATIVE=true

# Copy package files for dependency installation
COPY package.json pnpm-lock.yaml* ./

# Install dependencies including devDependencies for development
RUN pnpm install --frozen-lockfile

# Copy the rest of the application code
COPY . ./

# Expose port (Vite default is 5173, but can be configured)
EXPOSE 5173

# Run the application using Vite dev server
CMD ["pnpm", "run", "dev", "--host"] 