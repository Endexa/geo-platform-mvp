# Archive Index

> Historical documentation. Read only if you need context on past decisions.

---

## Original Project Documentation

| File | Description |
|------|-------------|
| `TECHNICAL_STATE_REPORT.md` | Full technical architecture report (105KB). Key parts extracted into `docs/ARCHITECTURE.md` and `docs/API-REFERENCE.md`. |
| `IMPLEMENTATION_PROGRESS.md` | Detailed 108/108 measurement script status table. Current status tracked in `docs/GEO-DATA-POINTS.md`. |
| `TESTING_GUIDE.md` | Original testing guide with curl commands and module-by-module test cases. Consolidated into `docs/TESTING-STRATEGY.md`. |
| `QUICKSTART.md` | Original 5-minute setup guide. Consolidated into `docs/quickstart-your-claude.md`. |

## Deleted (not archived)

| File | Reason |
|------|--------|
| `RAG_INTEGRATION_SUMMARY.md` | RAG system (MongoDB + Qdrant) was dead code. Brand Signature uses pgvector instead. Deleted 2026-02-21. |
| `backend/app/core/rag_system.py` | Dead code, never called by any service. |
| `backend/app/core/mongodb_client.py` | Dead code, MongoDB not in docker-compose. |
| `backend/app/core/qdrant_client.py` | Dead code, Qdrant not in docker-compose. |
| `backend/app/api/rag.py` | Dead code, standalone endpoints nothing used. |
| `backend/requirements_rag.txt` | Separate deps file, never installed. |

<!-- Add new archive entries above this line -->
