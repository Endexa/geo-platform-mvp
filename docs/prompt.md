# Session Starter Prompt

> Copy everything below the line and paste it as your first message in a new Claude Code session.

---

Read these files in order, then propose what to work on:

1. `CLAUDE.md` (already auto-loaded — skim it)
2. `docs/quickstart-your-claude.md`
3. `docs/BACKLOG.md`
4. `docs/progression.md`

After reading, do this:
- Run `docker-compose up --build` or `curl http://localhost:8000/health` to confirm the project is healthy.
- Tell me the current status, what's done, and what's next.
- Propose the **top 3 tasks** by priority. For each task include:
  - One-line rationale
  - **Files** you would read/modify
  - **Subagents** you would use (e.g. `python-pro`, `fastapi-pro`, `frontend-developer`)
  - **Verification** plan (how you'll confirm it works)
- Ask me which one to start (or if I have something else in mind).

## Rules for this session

### Branch discipline
- **Always work on a feature branch** — never commit directly to `main`.
- **Before creating your branch:** run `git pull origin main` to start from latest.
- **Do NOT switch branches** during the session. Use `git show main:path/to/file` instead.

### Branch verification before EVERY commit
```bash
git branch --show-current    # Must show YOUR feature branch, not main
```

### Testing
- Run `cd frontend && npm run build` after any frontend change.
- Run `cd backend && pytest` after any backend change (if tests exist).
- Run `docker-compose up --build` after infrastructure changes.

### Communication
- **Ask me before starting each task** — confirm priority.
- **Ask me after finishing each task** — report changes, ask what's next.
- Follow the commit rules in `docs/quickstart-your-claude.md` exactly.
- If you discover bugs or ideas, mention them and let me decide priority.

### Common pitfalls
1. **Check `docs/INCIDENTS.md` before debugging** — the fix might already be documented.
2. **Always stage specific files** — never `git add -A`.
3. **Update `docs/progression.md` before committing** — mandatory.
4. **Brand Signature uses pgvector only** — no external vector DB. See `docs/ARCHITECTURE.md` for the 4-layer design.
