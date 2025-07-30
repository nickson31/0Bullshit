# 🚀 Quick Start Guide - 0BullshitIntelligence

Get the 0BullshitIntelligence microservice up and running in minutes.

## 📋 Prerequisites

- Python 3.11+
- Git
- Docker (optional but recommended)
- Supabase account
- Google Gemini API key

## 🔧 Environment Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd 0BullshitIntelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required Environment Variables:**
```env
# Database (Create new Supabase project)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here

# AI Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# Security
JWT_SECRET_KEY=your-secure-jwt-secret
SERVICE_API_KEY=your-service-api-key
```

### 3. Database Setup

The microservice needs its own Supabase project for independence:

1. **Create new Supabase project** at [supabase.com](https://supabase.com)
2. **Copy connection details** to your `.env` file
3. **Run database migrations** (if available):
   ```bash
   python scripts/setup_database.py
   ```

## 🏃‍♂️ Running the Service

### Option 1: Direct Python

```bash
# Development mode
python main.py

# Production mode
ENVIRONMENT=production python main.py
```

### Option 2: Docker (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in background
docker-compose up -d

# Include testing interface
docker-compose --profile testing up
```

### Option 3: Docker Development

```bash
# Development mode with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## 🧪 Testing the Service

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "success": true,
  "message": "Service is healthy",
  "data": {
    "status": "operational",
    "components": {
      "database": "healthy",
      "ai_systems": "healthy",
      "search_engines": "healthy"
    }
  }
}
```

### 2. Service Information

```bash
curl http://localhost:8000/
```

### 3. Chat API Test

```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola, necesito ayuda con mi startup",
    "user_id": "test-user-123"
  }'
```

### 4. Testing Interface

If enabled, access the web testing interface at:
http://localhost:8000/test-interface

## 🔗 API Endpoints

### Core Endpoints
- `GET /` - Service information
- `GET /health` - Health check
- `GET /status` - Detailed status
- `GET /metrics` - Service metrics (if enabled)

### Chat API
- `POST /api/v1/chat/message` - Send chat message
- `GET /api/v1/chat/conversations` - List conversations
- `WS /ws/chat/{conversation_id}` - WebSocket chat

### Search API
- `POST /api/v1/search/investors` - Search investors
- `POST /api/v1/search/companies` - Search companies
- `GET /api/v1/search/results/{search_id}` - Get search results

### Webhooks
- `POST /api/v1/webhooks/sync` - Data synchronization
- `POST /api/v1/webhooks/user-update` - User data updates

## 🔧 Configuration Options

### AI Systems
```env
# Language detection
DEFAULT_LANGUAGE=spanish
SUPPORTED_LANGUAGES=spanish,english

# Anti-spam
SPAM_THRESHOLD=70

# Upselling
UPSELL_MAX_ATTEMPTS_PER_DAY=3
```

### Search Engines
```env
# Investor search
MIN_ANGEL_SCORE=40.0
MIN_EMPLOYEE_SCORE=5.9
DEFAULT_SEARCH_LIMIT=15

# Company search
COMPANY_SEARCH_LIMIT=10
```

### Performance
```env
# Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Caching
CACHE_TTL_DEFAULT=3600
CACHE_TTL_SEARCH_RESULTS=1800
```

## 🔄 Database Synchronization

To sync with main repository database:

```env
# Enable sync
SYNC_ENABLED=true

# Main repository database
SYNC_SUPABASE_URL=https://main-project.supabase.co
SYNC_SUPABASE_KEY=main-anon-key-here
```

## 📊 Monitoring

### Logs
```bash
# View logs
tail -f app.log

# Docker logs
docker-compose logs -f intelligence
```

### Metrics
Access metrics at: http://localhost:8000/metrics

### Health Monitoring
```bash
# Continuous health check
watch -n 30 'curl -s http://localhost:8000/health | jq'
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```
   Check SUPABASE_URL and SUPABASE_KEY in .env
   Verify Supabase project is active
   ```

2. **Gemini API Error**
   ```
   Verify GEMINI_API_KEY is correct
   Check API quota and billing
   ```

3. **Port Already in Use**
   ```bash
   # Change port in .env
   PORT=8001
   
   # Or kill existing process
   lsof -ti:8000 | xargs kill -9
   ```

4. **Import Errors**
   ```bash
   # Reinstall dependencies
   pip install --force-reinstall -r requirements.txt
   ```

### Debug Mode

Enable debug mode for detailed logging:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## 🚀 Production Deployment

### Environment Variables
```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### Security
- Use strong JWT secrets
- Configure proper CORS origins
- Set up SSL/TLS termination
- Use environment-specific API keys

### Scaling
- Use multiple workers: `WORKERS=4`
- Set up load balancer
- Configure Redis for session storage
- Monitor resource usage

## 📚 Next Steps

1. **Integration**: Connect with main 0Bullshit repository
2. **Testing**: Use the testing interface for team collaboration
3. **Monitoring**: Set up metrics and alerting
4. **Scaling**: Configure for production workloads

## 🆘 Support

- **Documentation**: Check `docs/` directory
- **API Docs**: http://localhost:8000/docs (debug mode)
- **Issues**: Create GitHub issues for problems
- **Testing**: Use `/test-interface` for interactive testing

---

**🎉 Congratulations! Your 0BullshitIntelligence microservice is now running!**