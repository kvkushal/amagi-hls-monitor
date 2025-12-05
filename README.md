# StreamProbeX

**Production-grade OTT Stream Monitoring System** - A complete Elecard Boro-style HLS/MPEG-DASH stream monitoring platform.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 Features

### Complete Stream Monitoring
- ✅ **Real-time HLS manifest monitoring** with automatic segment detection
- ✅ **Segment-level metrics** tracking (bitrate, TTFB, download speed, duration, size)
- ✅ **Timeline thumbnail preview** with YouTube-style hover functionality
- ✅ **Sprite sheet generation** for efficient thumbnail delivery
- ✅ **Loudness monitoring** (LUFS momentary/short-term with RMS fallback)
- ✅ **Ad insertion detection** (HLS DATERANGE, CUE-OUT/IN, bandwidth reservation)
- ✅ **Error detection** with gray placeholder thumbnails
- ✅ **Daily log rotation** with automatic compression and cleanup
- ✅ **WebSocket live updates** for real-time monitoring
- ✅ **Multi-stream dashboard** with KPI badges and alarms

### UI Features (Matching Elecard Boro)
- ⏱️ **Time range controls**: 3min, 30min, 3h, 8h, 2d, 4d
- ▶️ **Navigation controls**: <<, <, pause, >, >>, 00:00, TabSync©
- 🖼️ **Thumbnail density**: 100%, 75%, 50%, 25%
- 📊 **Loudness charts** with Recharts
- 📋 **Comprehensive metrics table** with all segment data
- 📝 **Event log viewer** with tabs (Events, Alarms, Records)
- 🚨 **KPI badges** (Task, BS, MLT.15, MLS.15, Alarms, KPI.15)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- FFmpeg (for local development)
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Run with Docker (Recommended)

```bash
# Clone the repository
cd amagi-hls-monitor

# Copy environment file
cp .env.example .env

# Build and start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost
# API Docs: http://localhost/api/docs
# Health Check: http://localhost/health
```

### Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 📖 Usage

### Adding a Stream

**Via UI:**
1. Access the dashboard at `http://localhost`
2. Click "Add Stream"
3. Enter stream name and manifest URL
4. Configure tags and settings
5. Click "Start Monitoring"

**Via API:**
```bash
curl -X POST http://localhost/api/streams \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my_stream",
    "name": "My HLS Stream",
    "manifest_url": "https://example.com/playlist.m3u8",
    "enabled": true,
    "tags": ["production", "1080p"]
  }'
```

### Using Sample Streams

The system includes test HLS streams. Load them via:

```bash
# Using the sample streams file
curl -X POST http://localhost/api/streams \
  -H "Content-Type: application/json" \
  -d @tests/sample_streams.json
```

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │  React + TypeScript
│   (Port 80)     │  TailwindCSS + Zustand
└────────┬────────┘
         │
    ┌────▼────┐
    │  Nginx  │  Reverse Proxy
    │ (Port   │  WebSocket Support
    │  80)    │
    └────┬────┘
         │
    ┌────▼───────┐         ┌──────────────┐
    │  Backend   │◄────────┤  WebSocket   │
    │  FastAPI   │         │  Manager     │
    │ (Port 8000)│         └──────────────┘
    └────┬───────┘
         │
    ┌────▼────────────────────────────┐
    │  Stream Monitor                 │
    │  ├─ HLS Fetcher                │
    │  ├─ Segment Downloader          │
    │  ├─ Metrics Calculator          │
    │  ├─ Thumbnail Generator (FFmpeg)│
    │  ├─ Sprite Compositor (Pillow)  │
    │  ├─ Loudness Analyzer (FFmpeg)  │
    │  ├─ Ad Detector                 │
    │  └─ Logger Service              │
    └─────────────────────────────────┘
         │
    ┌────▼────┐
    │ Storage │
    │ ├─ Logs │
    │ ├─ Data │
    │ └─ S3   │
    └─────────┘
```

## 📁 Project Structure

```
amagi-hls-monitor/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── services/     # Core services
│   │   ├── models.py     # Pydantic models
│   │   ├── config.py     # Configuration
│   │   └── main.py       # Application entry
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── store/        # Zustand state
│   │   ├── services/     # API client
│   │   └── hooks/        # React hooks
│   ├── package.json
│   └── Dockerfile
├── nginx/                # Nginx configuration
│   └── nginx.conf
├── logs/                 # Application logs
├── data/                 # Runtime data
│   ├── thumbnails/
│   ├── sprites/
│   └── segments/
├── tests/                # Test data and scripts
├── docker-compose.yml    # Multi-service orchestration
└── README.md            # This file
```

## 🔧 Configuration

All configuration is via environment variables. See `.env.example` for full options.

**Key Settings:**
- `MANIFEST_POLL_INTERVAL`: Seconds between manifest checks (default: 5)
- `SPRITE_SEGMENT_COUNT`: Segments per sprite (default: 100)
- `LOG_COMPRESS_DAYS`: Days before log compression (default: 7)
- `LOG_DELETE_DAYS`: Days before log deletion (default: 30)
- `THUMBNAIL_WIDTH/HEIGHT`: Thumbnail dimensions (default: 160x90)

## 📊 API Documentation

Interactive API documentation available at:
- **Swagger UI**: `http://localhost/api/docs`
- **ReDoc**: `http://localhost/api/redoc`

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/streams` | GET | List all streams |
| `/api/streams/{id}` | GET | Get stream details |
| `/api/streams` | POST | Add new stream |
| `/api/streams/{id}` | DELETE | Remove stream |
| `/api/streams/{id}/metrics` | GET | Get metrics (with time range) |
| `/api/streams/{id}/sprites` | GET | Get sprite maps |
| `/api/streams/{id}/loudness` | GET | Get loudness data |
| `/api/streams/{id}/events` | GET | Get event log |
| `/ws/streams/{id}` | WS | WebSocket subscription |
| `/health` | GET | Health check |

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
docker-compose up -d
python tests/integration_test.py
```

## 📝 Logging

Logs are stored in `/logs/` directory:
- Format: JSON lines (one event per line)
- Rotation: Daily at midnight UTC
- Compression: After 7 days (gzip)
- Retention: 30 days
- Query logs via `/api/streams/{id}/events` endpoint

## 🌐 Deployment

### Production Deployment

**AWS ECS/Fargate:**
```bash
# Build and push images
docker build -t streamprobe-api ./backend
docker build -t streamprobe-frontend ./frontend

# Push to ECR
docker tag streamprobe-api:latest {account}.dkr.ecr.{region}.amazonaws.com/streamprobe-api:latest
docker push {account}.dkr.ecr.{region}.amazonaws.com/streamprobe-api:latest

# Deploy via ECS task definition
```

**Google Cloud Run:**
```bash
gcloud builds submit --tag gcr.io/{project}/streamprobe-api ./backend
gcloud run deploy streamprobe-api --image gcr.io/{project}/streamprobe-api
```

**Traditional VPS:**
```bash
# Clone repo
git clone <repo-url>
cd amagi-hls-monitor

# Setup environment
cp .env.example .env
# Edit .env with production values

# Run with Docker Compose
docker-compose up -d

# Setup SSL with Let's Encrypt
certbot --nginx -d yourdomain.com
```

## 🔐 Security

- No authentication included by default
- Add nginx basic auth or OAuth2 proxy for production
- Use HTTPS with valid SSL certificates
- Configure CORS origins appropriately
- Implement rate limiting at nginx level
- Secure WebSocket connections

## 🛠️ Development

### Adding New Features

1. **Backend Service**: Add to `backend/app/services/`
2. **API Endpoint**: Add to `backend/app/api/`
3. **Frontend Component**: Add to `frontend/src/components/`
4. **State**: Update Zustand store in `frontend/src/store/`

### Code Quality

- Backend: Follow PEP 8, use type hints
- Frontend: Use TypeScript strict mode, ESLint
- Write tests for critical functionality
- Document complex logic

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Inspired by Elecard Boro OTT monitoring platform
- Uses FFmpeg for video processing
- Built with FastAPI, React, and modern web technologies

## 🐛 Troubleshooting

**Issue: Thumbnails not generating**
- Ensure FFmpeg is installed in container
- Check segment download is successful
- Review logs in `/logs/`

**Issue: WebSocket not connecting**
- Verify nginx WebSocket proxy configuration
- Check browser console for connection errors
- Ensure firewall allows WebSocket traffic

**Issue: High memory usage**
- Reduce `SPRITE_SEGMENT_COUNT`
- Lower `MAX_CONCURRENT_DOWNLOADS`
- Enable log compression earlier

## 📞 Support

For issues and questions:
- GitHub Issues: [Link to repo]
- Documentation: See `/docs` directory
- API Docs: http://localhost/api/docs

---

**Built with ❤️ for OTT stream monitoring**
