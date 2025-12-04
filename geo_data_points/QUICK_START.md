# GEO Data Points - Quick Start Guide

Get up and running with the GEO Data Points system in 5 minutes!

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL running (via Docker or locally)
- Backend API running (optional, for REST API access)

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

```bash
cd geo_data_points
pip install -r requirements.txt
```

**What gets installed:**
- SQLAlchemy (database ORM)
- psycopg2 (PostgreSQL driver)
- requests (HTTP client)
- beautifulsoup4 (HTML parsing)
- textstat (text analysis)

### Step 2: Test Individual Scripts (No Database Required)

```bash
python test_measurements.py https://anthropic.com
```

**Expected output:**
```
============================================================
Testing: RobotsTxtGPTBot
URL: https://anthropic.com
============================================================

✓ RobotsTxtGPTBot
  Score: 100.00/100
  Comment: GPTBot is allowed to crawl this site. ✓ Optimal for ChatGPT visibility.
  Execution Time: 245ms
  Success: True

...

============================================================
SUMMARY
============================================================
Total Tests: 5
Successful: 5
Failed: 0

Average Score: 85.40/100
Total Execution Time: 1250ms (1.25s)
```

✅ **If this works, your scripts are working correctly!**

### Step 3: Initialize Database & Run Full Analysis

```bash
# Initialize database tables
python init_db.py

# Run complete analysis
python orchestrator/run_all.py https://anthropic.com --summary
```

**Expected output:**
```
2025-12-04 13:10:15 - orchestrator - INFO - Initialized orchestrator for https://anthropic.com
2025-12-04 13:10:15 - orchestrator - INFO - Loaded 108 data points from JSON
2025-12-04 13:10:16 - orchestrator - INFO - [1/108] Processing: Robots.txt - GPTBot
2025-12-04 13:10:16 - orchestrator - INFO - ✓ Completed: Robots.txt - GPTBot - Score: 100.00 (245ms)
...

============================================================
Analysis completed successfully!
Analysis ID: 550e8400-e29b-41d4-a716-446655440000
============================================================

Summary:
  URL: https://anthropic.com
  Total Data Points: 108
  Successful: 5
  Failed: 103  (scripts not implemented yet)
  Average GEO Score: 85.40/100

Module Scores:
  WI: 87.50/100 (4 data points)
  SEO: 80.00/100 (1 data points)
```

✅ **If this works, your database integration is working!**

## 🌐 Using the REST API

### 1. Start Backend

```bash
cd ../backend
docker-compose up -d
```

### 2. Trigger Analysis

```bash
curl -X POST http://localhost:8000/api/v1/geo-datapoints/run \
  -H "Content-Type: application/json" \
  -d '{"url": "https://anthropic.com"}'
```

**Response:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "GEO analysis started"
}
```

### 3. Get Results

```bash
# Wait 2-3 seconds for analysis to complete, then:
curl http://localhost:8000/api/v1/geo-datapoints/550e8400-e29b-41d4-a716-446655440000
```

### 4. Get Summary

```bash
curl http://localhost:8000/api/v1/geo-datapoints/550e8400-e29b-41d4-a716-446655440000/summary
```

## 🔧 Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Database
GEO_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geo_platform

# Settings
GEO_REQUEST_TIMEOUT=10
GEO_MAX_RETRIES=3

# Optional: External APIs (when available)
OPENAI_API_KEY=sk-...
AHREFS_API_KEY=...
GOOGLE_PAGESPEED_API_KEY=...
```

### Database Connection

**Using Docker:**
```bash
# Already running if you started backend
docker ps | grep postgres
```

**Manual PostgreSQL:**
```bash
# Connect to create database
psql -U postgres
CREATE DATABASE geo_platform;
\q

# Update DATABASE_URL in .env
GEO_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/geo_platform
```

## 📊 Understanding Results

### Score Ranges

- **90-100**: Excellent GEO optimization ✅
- **70-89**: Good, minor improvements possible ✓
- **50-69**: Average, significant improvements needed ⚠
- **30-49**: Poor, critical issues ⚠⚠
- **0-29**: Very poor, major problems ❌

### Modules

- **WI** (Web Infrastructure): Technical foundation (robots.txt, schemas, performance)
- **CNT** (Content): Content quality & structure
- **BV** (Brand Visibility): Brand presence across web
- **SEO**: Traditional SEO factors
- **UX** (User Experience): Performance & usability
- **COMP** (Competitive): Competitive positioning
- **LEG** (Legal): Compliance & policies

### Priority Levels

- **High**: Critical for GEO ranking (implement first)
- **Med**: Important, noticeable impact
- **Low**: Nice to have, minor impact

## 🐛 Troubleshooting

### "Module not found" error

```bash
# Install dependencies
pip install -r requirements.txt

# Or install specific package
pip install sqlalchemy psycopg2-binary requests beautifulsoup4
```

### Database connection error

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U postgres -d geo_platform
# Enter password: postgres

# If database doesn't exist
psql -U postgres -c "CREATE DATABASE geo_platform;"
```

### "Failed to fetch URL" errors

**Normal for some URLs:**
- Sites that block bots
- Sites with aggressive rate limiting
- Invalid/non-existent URLs

**Check:**
```bash
# Test direct access
curl -I https://example.com

# Test with custom user agent
curl -I -A "GeoBot/1.0" https://example.com
```

### "Script not implemented yet" messages

**This is normal!** Only 5/108 scripts are implemented.

The orchestrator will:
- Skip unimplemented scripts
- Log warning messages
- Store zero scores
- Continue with remaining scripts

To implement more scripts, see `README.md` section "Implementing New Data Points".

## 📚 Next Steps

### Learn More

1. **Full Documentation**: Read `README.md` (350+ lines)
2. **Implementation Details**: Check `IMPLEMENTATION_SUMMARY.md`
3. **Architecture**: Review `TECHNICAL_STATE_REPORT.md` (in parent directory)

### Implement More Data Points

1. Choose a data point from `data_points.json`
2. Create script in `scripts/` folder
3. Follow the pattern from existing scripts
4. Test with `python scripts/your_script.py https://example.com`

**Example templates available:**
- `robots_txt_gptbot.py` - Simple API check
- `schema_org_organization.py` - JSON-LD parsing
- `response_time.py` - Performance measurement
- `title_tag_optimization.py` - HTML analysis

### Integrate with Dashboard

The REST API is ready! Build frontend components to:
- Display module scores
- Show individual data points
- Visualize trends over time
- Compare multiple sites

## 💡 Tips

### Best Practices

1. **Start Small**: Test with known URLs (anthropic.com, example.com)
2. **Monitor Logs**: Check `logs/geo_datapoints_*.log` for details
3. **Handle Failures**: Scripts failing is normal, system recovers gracefully
4. **Implement Incrementally**: Add 5-10 scripts at a time, test thoroughly

### Performance Optimization

1. **Use Caching**: Cache robots.txt, schemas (same for all pages)
2. **Parallel Execution**: Enable `GEO_PARALLEL_EXECUTION=true`
3. **Connection Pooling**: Reuse HTTP connections
4. **Timeout Tuning**: Adjust `GEO_REQUEST_TIMEOUT` for slow sites

### Development Workflow

```bash
# 1. Create new script
cp scripts/robots_txt_gptbot.py scripts/my_new_check.py

# 2. Modify the class
# Edit scripts/my_new_check.py

# 3. Test standalone
python scripts/my_new_check.py https://example.com

# 4. Test with orchestrator
python orchestrator/run_all.py https://example.com --summary

# 5. Verify in database
psql geo_platform -c "SELECT data_point_name, score FROM geo_data_point_results ORDER BY created_at DESC LIMIT 10;"
```

## 🎯 Success Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Test script runs successfully (`python test_measurements.py`)
- [ ] Database initialized (`python init_db.py`)
- [ ] Orchestrator runs without errors (`python orchestrator/run_all.py`)
- [ ] Results stored in database (check via psql or API)
- [ ] Backend API responds to `/api/v1/geo-datapoints/run`

## 🆘 Getting Help

**Check these resources:**

1. **README.md** - Complete documentation
2. **IMPLEMENTATION_SUMMARY.md** - Implementation details
3. **Logs** - `logs/geo_datapoints_YYYYMMDD.log`
4. **Scripts** - Examine working examples

**Common issues:**
- Database connection → Check Docker/PostgreSQL status
- Module import errors → Install dependencies
- Script failures → Normal for unimplemented scripts (103/108)
- Slow execution → Expected, each script takes ~100-500ms

## 🚀 You're Ready!

The system is fully operational. Start analyzing URLs and implementing more data points!

```bash
# Quick test
python test_measurements.py https://anthropic.com

# Full analysis
python orchestrator/run_all.py https://your-site.com --summary
```

Happy optimizing! 🎉
