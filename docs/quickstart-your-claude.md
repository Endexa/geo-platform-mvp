# Quickstart Guide for New Claude Sessions

> **Read this when starting a new session.** It tells you how to orient yourself, find work, and operate autonomously on this project.

---

## 1. First Steps (Read Order)

Start every session by reading these files in order:

| # | File | What it gives you |
|---|------|-------------------|
| 1 | `CLAUDE.md` | Auto-loaded. Project overview, tech stack, architecture, scoring system, what works, what doesn't. |
| 2 | This file (`docs/quickstart-your-claude.md`) | How to work: finding tasks, commit rules, testing, agents. |
| 3 | `docs/BACKLOG.md` | Prioritized tasks with acceptance criteria and dependencies. |
| 4 | `docs/progression.md` | What's been done, known bugs, changelog. |
| 5 | `docs/DEPLOYMENTS.md` | What is live. Every deployment logged. Read before touching production. |
| 6 | `docs/INCIDENTS.md` | **Check FIRST when debugging any error.** Known errors + exact fixes by category. |

You should NOT need to explore the codebase after reading these files.

---

## 2. Health Check (Before Starting Work)

```bash
# One command (starts Redis, backend, Celery, frontend)
./start.sh

# Or manual (3 terminals)
docker start geo-redis || docker run -d --name geo-redis -p 6379:6379 redis:7-alpine
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev

# Verify
curl http://localhost:8000/health # Backend must respond {"status": "healthy"}
git status                        # Check branch, uncommitted changes. Start clean.
```

Database is on **Supabase** (remote PostgreSQL). No local Postgres needed.
For external service health checks, see `docs/CONNECTIONS.md`.

---

## 3. Finding Work

### Where to look (priority order):

1. **User instructions** — If the user gave you a specific task, do that first.
2. **`docs/BACKLOG.md`** — Find the current priority, pick the next unchecked task.
3. **`docs/progression.md`** — Check known issues for bugs worth fixing.
4. **Agent-Suggested Tasks** in `docs/BACKLOG.md` — Lower priority unless promoted.

### Before starting a task, always:

1. **Check with the user** if the task is still relevant: *"I'm planning to work on [task]. Is this the right priority?"*
2. Read the task's acceptance criteria in `docs/BACKLOG.md`.
3. Read the files listed for that task.

### When you discover new work:

If you find a bug, improvement, or feature idea while working:
- Add it to `docs/BACKLOG.md` under "Agent-Suggested Tasks" with `[Agent Suggested]` prefix.
- Include a brief rationale.
- **Don't implement without asking** — mention it to the user and let them decide priority.

---

## 4. How to Work (Rules)

### The golden rules:

1. **Always read files before editing them.** Never propose changes to code you haven't read.
2. **Verify the app works after every change.** Backend: `pytest` or curl. Frontend: `npm run build`.
3. **One task = one commit.** Don't batch unrelated changes.
4. **Update `docs/progression.md` changelog BEFORE every commit.** Mandatory.
5. **Update `CLAUDE.md` if architecture, features, or patterns change.**
6. **No AI attribution** in commit messages.
7. **Ask the user often.** Before starting major work, after completing a task, when unsure about priority.
8. **Check `docs/INCIDENTS.md` first when hitting any error.** If the error is there, apply the documented fix. If not, fix it, then add a new entry.

### Commit flow:

```bash
# 1. Make your code changes
# 2. Verify
cd backend && pytest              # If tests exist
cd frontend && npm run build      # Must pass
# 3. Update docs/progression.md changelog (add a row)
# 4. Update CLAUDE.md if needed
# 5. Stage specific files (NOT git add -A)
git add backend/app/path/to/changed/files docs/progression.md
# 6. Commit
git commit -m "Add schema.org FAQPage measurement"
```

### What NOT to do:

- Don't explore the whole codebase — read `CLAUDE.md` instead.
- Don't commit `.env` or secrets.
- Don't implement multiple tasks without checking in with the user between them.

---

## 5. Using Agents

See `CLAUDE.md` > "Available Subagents" for the full agent catalog.

### When to parallelize:

- **Yes:** Independent research, reading multiple files, independent code changes to different files.
- **No:** Sequential changes where file B depends on file A, code that needs to compile together.

---

## 6. Development Tools Workflow

Three tools are installed that change how you work. Read `CLAUDE.md` > "Installed Development Tools" for full details. Here's the practical workflow:

### For a large feature or redesign:

Use **GSD** (Get Shit Done) — it handles the full lifecycle:

```
/gsd:new-project          # Interview → Research → Requirements → Roadmap
/gsd:discuss-phase 1      # Lock in preferences before planning
/gsd:plan-phase 1         # Generate executable plans with verification
/gsd:execute-phase 1      # Wave-based execution with subagents
/gsd:verify-work 1        # UAT + auto gap closure
```

GSD creates a `.planning/` directory with all artifacts. Plans are saved as `.planning/phases/NN-name/NN-MM-PLAN.md`.

### For a medium task (single feature, few files):

Use **Superpowers** — it activates automatically and enforces:

1. **Brainstorm** — Ask questions, propose approaches, get approval
2. **Write plan** — Save to `docs/plans/YYYY-MM-DD-<feature>-design.md`
3. **TDD** — Failing test first, then minimal code, then refactor
4. **Code review** — Spec compliance, then code quality

The Superpowers skills activate automatically based on what you're doing. You don't need to invoke them manually.

### For any frontend/UI work:

**UI/UX Pro Max** activates automatically when it detects UI work. It will:
- Consult `design-system/endexa-geo-platform/MASTER.md` for our design system
- Apply the Data-Dense Dashboard style with our color palette
- Enforce accessibility (contrast, focus rings, touch targets)
- Use Nuxt 3 + Tailwind best practices from its CSV databases

If you need page-specific design guidance:
```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "your page description" --design-system --persist -p "Endexa GEO Platform" --page "page-name"
```

### For a small/quick fix:

Use `/gsd:quick` for lightweight planning, or just follow the golden rules in section 4.

### Decision tree:

```
Is this a large multi-phase feature or redesign?
  → YES → /gsd:new-project (full GSD workflow)
  → NO →
    Is this a medium task (new endpoint, new component, etc.)?
      → YES → Let Superpowers guide you (brainstorm → plan → TDD → review)
      → NO →
        Is this a quick bug fix or small change?
          → YES → /gsd:quick or just do it directly
```

---

## 7. Testing

### Quick smoke test:

```bash
curl http://localhost:8000/health                    # Backend up (public endpoint)

# Auth is enabled — get a token first:
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123!"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl http://localhost:8000/api/v1/dashboard/stats \
  -H "Authorization: Bearer $TOKEN"                  # API working (requires auth)

cd frontend && npm run build                         # Frontend builds
```

### Backend tests:

```bash
cd backend
source venv/bin/activate
pytest                        # Run all
pytest tests/test_analysis.py # Run specific
```

### Frontend tests:

```bash
cd frontend
npm run test
```

### Required scope by change type:

| Change Type | Minimum Test |
|------------|-------------|
| Measurement script | Run orchestrator with that script |
| API endpoint | curl test + pytest if exists |
| Frontend page | `npm run build` + manual check |
| Database schema | `alembic upgrade head` + verify |
| Docker config | `docker-compose up --build` |

---

## 8. Deployment

See `CLAUDE.md` > "Commands" for all deployment commands. See `docs/DEPLOYMENTS.md` for the log (update after every deploy).

---

## 9. Autopilot Checklist

When operating autonomously, follow this loop:

1. Read `docs/BACKLOG.md` and `docs/progression.md` to find the next task.
2. **Ask the user**: "I'm planning to work on [task]. Is this the right priority?"
3. Read the task's files and acceptance criteria.
4. Implement the task. **If you hit an error, check `docs/INCIDENTS.md` first.**
5. Verify the change works (pytest, npm run build, curl, docker-compose).
6. Update `docs/progression.md` changelog.
7. Update `CLAUDE.md` if architecture changed.
8. Commit with descriptive message.
9. If deploying: run deploy commands and **update `docs/DEPLOYMENTS.md`**.
10. **Report to the user**: "Completed [task]. Here's what changed. What should I work on next?"
11. If you discovered bugs or ideas, mention them and ask about priority.

**Key principle:** Check in with the user between tasks. Don't assume priorities — ask.

---

## 10. Documentation Maintenance Rules

Keep docs lean so every new session onboards fast. Zero information loss — always archive, never delete.

1. **Changelog cap:** `docs/progression.md` keeps max 15 entries. Move oldest to `docs/archive/changelog-YYYY-MM.md`.
2. **Deployment log cap:** `docs/DEPLOYMENTS.md` keeps last 5 deployments. Move oldest to `docs/archive/DEPLOYMENTS-pre-YYYY-MM-DD.md`.
3. **Phase completion:** When a BACKLOG phase is marked COMPLETE, move full task details to `docs/archive/BACKLOG-completed-phases.md` and replace with a one-liner summary.
4. **Architecture doc lifecycle:** Architecture/plan docs stay in `docs/` while active. Once COMPLETE, move to `docs/archive/`.
5. **Archive index:** After moving files, update `docs/archive/README.md`.
6. **Never delete:** Always move to archive. All archived content is accessible in `docs/archive/`.
