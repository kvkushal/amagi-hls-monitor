# StreamProbeX Deployment Guide

Complete guide for deploying StreamProbeX OTT monitoring system to production.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 2 GB RAM minimum, 4 GB recommended
- 10 GB disk space
- FFmpeg (included in Docker image)
- Network access to HLS manifests

## Quick Deploy (Docker Compose)

### Step 1: Clone and Configure

```bash
# Navigate to project
cd c:\Users\Kush\Desktop\amagi-hls-monitor

# Copy environment file
copy .env.example .env

# Edit .env with your settings (optional)
notepad .env
```

### Step 2: Build and Start

```bash
# Build and start all services
docker-compose up --build -d

# Check logs
docker-compose logs -f

# Verify services are running
docker-compose ps
```

### Step 3: Access Application

- **Frontend**: http://localhost
- **API Documentation**: http://localhost/api/docs
- **Health Check**: http://localhost/health
- **WebSocket Test**: ws://localhost/ws/streams/{stream_id}

### Step 4: Add Test Streams

```bash
# Using cURL (Git Bash on Windows)
curl -X POST http://localhost/api/streams \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"test_stream\",\"name\":\"Big Buck Bunny\",\"manifest_url\":\"https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8\",\"enabled\":true,\"tags\":[\"test\"]}"

# Using PowerShell
Invoke-RestMethod -Uri "http://localhost/api/streams" -Method Post -Headers @{"Content-Type"="application/json"} -Body '{"id":"test_stream","name":"Big Buck Bunny","manifest_url":"https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8","enabled":true,"tags":["test"]}'
```

## Production Deployment

### Option 1: Cloud VPS (DigitalOcean, Linode, Hetzner)

```bash
# 1. SSH into server
ssh user@your-server-ip

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt-get install docker-compose-plugin

# 3. Clone repository
git clone <your-repo-url>
cd amagi-hls-monitor

# 4. Configure environment
cp .env.example .env
nano .env
# Set DEBUG=False
# Configure CORS_ORIGINS with your domain

# 5. Start services
docker compose up -d

# 6. Configure nginx for SSL
apt-get install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com

# 7. Update nginx config to use SSL
nano nginx/nginx.conf
# Add SSL server block

# 8. Restart services
docker compose restart nginx
```

### Option 2: AWS ECS/Fargate

**1. Build and Push Images to ECR:**

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin {account}.dkr.ecr.us-east-1.amazonaws.com

# Build images
docker build -t streamprobe-api ./backend
docker build -t streamprobe-frontend ./frontend

# Tag images
docker tag streamprobe-api:latest {account}.dkr.ecr.us-east-1.amazonaws.com/streamprobe-api:latest
docker tag streamprobe-frontend:latest {account}.dkr.ecr.us-east-1.amazonaws.com/streamprobe-frontend:latest

# Push images
docker push {account}.dkr.ecr.us-east-1.amazonaws.com/streamprobe-api:latest
docker push {account}.dkr.ecr.us-east-1.amazonaws.com/streamprobe-frontend:latest
```

**2. Create ECS Task Definition:**

```json
{
  "family": "streamprobe",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "{account}.dkr.ecr.us-east-1.amazonaws.com/streamprobe-api:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "DEBUG", "value": "False"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/streamprobe",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      }
    },
    {
      "name": "frontend",
      "image": "{account}.dkr.ecr.us-east-1.amazonaws.com/streamprobe-frontend:latest",
      "portMappings": [{"containerPort": 80}]
    }
  ]
}
```

**3. Create ECS Service with ALB**

### Option 3: Google Cloud Run

```bash
# Build and submit to Cloud Build
gcloud builds submit --tag gcr.io/{project-id}/streamprobe-api ./backend
gcloud builds submit --tag gcr.io/{project-id}/streamprobe-frontend ./frontend

# Deploy API
gcloud run deploy streamprobe-api \
  --image gcr.io/{project-id}/streamprobe-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Deploy Frontend
gcloud run deploy streamprobe-frontend \
  --image gcr.io/{project-id}/streamprobe-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Configure Cloud Run to talk to each other
# Use service URLs in frontend environment
```

### Option 4: Azure Container Instances

```bash
# Create resource group
az group create --name streamprobe-rg --location eastus

# Create container group
az container create \
  --resource-group streamprobe-rg \
  --name streamprobe \
  --image {registry}.azurecr.io/streamprobe-api:latest \
  --dns-name-label streamprobe-api \
  --ports 8000 80

# Enable HTTPS with Azure Front Door or Application Gateway
```

## Configuration

### Environment Variables

Key production settings in `.env`:

```bash
# Set to False for production
DEBUG=False

# Allow your domain
CORS_ORIGINS=["https://yourdomain.com"]

# Adjust based on load
MANIFEST_POLL_INTERVAL=10
MAX_CONCURRENT_DOWNLOADS=5

# Lower for resource constraints
SPRITE_SEGMENT_COUNT=50

# Storage paths
LOGS_DIR=/app/logs
DATA_DIR=/app/data

# Optional: S3 storage
S3_ENABLED=True
S3_BUCKET=streamprobe-data
S3_REGION=us-east-1
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx
```

### Scaling Considerations

**Horizontal Scaling:**
- Run multiple API containers behind load balancer
- Share storage via NFS, EFS, or S3
- Use Redis for shared state if needed

**Resource Allocation:**
- CPU: 1-2 cores per 5 concurrent streams
- Memory: 512 MB base + 100 MB per stream
- Storage: 1 GB per stream per day (thumbnails + logs)

**Database (Optional):**
- Currently using in-memory storage
- For production, add PostgreSQL or MongoDB
- Modify `backend/app/api/streams.py` to use DB

## Monitoring

### Health Checks

```bash
# Docker Compose includes health checks
docker-compose ps

# Manual health check
curl http://localhost/health
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f api
docker-compose logs -f frontend

# Application logs (inside container)
docker exec streamprobe-api ls /app/logs
```

### Metrics

Access Prometheus metrics (if added):
- `/metrics` endpoint on API

## Security

### Authentication (Add to nginx)

```nginx
# In nginx config, add basic auth
location / {
    auth_basic "StreamProbeX";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://frontend_app;
}

# Generate password file
htpasswd -c /etc/nginx/.htpasswd admin
```

### SSL/TLS

```bash
# Let's Encrypt (automatic renewal)
certbot --nginx -d yourdomain.com

# Or use custom certificates
# Update nginx config with ssl_certificate paths
```

### Firewall Rules

```bash
# Allow only HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## Backup and Recovery

### Backup

```bash
# Backup logs and data
tar -czf backup-$(date +%Y%m%d).tar.gz logs/ data/

# Backup to S3
aws s3 cp backup-$(date +%Y%m%d).tar.gz s3://your-bucket/backups/
```

### Recovery

```bash
# Restore from backup
tar -xzf backup-20231129.tar.gz

# Restart services
docker-compose restart
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker logs
docker-compose logs api
docker-compose logs frontend

# Verify ports not in use
netstat -an | findstr "8000 80"

# Rebuild completely
docker-compose down -v
docker-compose up --build
```

### WebSocket Not Connecting

- Verify nginx WebSocket upgrade headers
- Check firewall allows WebSocket
- Test with `wscat`: `wscat -c ws://localhost/ws/streams/test_stream`

### High Memory Usage

- Reduce `SPRITE_SEGMENT_COUNT`
- Lower `MAX_CONCURRENT_DOWNLOADS`
- Add memory limits in docker-compose:
  ```yaml
  api:
    deploy:
      resources:
        limits:
          memory: 1G
  ```

### Thumbnails Not Generating

- Verify FFmpeg in container: `docker exec streamprobe-api ffmpeg -version`
- Check segment downloads successful
- Review logs: `docker-compose logs api | grep thumbnail`

## Maintenance

### Log Rotation

Automatic rotation configured:
- Daily rotation at midnight UTC
- Compression after 7 days
- Deletion after 30 days

Manual rotation:
```bash
docker exec streamprobe-api python -c "from app.services.logger_service import log_service; import asyncio; asyncio.run(log_service.rotate_logs())"
```

### Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up --build -d

# Check logs for issues
docker-compose logs -f
```

## Performance Optimization

1. **Enable Gzip**: Already configured in nginx
2. **CDN**: Use CloudFlare or similar for static assets
3. **Database**: Move to PostgreSQL for large deployments
4. **Redis**: Add for caching sprite maps and metrics
5. **Load Balancer**: Nginx or HAProxy for multi-instance

## Support

- Check logs first: `docker-compose logs`
- Health endpoint: `http://localhost/health`
- API docs: `http://localhost/api/docs`
- GitHub Issues: [your-repo/issues]

---

**Successfully deployed StreamProbeX!** 🚀

Access your monitoring dashboard at http://localhost (or your configured domain).
