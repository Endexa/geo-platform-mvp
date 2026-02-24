#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PID_BACKEND=""
PID_CELERY=""
PID_FRONTEND=""

cleanup() {
  echo -e "\n${YELLOW}Shutting down...${NC}"
  [[ -n "$PID_BACKEND" ]] && kill "$PID_BACKEND" 2>/dev/null || true
  [[ -n "$PID_CELERY" ]] && kill "$PID_CELERY" 2>/dev/null || true
  [[ -n "$PID_FRONTEND" ]] && kill "$PID_FRONTEND" 2>/dev/null || true
  wait 2>/dev/null || true
  docker stop geo-redis 2>/dev/null || true
  echo -e "${GREEN}All services stopped.${NC}"
}
trap cleanup EXIT

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN} GEO Platform — Development Server${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# --- Free up ports from stale processes ---
for port in 3000 8000; do
  pid=$(lsof -ti :"$port" 2>/dev/null || true)
  if [[ -n "$pid" ]]; then
    echo -e "${YELLOW}Killing stale process on port $port (PID $pid)${NC}"
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
done

# --- Supabase DB check ---
echo -e "\n${YELLOW}[1/5] Supabase PostgreSQL${NC}"
cd "$PROJECT_DIR/backend"
source venv/bin/activate
python -c "
from app.core.config import settings
from sqlalchemy import create_engine, text
engine = create_engine(settings.DATABASE_URL, connect_args={'connect_timeout': 10})
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
    print('  Connected to Supabase')
" 2>&1 || { echo -e "  ${RED}Cannot reach Supabase DB. Check DATABASE_URL in backend/.env${NC}"; exit 1; }
echo -e "  ${GREEN}OK${NC}"

# --- Redis ---
echo -e "\n${YELLOW}[2/5] Redis${NC}"
if docker ps --format '{{.Names}}' | grep -q '^geo-redis$'; then
  echo -e "  ${GREEN}Already running${NC}"
else
  docker rm -f geo-redis 2>/dev/null || true
  docker run -d \
    --name geo-redis \
    -p 6379:6379 \
    redis:7-alpine >/dev/null
  echo -e "  ${GREEN}Started (port 6379)${NC}"
fi

# --- Alembic migrations ---
echo -e "\n${YELLOW}[3/5] Database migrations${NC}"
alembic upgrade head 2>&1 | tail -3
echo -e "  ${GREEN}Migrations applied${NC}"

# --- Backend ---
echo -e "\n${YELLOW}[4/5] Backend (FastAPI)${NC}"
uvicorn app.main:app --reload --port 8000 &
PID_BACKEND=$!
echo -e "  ${GREEN}Started (port 8000, PID $PID_BACKEND)${NC}"

# --- Celery ---
echo -e "\n${YELLOW}[5/5] Celery worker${NC}"
celery -A app.tasks.celery_app worker --loglevel=info -Q geo_platform,audit,analysis &
PID_CELERY=$!
echo -e "  ${GREEN}Started (PID $PID_CELERY)${NC}"
cd "$PROJECT_DIR"

# --- Frontend ---
echo -e "\n${YELLOW}[6/5] Frontend (Nuxt)${NC}"
cd "$PROJECT_DIR/frontend"
npm run dev &
PID_FRONTEND=$!
echo -e "  ${GREEN}Started (port 3000, PID $PID_FRONTEND)${NC}"
cd "$PROJECT_DIR"

echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} All services running${NC}"
echo -e "  Frontend:  http://localhost:3000"
echo -e "  Backend:   http://localhost:8000"
echo -e "  API Docs:  http://localhost:8000/api/v1/docs"
echo -e "  Database:  Supabase (remote)"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"

wait
