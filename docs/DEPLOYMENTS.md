# Deployment Log

> **Update this file after every production deployment.** Newest entries at the top.

---

## Pre-Deploy Checklist

- [ ] Backend: `pytest` passes
- [ ] Frontend: `npm run build` passes
- [ ] Docker: `docker-compose up --build` starts clean
- [ ] Environment variables set for target environment
- [ ] Database migrations applied: `alembic upgrade head`
- [ ] `docs/progression.md` updated
- [ ] `CLAUDE.md` updated if architecture changed

## Post-Deploy Verification

- [ ] `curl https://<domain>/health` returns `{"status": "healthy"}`
- [ ] Frontend loads at target URL
- [ ] Core flow works: analyze URL → see scores

---

## Deployment History

<!-- No deployments yet. Add entries here as:

### YYYY-MM-DD — Description

**Target:** (local / staging / production)
**Changes:**
- Change 1
- Change 2

**Migrations:** (none / list)
**Edge Functions:** (none / list)
**Verified:** (yes/no + method)

-->

_No deployments recorded yet._

<!-- Keep last 5 entries. Move older to docs/archive/DEPLOYMENTS-pre-YYYY-MM-DD.md -->
