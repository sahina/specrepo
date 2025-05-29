# Docker Compose Configuration Guide

This guide explains the Docker Compose setup for SpecRepo, including different configurations for development and production environments.

## Overview

SpecRepo uses multiple Docker Compose files to support different deployment scenarios:

- `docker-compose.yml` - Base development configuration
- `docker-compose.override.yml` - Development tools and debugging
- `docker-compose.prod.yml` - Production-optimized configuration

## Quick Start

### Development Environment

```bash
# Start all services for development
make dev-up

# Or manually:
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Environment

```bash
# Start production services
make prod-up

# Or manually:
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

## Service Architecture

### Core Services

#### Backend API (`backend`)

- **Development**: Hot-reloading with uvicorn
- **Production**: Optimized multi-stage build
- **Port**: 8000
- **Health Check**: `/health` endpoint
- **Dependencies**: PostgreSQL

#### Frontend (`frontend`)

- **Development**: Vite dev server with hot-reloading
- **Production**: Nginx serving optimized build
- **Port**: 5173 (dev), 8080 (prod)
- **Health Check**: `/health` endpoint
- **Dependencies**: Backend API

#### PostgreSQL Database (`postgres`)

- **Image**: postgres:15-alpine
- **Port**: 5432
- **Persistent Storage**: `postgres_data` volume
- **Health Check**: `pg_isready` command
- **Initialization**: `scripts/init-db.sql`

#### WireMock (`wiremock`)

- **Image**: wiremock/wiremock:3.3.1
- **Port**: 8081
- **Purpose**: API mocking and testing
- **Configuration**: `wiremock/mappings` and `wiremock/files`

#### n8n Workflow Automation (`n8n`)

- **Image**: n8nio/n8n:1.19.4
- **Port**: 5679
- **Purpose**: Workflow automation and webhooks
- **Persistent Storage**: `n8n_data` volume
- **Configuration**: `n8n/workflows`

### Development-Only Services

#### Test Database (`postgres_test`)

- **Purpose**: Isolated testing environment
- **Port**: 5433
- **Database**: `appdb_test`

#### pgAdmin (`pgadmin`)

- **Purpose**: Database administration
- **Port**: 5050
- **Credentials**: <admin@specrepo.dev> / admin

#### Redis (`redis`)

- **Purpose**: Caching and session storage
- **Port**: 6379
- **Persistent Storage**: `redis_data` volume

## Configuration Files

### docker-compose.yml (Development Base)

This is the primary development configuration with:

- Hot-reloading for both frontend and backend
- Development-friendly logging levels
- Volume mounts for live code editing
- Higher rate limits for testing

Key features:

- Backend uses `builder` target for development tools
- Frontend uses `Dockerfile.dev` for Vite dev server
- All services connected via `app-network`
- Health checks for service dependencies

### docker-compose.override.yml (Development Tools)

Automatically loaded in development, adds:

- Additional debugging tools
- Test database
- pgAdmin for database management
- Redis for caching
- Enhanced logging and debugging

### docker-compose.prod.yml (Production)

Optimized for production with:

- Multi-stage builds for smaller images
- Resource limits and reservations
- Environment variable substitution
- Production-grade health checks
- Optimized networking configuration

## Environment Variables

### Required Variables

Copy `scripts/env.example` to `.env` and configure:

```bash
# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=appdb

# n8n
N8N_API_KEY=your-api-key
N8N_WEBHOOK_SECRET=your-webhook-secret

# Application
LOG_LEVEL=INFO
RATE_LIMIT_MAX_ATTEMPTS=100
```

### Production-Specific Variables

```bash
# Security
JWT_SECRET=your-secure-jwt-secret
API_SECRET_KEY=your-api-secret

# Monitoring
SENTRY_DSN=your-sentry-dsn
MONITORING_ENABLED=true

# Performance
WORKER_PROCESSES=4
DB_POOL_SIZE=20
```

## Networking

### Development Network

- **Name**: `app-network`
- **Driver**: bridge
- **Subnet**: Auto-assigned

### Production Network

- **Name**: `app-network`
- **Driver**: bridge
- **Subnet**: 172.20.0.0/16 (explicitly defined)

## Volumes

### Persistent Data

- `postgres_data`: Database files
- `n8n_data`: n8n workflows and data
- `wiremock_data`: WireMock persistent data (production)

### Development Volumes

- `frontend_node_modules`: Node.js dependencies cache
- `backend_cache`: Python virtual environment cache
- `pgadmin_data`: pgAdmin configuration
- `redis_data`: Redis data

## Health Checks

All services include comprehensive health checks:

- **Backend**: HTTP check on `/health`
- **Frontend**: HTTP check on `/health`
- **PostgreSQL**: `pg_isready` command
- **WireMock**: Admin health endpoint
- **n8n**: Health endpoint check

## Resource Management

### Development

- No resource limits (unlimited for development)
- Optimized for developer experience

### Production

Resource limits per service:

```yaml
backend:
  limits: 1 CPU, 1GB RAM
  reservations: 0.5 CPU, 512MB RAM

frontend:
  limits: 0.5 CPU, 256MB RAM
  reservations: 0.25 CPU, 128MB RAM

postgres:
  limits: 1 CPU, 1GB RAM
  reservations: 0.5 CPU, 512MB RAM
```

## Security Considerations

### Development

- Default credentials for ease of use
- Debug logging enabled
- All ports exposed for testing

### Production

- Environment variable substitution for secrets
- Non-root users in containers
- Read-only volume mounts where possible
- Security headers in nginx configuration

## Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]
```

#### Database Connection Issues

```bash
# Check database health
docker-compose exec postgres pg_isready -U user -d appdb

# Connect to database
docker-compose exec postgres psql -U user -d appdb
```

#### Frontend Build Issues

```bash
# Rebuild frontend
docker-compose build frontend

# Clear node_modules volume
docker volume rm specrepo_frontend_node_modules
```

### Performance Issues

#### Slow Startup

- Increase health check intervals
- Check available system resources
- Review Docker Desktop resource allocation

#### High Memory Usage

- Review resource limits in production
- Check for memory leaks in application logs
- Monitor container resource usage

## Maintenance

### Regular Tasks

#### Update Images

```bash
# Pull latest images
docker-compose pull

# Rebuild with latest base images
docker-compose build --no-cache
```

#### Clean Up

```bash
# Remove unused volumes
docker volume prune

# Remove unused images
docker image prune

# Complete cleanup
docker system prune -a
```

#### Backup Data

```bash
# Backup database
docker-compose exec postgres pg_dump -U user appdb > backup.sql

# Backup n8n data
docker run --rm -v specrepo_n8n_data:/data -v $(pwd):/backup alpine tar czf /backup/n8n-backup.tar.gz -C /data .
```

## Development Workflow

### Starting Development

1. Copy `scripts/env.example` to `.env`
2. Update environment variables
3. Run `make dev-up` or `docker-compose up -d`
4. Access services:
   - Frontend: <http://localhost:5173>
   - Backend API: <http://localhost:8000>
   - API Docs: <http://localhost:8000/docs>
   - pgAdmin: <http://localhost:5050>
   - n8n: <http://localhost:5679>

### Making Changes

- Code changes are automatically reflected (hot-reload)
- Database schema changes require migration
- New dependencies require container rebuild

### Testing

- Use test database on port 5433
- Run tests with `make test`
- Integration tests use Docker services

## Production Deployment

### Prerequisites

- Docker and Docker Compose installed
- Environment variables configured
- SSL certificates (if using HTTPS)
- Monitoring tools configured

### Deployment Steps

1. Configure production environment variables
2. Build production images: `docker-compose -f docker-compose.prod.yml build`
3. Start services: `docker-compose -f docker-compose.prod.yml up -d`
4. Verify health checks: `docker-compose -f docker-compose.prod.yml ps`
5. Monitor logs: `docker-compose -f docker-compose.prod.yml logs -f`

### Monitoring

- Health check endpoints for all services
- Resource usage monitoring
- Application logs centralization
- Error tracking with Sentry (if configured)

## Advanced Configuration

### Custom Networks

```yaml
networks:
  app-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
```

### External Services

```yaml
services:
  external-db:
    external: true
    external_name: production-postgres
```

### Secrets Management

```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

## Best Practices

1. **Environment Separation**: Use different compose files for different environments
2. **Secret Management**: Never commit secrets to version control
3. **Resource Limits**: Always set resource limits in production
4. **Health Checks**: Implement comprehensive health checks
5. **Logging**: Use structured logging with appropriate levels
6. **Monitoring**: Implement monitoring and alerting
7. **Backups**: Regular automated backups of persistent data
8. **Updates**: Keep base images and dependencies updated
9. **Security**: Follow security best practices for containers
10. **Documentation**: Keep configuration documented and up-to-date
