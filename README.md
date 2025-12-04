# GEO Platform MVP

A production-grade Generative Engine Optimization (GEO) platform built with a modern, scalable stack.

## 🚀 Quick Start

### Prerequisites

- **Node.js**: v18+
- **Python**: 3.11+
- **Docker**: Latest version
- **Supabase Account**: For database and auth

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd geo-platform-mvp
   ```

2. **Setup Backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

3. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   # Edit .env with your API URL
   ```

### Running the Application

#### Development Mode

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Access the app at `http://localhost:3000`

#### Using Docker

```bash
docker-compose up --build
```

## 📁 Project Structure

```
geo-platform-mvp/
├── backend/              # FastAPI Python backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Config, security
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic
│   │   └── main.py      # App entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/            # Nuxt 3 frontend
│   ├── components/      # Vue components
│   ├── layouts/         # Layout templates
│   ├── pages/           # Route pages
│   ├── composables/     # Reusable logic
│   └── nuxt.config.ts
│
├── docker-compose.yml
└── README.md
```

## 🔧 Tech Stack

### Frontend
- **Nuxt 3** - Vue.js framework
- **Tailwind CSS** - Utility-first CSS
- **Tremor** - Dashboard charts
- **Lucide** - Icon library

### Backend
- **FastAPI** - Modern Python API framework
- **Supabase** - PostgreSQL database with auth
- **LiteLLM** - Multi-provider LLM router
- **LangChain** - LLM orchestration
- **Redis + Celery** - Background tasks

### Database
- **PostgreSQL 15+** - Relational data
- **pgvector** - Vector embeddings

## 🎯 Core Features

### Module 1: Intelligence Engine
- URL analysis and scoring
- GEO score calculation (0-100)
- Visibility, Readability, Authority metrics
- Historical trend analysis

### Module 2: Optimization Engine
- AI-powered recommendations
- Gap analysis vs competitors
- Jira integration for task creation
- Priority-based action items

### Module 3: Brand Voice
- Vector-based similarity checking
- Rule-based content validation
- Hybrid scoring algorithm
- Real-time content feedback

## 🔐 Environment Variables

### Backend (.env)
```env
SUPABASE_URL=your-project-url
SUPABASE_KEY=your-anon-key
OPENAI_API_KEY=your-openai-key
REDIS_URL=redis://localhost:6379
STRIPE_SECRET_KEY=your-stripe-key
JIRA_BASE_URL=your-jira-url
JIRA_API_TOKEN=your-jira-token
```

### Frontend (.env)
```env
NUXT_PUBLIC_API_URL=http://localhost:8000
NUXT_PUBLIC_SUPABASE_URL=your-project-url
NUXT_PUBLIC_SUPABASE_KEY=your-anon-key
```

## 📊 Database Setup

1. Create a Supabase project
2. Enable pgvector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Run migrations:
   ```bash
   cd backend
   alembic upgrade head
   ```

## 🚢 Deployment

### Frontend (Vercel)
```bash
cd frontend
vercel --prod
```

### Backend (Railway/Render)
- Connect GitHub repository
- Set environment variables
- Deploy from main branch

### Database
- Use Supabase cloud hosting
- Configure connection pooling
- Enable Row Level Security (RLS)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

## 📈 Monitoring

- Backend logs: Railway/Render dashboard
- Frontend analytics: Vercel Analytics
- Database: Supabase dashboard
- Errors: Sentry (optional)

## 🔄 Development Workflow

1. Create feature branch
2. Implement changes
3. Run tests
4. Submit PR
5. Deploy to staging
6. Merge to main → auto-deploy

## 📝 API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🎨 UI/UX Features

- **Real-time Progress**: Stepper showing analysis stages
- **Score Gauges**: Color-coded donut charts (Red < 50, Yellow 50-80, Green > 80)
- **Streaming Text**: ChatGPT-style text generation
- **Premium Blur**: Freemium model with feature previews
- **Loading States**: Skeleton screens and animations

## 🤝 Contributing

This is an MVP project. Contributions welcome after v1.0 release.

## 📄 License

Proprietary - All rights reserved

## 🆘 Support

For issues and questions:
- Create GitHub issue
- Email: support@geoplatform.com

---

Built with ❤️ for the future of GEO
