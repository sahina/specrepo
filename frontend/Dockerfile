# Use an official Node runtime as a parent image
FROM --platform=linux/arm64 node:20-bookworm-slim

# Install build tools that might be needed for native modules
RUN apt-get update && apt-get install -y --no-install-recommends python3 make g++ \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install and setup pnpm
RUN npm install -g pnpm
ENV ROLLUP_NO_NATIVE=true

# Copy configuration files and package manifests
COPY package.json ./
COPY tsconfig.json ./
# COPY pnpm-lock.yaml ./ # We will remove it before install

# Clean install & try shamefully-hoist
RUN rm -rf node_modules pnpm-lock.yaml # Ensure lockfile is gone before fresh resolve
RUN pnpm install --shamefully-hoist

# Aggressively try to disable Rollup native module by removing its loader
RUN find /app/node_modules/.pnpm -path '*/rollup/dist/native.js' -delete

# Copy the rest of the application code
COPY . ./

# Build the app (if you have a build step for production)
# RUN pnpm run build # Uncomment if you want to build here

# Expose port (Vite default is 5173, but can be configured)
EXPOSE 5173

# Run the application using Vite dev server
CMD ["pnpm", "run", "dev", "--host"] 