# Session Starter Prompt

> Copy everything below the line and paste it as your first message in a new Claude Code session.

---

Read these files in order, then propose what to work on:

1. `CLAUDE.md` (already auto-loaded — skim it, especially "Installed Development Tools")
2. `docs/quickstart-your-claude.md` (especially section 6: Development Tools Workflow)
3. `docs/BACKLOG.md`
4. `docs/progression.md`

After reading, do this:
- Run `docker-compose up --build` or `curl http://localhost:8000/health` to confirm the project is healthy.
- Tell me the current status, what's done, and what's next.
- Propose the **top 3 tasks** by priority. For each task include:
  - One-line rationale
  - **Files** you would read/modify
  - **Subagents** you would use (e.g. `python-pro`, `fastapi-pro`, `frontend-developer`)
  - **Tool workflow**: which dev tool to use (GSD for large features, Superpowers for medium tasks, direct for quick fixes)
  - **Verification** plan (how you'll confirm it works)
- Ask me which one to start (or if I have something else in mind).

## Rules for this session

### Development tools (IMPORTANT — read this)

Three tools are installed that change how you work. See `CLAUDE.md` > "Installed Development Tools" for full details.

**Decision tree:**
- **Large feature or redesign** → Use `/gsd:new-project` (full spec-driven workflow with phases)
- **Medium task** (new endpoint, component, etc.) → Let Superpowers guide you (brainstorm → plan → TDD → review)
- **Quick fix** → `/gsd:quick` or direct implementation
- **Any frontend/UI work** → UI/UX Pro Max activates automatically. Always consult `design-system/endexa-geo-platform/MASTER.md`

**Non-negotiable rules from these tools:**
1. **No code before tests** — write failing test first, verify it fails, then code (Superpowers TDD)
2. **No code before design** — brainstorm and save a plan before implementing (Superpowers brainstorming)
3. **No "should work" claims** — run the verification command and show actual output before claiming completion
4. **Follow the design system** — colors, fonts, spacing from `design-system/endexa-geo-platform/MASTER.md`

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
5. **Frontend must follow design system** — check `design-system/endexa-geo-platform/MASTER.md` before any UI work.
