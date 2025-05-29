# SpecRepo Deployment Guide

This guide covers deploying SpecRepo in various environments, from local development to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Security Considerations](#security-considerations)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

#### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB free space
- **OS**: Linux, macOS, or Windows with WSL2

#### Recommended for Production

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **OS**: Linux (Ubuntu 20.04+ or CentOS 8+)

### Software Dependencies

#### Required

- Docker 20.10+
- Docker Compose 2.0+
- Git
- Make (for using Makefile commands)

#### Optional

- nginx (for reverse proxy)
- SSL certificates (for HTTPS)
- Monitoring tools (Prometheus, Grafana)

### Installation

#### Docker Installation

**Ubuntu/Debian:**

```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
```

**CentOS/RHEL:**

```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
```

**macOS:**

```bash
# Install Docker Desktop
brew install --cask docker

# Or download from https://www.docker.com/products/docker-desktop
```

## Local Development

### Quick Start

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd specrepo
   ```

2. **Set up environment:**

   ```bash
   # Copy environment template
   cp scripts/env.example .env
   
   # Edit environment variables
   nano .env
   ```

3. **Start development environment:**

   ```bash
   # Using Makefile (recommended)
   make dev-up
   
   # Or manually
   docker-compose up -d
   ```

4. **Verify deployment:**

   ```bash
   # Check service status
   docker-compose ps
   
   # View logs
   docker-compose logs -f
   ```

5. **Access services:**
   - Frontend: <http://localhost:5173>
   - Backend API: <http://localhost:8000>
   - API Documentation: <http://localhost:8000/docs>
   - pgAdmin: <http://localhost:5050>
   - n8n: <http://localhost:5679>
   - WireMock: <http://localhost:8081>

### Development Workflow

#### Making Code Changes

- Frontend and backend support hot-reloading
- Changes are reflected immediately
- No need to restart containers for code changes

#### Database Changes

```bash
# Run migrations
make migrate

# Or manually
docker-compose exec backend alembic upgrade head
```

#### Adding Dependencies

**Backend (Python):**

```bash
# Add to pyproject.toml, then rebuild
docker-compose build backend
```

**Frontend (Node.js):**

```bash
# Add to package.json, then rebuild
docker-compose build frontend
```

#### Running Tests

```bash
# Run all tests
make test

# Run specific test suite
make test-backend
make test-frontend
```

#### Stopping Development Environment

```bash
# Stop services
make dev-down

# Or manually
docker-compose down

# Remove volumes (clean slate)
docker-compose down -v
```

## Production Deployment

### Preparation

1. **Server Setup:**

   ```bash
   # Update system
   sudo apt-get update && sudo apt-get upgrade -y
   
   # Install required packages
   sudo apt-get install -y curl git make
   
   # Install Docker (see prerequisites)
   ```

2. **Clone Repository:**

   ```bash
   git clone <repository-url>
   cd specrepo
   ```

3. **Configure Environment:**

   ```bash
   # Copy and edit production environment
   cp scripts/env.example .env
   
   # Generate secure secrets
   openssl rand -base64 32  # For JWT_SECRET
   openssl rand -base64 32  # For API_SECRET_KEY
   
   # Edit .env with production values
   nano .env
   ```

### Production Environment Variables

**Critical Variables to Update:**

```bash
# Database (use strong passwords)
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=specrepo_prod

# Security (generate secure values)
JWT_SECRET=<secure-jwt-secret>
API_SECRET_KEY=<secure-api-secret>

# n8n (update default keys)
N8N_API_KEY=<secure-n8n-api-key>
N8N_WEBHOOK_SECRET=<secure-webhook-secret>

# Application
LOG_LEVEL=INFO
NODE_ENV=production

# Monitoring (optional)
SENTRY_DSN=<your-sentry-dsn>
MONITORING_ENABLED=true
```

### Deployment Steps

1. **Build Production Images:**

   ```bash
   docker-compose -f docker-compose.prod.yml build
   ```

2. **Start Services:**

   ```bash
   # Start in detached mode
   docker-compose -f docker-compose.prod.yml up -d
   
   # Or using Makefile
   make prod-up
   ```

3. **Initialize Database:**

   ```bash
   # Run migrations
   docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
   
   # Create initial data (if needed)
   docker-compose -f docker-compose.prod.yml exec backend python scripts/init_data.py
   ```

4. **Verify Deployment:**

   ```bash
   # Check service status
   docker-compose -f docker-compose.prod.yml ps
   
   # Check health endpoints
   curl http://localhost:8000/health
   curl http://localhost:8080/health
   
   # View logs
   docker-compose -f docker-compose.prod.yml logs -f
   ```

### Reverse Proxy Setup (nginx)

**Install nginx:**

```bash
sudo apt-get install nginx
```

**Configure nginx:**

```nginx
# /etc/nginx/sites-available/specrepo
server {
    listen 80;
    server_name your-domain.com;
    
    # Frontend
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # n8n (optional, for webhook access)
    location /n8n/ {
        proxy_pass http://localhost:5679/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable site:**

```bash
sudo ln -s /etc/nginx/sites-available/specrepo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL/TLS Setup

**Using Let's Encrypt:**

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Cloud Deployment

### AWS Deployment

#### Using EC2

1. **Launch EC2 Instance:**
   - Instance type: t3.medium or larger
   - OS: Ubuntu 20.04 LTS
   - Security groups: Allow ports 22, 80, 443

2. **Setup:**

   ```bash
   # Connect to instance
   ssh -i your-key.pem ubuntu@your-instance-ip
   
   # Follow production deployment steps
   ```

#### Using ECS (Elastic Container Service)

1. **Create Task Definition:**

   ```json
   {
     "family": "specrepo",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "1024",
     "memory": "2048",
     "containerDefinitions": [
       {
         "name": "backend",
         "image": "your-registry/specrepo-backend:latest",
         "portMappings": [{"containerPort": 8000}],
         "environment": [
           {"name": "DATABASE_URL", "value": "postgresql://..."}
         ]
       }
     ]
   }
   ```

2. **Create Service:**

   ```bash
   aws ecs create-service \
     --cluster your-cluster \
     --service-name specrepo \
     --task-definition specrepo \
     --desired-count 2
   ```

### Google Cloud Platform

#### Using Compute Engine

1. **Create VM Instance:**

   ```bash
   gcloud compute instances create specrepo-vm \
     --image-family=ubuntu-2004-lts \
     --image-project=ubuntu-os-cloud \
     --machine-type=e2-medium \
     --tags=http-server,https-server
   ```

2. **Setup firewall:**

   ```bash
   gcloud compute firewall-rules create allow-http \
     --allow tcp:80,tcp:443 \
     --source-ranges 0.0.0.0/0 \
     --target-tags http-server
   ```

#### Using Cloud Run

1. **Build and push images:**

   ```bash
   # Build for Cloud Run
   docker build -t gcr.io/your-project/specrepo-backend ./backend
   docker push gcr.io/your-project/specrepo-backend
   ```

2. **Deploy:**

   ```bash
   gcloud run deploy specrepo-backend \
     --image gcr.io/your-project/specrepo-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### Digital Ocean

#### Using Droplets

1. **Create Droplet:**
   - OS: Ubuntu 20.04
   - Size: 2GB RAM minimum
   - Add SSH key

2. **Setup:**

   ```bash
   # Connect and follow production deployment steps
   ssh root@your-droplet-ip
   ```

#### Using App Platform

1. **Create app spec:**

   ```yaml
   name: specrepo
   services:
   - name: backend
     source_dir: /backend
     github:
       repo: your-username/specrepo
       branch: main
     run_command: uvicorn main:app --host 0.0.0.0 --port 8080
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
   ```

## Environment Configuration

### Development vs Production

| Setting | Development | Production |
|---------|-------------|------------|
| LOG_LEVEL | DEBUG | INFO |
| RATE_LIMIT_MAX_ATTEMPTS | 1000 | 100 |
| Database | Local PostgreSQL | Managed database |
| SSL | Not required | Required |
| Monitoring | Optional | Required |
| Backups | Not required | Required |

### Environment Variables Reference

See `scripts/env.example` for complete list of variables.

**Critical Production Variables:**

- `POSTGRES_PASSWORD`: Strong database password
- `JWT_SECRET`: Secure JWT signing key
- `API_SECRET_KEY`: API encryption key
- `N8N_API_KEY`: n8n API access key
- `N8N_WEBHOOK_SECRET`: Webhook security secret

## Security Considerations

### Container Security

1. **Non-root users:** All containers run as non-root users
2. **Read-only filesystems:** Where possible
3. **Resource limits:** Prevent resource exhaustion
4. **Security scanning:** Regular image vulnerability scans

### Network Security

1. **Firewall configuration:**

   ```bash
   # Allow only necessary ports
   sudo ufw allow 22    # SSH
   sudo ufw allow 80    # HTTP
   sudo ufw allow 443   # HTTPS
   sudo ufw enable
   ```

2. **Internal networking:** Services communicate via internal network

### Data Security

1. **Encryption at rest:** Database encryption
2. **Encryption in transit:** HTTPS/TLS
3. **Secret management:** Environment variables, not hardcoded
4. **Regular backups:** Automated and tested

### Access Control

1. **SSH key authentication:** Disable password auth
2. **Principle of least privilege:** Minimal permissions
3. **Regular updates:** Keep system and dependencies updated

## Monitoring and Maintenance

### Health Monitoring

**Built-in Health Checks:**

- Backend: `GET /health`
- Frontend: `GET /health`
- Database: `pg_isready`
- n8n: `GET /healthz`

**External Monitoring:**

```bash
# Simple uptime monitoring
curl -f http://your-domain.com/health || echo "Service down"

# Using monitoring services
# - UptimeRobot
# - Pingdom
# - DataDog
```

### Log Management

**View logs:**

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# With timestamps
docker-compose -f docker-compose.prod.yml logs -f -t
```

**Log rotation:**

```bash
# Configure Docker daemon
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### Backup Strategy

**Database Backup:**

```bash
# Create backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$DATE.sql

# Upload to S3 (optional)
aws s3 cp backup_$DATE.sql s3://your-backup-bucket/
```

**Automated Backups:**

```bash
# Add to crontab
0 2 * * * /path/to/backup-script.sh
```

### Updates and Maintenance

**Regular Updates:**

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Clean up old images
docker image prune -f
```

**Maintenance Windows:**

1. Schedule during low-traffic periods
2. Notify users in advance
3. Have rollback plan ready
4. Monitor after updates

## Troubleshooting

### Common Issues

#### Services Won't Start

**Check service status:**

```bash
docker-compose -f docker-compose.prod.yml ps
```

**View logs:**

```bash
docker-compose -f docker-compose.prod.yml logs [service-name]
```

**Common causes:**

- Port conflicts
- Missing environment variables
- Insufficient resources
- Network connectivity issues

#### Database Connection Issues

**Check database health:**

```bash
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_isready -U $POSTGRES_USER -d $POSTGRES_DB
```

**Connect to database:**

```bash
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U $POSTGRES_USER -d $POSTGRES_DB
```

#### Performance Issues

**Monitor resource usage:**

```bash
# Container stats
docker stats

# System resources
htop
df -h
free -h
```

**Common solutions:**

- Increase server resources
- Optimize database queries
- Add caching layer
- Scale horizontally

#### SSL/TLS Issues

**Check certificate:**

```bash
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

**Renew Let's Encrypt:**

```bash
sudo certbot renew --dry-run
```

### Getting Help

1. **Check logs first:** Most issues are logged
2. **Review documentation:** This guide and Docker Compose guide
3. **Search issues:** GitHub repository issues
4. **Create issue:** If problem persists

### Emergency Procedures

#### Service Recovery

1. **Stop all services:**

   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Check system resources:**

   ```bash
   df -h
   free -h
   docker system df
   ```

3. **Clean up if needed:**

   ```bash
   docker system prune -f
   ```

4. **Restart services:**

   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

#### Data Recovery

1. **Stop services:**

   ```bash
   docker-compose -f docker-compose.prod.yml stop
   ```

2. **Restore from backup:**

   ```bash
   docker-compose -f docker-compose.prod.yml exec -T postgres \
     psql -U $POSTGRES_USER -d $POSTGRES_DB < backup_file.sql
   ```

3. **Restart services:**

   ```bash
   docker-compose -f docker-compose.prod.yml start
   ```

## Best Practices Summary

1. **Security First:** Use strong passwords, enable HTTPS, keep updated
2. **Monitor Everything:** Health checks, logs, resources, uptime
3. **Backup Regularly:** Automated, tested, and versioned backups
4. **Document Changes:** Keep deployment documentation updated
5. **Test Deployments:** Use staging environment before production
6. **Plan for Scale:** Design for growth from the beginning
7. **Automate Operations:** Use scripts and CI/CD for consistency
8. **Have Rollback Plan:** Always be able to revert changes quickly
