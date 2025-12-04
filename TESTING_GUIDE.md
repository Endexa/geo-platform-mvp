# GEO Platform MVP - Complete Testing Guide

This guide will walk you through setting up, running, and testing all modules and functionalities of the GEO Platform.

## 📋 Table of Contents

1. [Prerequisites & Setup](#prerequisites--setup)
2. [Starting the Application](#starting-the-application)
3. [Module 1: Dashboard Intelligence](#module-1-dashboard-intelligence)
4. [Module 2: Analysis Engine](#module-2-analysis-engine)
5. [Module 3: Optimization Engine](#module-3-optimization-engine)
6. [Module 4: Brand Voice](#module-4-brand-voice)
7. [API Testing with cURL](#api-testing-with-curl)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites & Setup

### Required Software

1. **Docker & Docker Compose** (Recommended Method)
   ```bash
   # Verify installation
   docker --version
   docker-compose --version
   ```

2. **OR Manual Installation:**
   - Python 3.11+
   - Node.js 18+
   - PostgreSQL 15+ with pgvector
   - Redis 7+

### Environment Configuration

#### 1. Backend Configuration

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` with your credentials:

```env
# Supabase (Sign up at https://supabase.com)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-key-here

# OpenAI (Get from https://platform.openai.com)
OPENAI_API_KEY=sk-your-api-key-here

# Database (for Docker, use these defaults)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/geo_platform

# Redis
REDIS_URL=redis://redis:6379/0

# Secret Key (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here
```

#### 2. Frontend Configuration

```bash
cd frontend
cp .env.example .env
```

Edit `frontend/.env`:

```env
NUXT_PUBLIC_API_URL=http://localhost:8000
NUXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NUXT_PUBLIC_SUPABASE_KEY=your-anon-key-here
```

---

## Starting the Application

### Option 1: Docker Compose (Recommended)

```bash
# From project root
docker-compose up --build
```

This will start:
- **PostgreSQL** (with pgvector) on port `5432`
- **Redis** on port `6379`
- **Backend API** on port `8000`
- **Celery Worker** for background tasks
- **Frontend** on port `3000`

**Access Points:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/v1/docs

### Option 2: Manual Setup

#### Terminal 1: Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Terminal 2: Celery Worker

```bash
cd backend
source venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info
```

#### Terminal 3: Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Module 1: Dashboard Intelligence

### Accessing the Dashboard

1. **Navigate to:** http://localhost:3000
2. **You'll see:**
   - Average GEO Score card
   - Total Analyses count
   - System status indicator
   - Recent audits table (empty initially)

### Testing the Dashboard

#### Step 1: Check Initial State

The dashboard should show:
- "No analyses yet" message
- "Analyze Now" button

#### Step 2: After Running Analyses

After completing some analyses, the dashboard will display:
- Updated average GEO score with color coding:
  - **Green** (80-100): Excellent
  - **Yellow** (50-79): Good
  - **Red** (0-49): Needs improvement
- List of recent analyses with scores and timestamps

### API Testing

```bash
# Get dashboard stats
curl http://localhost:8000/api/v1/dashboard/stats

# Expected response:
{
  "total_analyses": 5,
  "avg_geo_score": 72.5,
  "trend_data": [...],
  "recent_audits": [...]
}
```

---

## Module 2: Analysis Engine

### Accessing the Analyzer

1. **Navigate to:** http://localhost:3000/analyze
2. **You'll see:**
   - URL input field
   - Keywords input field
   - "Analyze Now" button

### Testing Analysis Workflow

#### Test Case 1: Basic Analysis

1. **Enter URL:** `https://example.com`
2. **Enter Keywords:** `web, design, development`
3. **Click:** "Analyze Now"

**Expected Behavior:**
1. Button shows "Analyzing..." with spinner
2. Progress stepper shows 4 stages:
   - ✓ Crawling Site...
   - ✓ Simulating AI Search...
   - ✓ Calculating Vectors...
   - ✓ Done!
3. Results display 4 score cards:
   - **GEO Score** (0-100)
   - **Visibility** (0-100)
   - **Readability** (0-100)
   - **Authority** (0-100)

#### Test Case 2: Analysis with Multiple Keywords

1. **Enter URL:** `https://wikipedia.org`
2. **Enter Keywords:** `knowledge, encyclopedia, information, research`
3. **Click:** "Analyze Now"

**Expected:**
- Higher visibility score due to keyword matching
- Higher authority score (Wikipedia is a high-authority domain)

#### Test Case 3: Educational Domain (.edu)

1. **Enter URL:** `https://mit.edu`
2. **Click:** "Analyze Now"

**Expected:**
- Authority score should be ~85 (educational domains get bonus)

### API Testing

```bash
# Step 1: Start analysis
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "keywords": ["test", "demo"]
  }'

# Response: {"analysis_id": "uuid-here", "status": "pending"}

# Step 2: Poll for results (replace UUID)
curl http://localhost:8000/api/v1/analysis/{analysis-id}

# Response when complete:
{
  "id": "uuid",
  "status": "completed",
  "geo_score": 75,
  "visibility_score": 80,
  "readability_score": 70,
  "authority_score": 75
}
```

### Score Calculation Logic

- **Visibility Score:** (Keywords found in headings / Total keywords) × 100
- **Readability Score:** Flesch Reading Ease normalized to 0-100
- **Authority Score:** Mock calculation based on domain (for MVP)
- **GEO Score:** (Visibility × 0.4) + (Readability × 0.3) + (Authority × 0.3)

---

## Module 3: Optimization Engine

### Accessing Recommendations

**Method 1: From Analysis Results**
1. Complete an analysis
2. Click "Generate Recommendations" button

**Method 2: Direct Navigation**
- Navigate to: http://localhost:3000/optimization

### Testing Recommendation Generation

#### Test Case 1: Generate Recommendations

1. **Complete an analysis first** (see Module 2)
2. **Click:** "Generate Recommendations"
3. **Backend Process:**
   - Uses GPT-4o-mini to analyze the results
   - Identifies 3 optimization opportunities
   - Categorizes by: content, technical, metadata
   - Assigns severity: high, medium, low
   - Provides impact scores: +10pts, +15pts, +20pts

**Expected Output:**
```json
[
  {
    "category": "content",
    "severity": "high",
    "issue": "Content optimization needed",
    "action_plan": "Improve content structure...",
    "impact_score": "+15pts"
  },
  {
    "category": "technical",
    "severity": "medium",
    "issue": "Schema markup missing",
    "action_plan": "Implement Schema.org...",
    "impact_score": "+12pts"
  }
]
```

#### Test Case 2: Optimize Content

1. **Click** on a recommendation's "Optimize" button
2. **Expected:**
   - "Writing..." animation appears
   - AI generates optimized content
   - Content streams in (ChatGPT style)
   - Final optimized text displayed

### API Testing

```bash
# Generate recommendations (replace analysis-id)
curl -X POST http://localhost:8000/api/v1/optimization/generate \
  -H "Content-Type: application/json" \
  -d '{"analysis_id": "your-analysis-id"}'

# Get recommendations
curl http://localhost:8000/api/v1/analysis/{analysis-id}/recommendations

# Optimize specific recommendation
curl -X POST http://localhost:8000/api/v1/optimization/optimize-content \
  -H "Content-Type: application/json" \
  -d '{"recommendation_id": "your-recommendation-id"}'
```

### Jira Integration Testing

```bash
# Create Jira ticket from recommendation
curl -X POST http://localhost:8000/api/v1/integrations/jira/create-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_id": "your-recommendation-id",
    "project_key": "GEO"
  }'

# Response:
{
  "message": "Jira ticket created",
  "ticket_id": "GEO-123",
  "recommendation_id": "uuid"
}
```

**Note:** For MVP, if Jira credentials are not configured, it returns a mock ticket ID.

---

## Module 4: Brand Voice

### Accessing Brand Voice

1. **Navigate to:** http://localhost:3000/brand-voice
2. **You'll see:**
   - Split-screen interface
   - Left: "Golden Knowledge Base" upload
   - Right: "Test Your Content" text area

### Testing Brand Voice Workflow

#### Test Case 1: Create Configuration

```bash
# Create brand voice config
curl -X POST http://localhost:8000/api/v1/voice/config \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Startup Voice",
    "description": "Professional yet approachable"
  }'

# Response: {"config_id": "uuid", "name": "Tech Startup Voice"}
```

#### Test Case 2: Upload Knowledge Base

```bash
# Create a sample text file
cat > brand_sample.txt << EOF
We are a modern technology company focused on innovation.
Our tone is professional yet approachable.
We believe in empowering businesses through AI.
Quality and reliability are our top priorities.
EOF

# Upload to brand voice (replace config-id)
curl -X POST http://localhost:8000/api/v1/voice/config/{config-id}/upload \
  -F "file=@brand_sample.txt"

# Response:
{
  "message": "Knowledge base uploaded and processed",
  "vectors_created": 4
}
```

#### Test Case 3: Add Rules

```bash
# Add forbidden word rule
curl -X POST http://localhost:8000/api/v1/voice/config/{config-id}/rule \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "your-config-id",
    "rule_type": "forbidden_word",
    "value": "cheap"
  }'

# Add required phrase rule
curl -X POST http://localhost:8000/api/v1/voice/config/{config-id}/rule \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "your-config-id",
    "rule_type": "required_phrase",
    "value": "innovation"
  }'
```

#### Test Case 4: Check Voice Alignment

**Test Good Content:**
```bash
curl -X POST http://localhost:8000/api/v1/voice/check \
  -H "Content-Type: application/json" \
  -d '{
    "text": "We empower businesses with innovative AI solutions that deliver quality results.",
    "config_id": "your-config-id"
  }'

# Expected: High score (80-100)
{
  "overall_score": 92,
  "vector_score": 95,
  "rule_score": 90,
  "violations": [],
  "suggestions": []
}
```

**Test Bad Content:**
```bash
curl -X POST http://localhost:8000/api/v1/voice/check \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Buy our cheap products now! Limited time offer!",
    "config_id": "your-config-id"
  }'

# Expected: Low score (0-50)
{
  "overall_score": 35,
  "vector_score": 45,
  "rule_score": 10,
  "violations": [
    {
      "type": "forbidden_word",
      "word": "cheap",
      "suggestion": "Remove or replace cheap"
    },
    {
      "type": "missing_phrase",
      "phrase": "innovation",
      "suggestion": "Consider adding innovation"
    }
  ]
}
```

### Hybrid Scoring Algorithm

**Formula:** `Final Score = (Vector Score × 0.7) + (Rule Score × 0.3)`

- **Vector Score (0-100):** Cosine similarity with stored brand voice vectors
- **Rule Score (0-100):**
  - Starts at 100
  - -20 points per forbidden word found
  - -10 points per required phrase missing

---

## API Testing with cURL

### Complete Workflow Example

```bash
# 1. Start an analysis
ANALYSIS=$(curl -s -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "keywords": ["web", "design"]
  }')

ANALYSIS_ID=$(echo $ANALYSIS | jq -r '.analysis_id')
echo "Analysis ID: $ANALYSIS_ID"

# 2. Wait a few seconds, then check status
sleep 10
curl http://localhost:8000/api/v1/analysis/$ANALYSIS_ID | jq

# 3. Generate recommendations
curl -X POST http://localhost:8000/api/v1/optimization/generate \
  -H "Content-Type: application/json" \
  -d "{\"analysis_id\": \"$ANALYSIS_ID\"}" | jq

# 4. Get recommendations
curl http://localhost:8000/api/v1/analysis/$ANALYSIS_ID/recommendations | jq
```

---

## Troubleshooting

### Common Issues

#### 1. Frontend Can't Connect to Backend

**Symptom:** Network errors, "Failed to fetch"

**Solutions:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check Docker logs
docker-compose logs backend

# Verify CORS settings in backend/.env
CORS_ORIGINS=["http://localhost:3000"]
```

#### 2. Database Connection Error

**Symptom:** `sqlalchemy.exc.OperationalError`

**Solutions:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Verify DATABASE_URL in .env
# For Docker: postgresql://postgres:postgres@postgres:5432/geo_platform
# For local: postgresql://postgres:postgres@localhost:5432/geo_platform

# Enable pgvector extension
docker-compose exec postgres psql -U postgres -d geo_platform -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 3. OpenAI API Errors

**Symptom:** 401 Unauthorized, 429 Rate Limit

**Solutions:**
```bash
# Verify API key
echo $OPENAI_API_KEY

# Check rate limits at https://platform.openai.com/account/limits

# Fallback recommendations will be used if API fails
```

#### 4. Analysis Stuck in "processing"

**Symptom:** Analysis never completes

**Solutions:**
```bash
# Check Celery worker logs
docker-compose logs celery

# Restart Celery
docker-compose restart celery

# Check for network issues preventing URL fetching
```

### Development Tips

1. **View Backend Logs:**
   ```bash
   docker-compose logs -f backend
   ```

2. **View Database:**
   ```bash
   docker-compose exec postgres psql -U postgres -d geo_platform
   \dt  # List tables
   SELECT * FROM analyses LIMIT 5;
   ```

3. **Clear Database:**
   ```bash
   docker-compose down -v  # Warning: Deletes all data
   docker-compose up --build
   ```

4. **Hot Reload Issues:**
   - Backend: Changes auto-reload with uvicorn --reload
   - Frontend: Changes auto-reload with Nuxt dev server
   - If not working, restart the specific service

---

## Performance Benchmarks

### Expected Response Times

- **Dashboard Load:** < 500ms
- **Start Analysis:** < 200ms (returns immediately with analysis_id)
- **Analysis Completion:** 10-30 seconds
- **Recommendation Generation:** 5-15 seconds
- **Brand Voice Check:** 2-5 seconds

### Optimization Tips

1. **Database Queries:** Add indexes for frequently queried fields
2. **Caching:** Implement Redis caching for repeated analyses
3. **Rate Limiting:** Enforce limits to prevent abuse
4. **Background Tasks:** Use Celery for all long-running operations

---

## Next Steps

After testing:

1. **Deploy to Production:**
   - Use environment-specific .env files
   - Enable HTTPS
   - Set up proper monitoring (Sentry)
   - Configure backups

2. **Add Authentication:**
   - Integrate Supabase Auth
   - Protect all API routes
   - Implement organization-based access control

3. **Enable Stripe:**
   - Configure webhook endpoint
   - Test subscription flows
   - Implement usage tracking

4. **Enhance Features:**
   - Real-time WebSocket updates
   - Scheduled monitoring
   - Email notifications
   - Advanced analytics

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs [service-name]`
2. Review API docs: http://localhost:8000/api/v1/docs
3. Check database state
4. Create GitHub issue with logs and steps to reproduce

Happy Testing! 🚀
