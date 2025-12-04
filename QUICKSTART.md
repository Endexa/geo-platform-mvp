# 🚀 GEO Platform - Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Prerequisites

Install Docker Desktop:
- **macOS/Windows:** https://www.docker.com/products/docker-desktop
- **Linux:** `sudo apt-get install docker-compose`

## Step 2: Get API Keys

### OpenAI API Key (Required)
1. Go to https://platform.openai.com/api-keys
2. Create new key
3. Copy the key (starts with `sk-`)

### Supabase (Optional for MVP)
1. Go to https://supabase.com
2. Create new project
3. Get URL and anon key from Project Settings > API

## Step 3: Configure Environment

```bash
cd /home/salim/Informatique/Perso/Endexa/geo-platform-mvp

# Backend
cd backend
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Frontend
cd ../frontend
cp .env.example .env
# No changes needed for local development
```

## Step 4: Start Everything

```bash
# From project root
cd /home/salim/Informatique/Perso/Endexa/geo-platform-mvp
docker-compose up --build
```

Wait 1-2 minutes for all services to start.

## Step 5: Access the Application

Open in your browser:
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/api/v1/docs

## Step 6: Test the Core Flow

### Test 1: Analyze a Website

1. Go to http://localhost:3000/analyze
2. Enter URL: `https://example.com`
3. Enter keywords: `web, design, development`
4. Click "Analyze Now"
5. Wait 10-15 seconds
6. See your GEO score!

### Test 2: Check Dashboard

1. Go to http://localhost:3000
2. See your analysis in "Recent Audits"
3. View average GEO score

### Test 3: Test API Directly

```bash
# Health check
curl http://localhost:8000/health

# Start analysis
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://wikipedia.org", "keywords": ["knowledge"]}'
```

## Common Commands

```bash
# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Restart a service
docker-compose restart backend

# Clear everything
docker-compose down -v  # Warning: Deletes all data
```

## Need Help?

- **Detailed Testing:** See [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- **Full Documentation:** See [README.md](./README.md)
- **API Docs:** http://localhost:8000/api/v1/docs

## What's Next?

✅ You now have a working GEO Platform MVP!

Try these:
1. Analyze multiple URLs with different keywords
2. Compare scores across different websites
3. Generate AI recommendations
4. Test the Brand Voice checker (see TESTING_GUIDE.md)

Enjoy optimizing for Generative Engines! 🎉
