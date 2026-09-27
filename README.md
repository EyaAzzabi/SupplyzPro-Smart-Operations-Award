# FailureLens

**Finding the Hidden Failures** — a framework for detecting, grouping, and prioritizing failures in AI-agent conversations, built for SupplyzPro's "Come Build with AI" hackathon challenge.

> We don't just find bugs in AI-agent conversations — we group them by root cause, rank them by real impact, and prove a fix works.

## The problem

Most agent failures never throw an error. A tool call "succeeds" with an empty or wrong result, the agent smooths it over with a confident sentence, and the only trace is a customer getting the wrong answer. FailureLens finds that gap between what a tool returned and what the agent claimed — not just counts of exceptions.

## Architecture

```
ai/          The AI system: detection, clustering, prioritization, regression probes
database/    SQLite — conversations, tool calls, detected failures, clusters, probes
backend/     FastAPI — REST API in front of the database
frontend/    React (Vite) — the dashboard
data/        Synthetic conversation generator (feeds the AI system)
results/     ai/ layer's JSON output, consumed by database/seed_db.py
app.py       Streamlit dashboard (kept as a zero-setup fallback demo)
```

Data flow: `data/` generates conversations → `ai/` detects/clusters/prioritizes them into `results/*.json` → `database/seed_db.py` loads that into SQLite → `backend/` serves it over REST → `frontend/` renders it.

## Team task split (5 people, work in parallel)

Everyone can start immediately — the layers are already wired together end to end with synthetic data, so no one is blocked waiting on anyone else. Pull latest, then work in your own folder.

**1. AI/Detection** — `ai/`
- `rules.py` (error codes, timeouts, retry-loop duplicate calls), `llm_judge.py` (hallucination + wrong-target detection), `behavioral.py` (context collapse, user frustration), `cluster.py` (TF-IDF/KMeans root-cause grouping), `prioritize.py` (the scoring formula), `regression_probes.py` (fix verification).
- Today: set `NVIDIA_API_KEY` in `.env` (see `.env.example`) so `llm_judge.py` calls a real NVIDIA NIM model instead of the offline fallback heuristic. Sanity-check detection quality; tune clustering if categories look muddy. Re-run with `python -m ai.run_pipeline`.

**2. Data** — `data/`
- `generate_conversations.py` — the synthetic conversation generator (60 "before" / 60 "after" conversations, 5 seeded failure types).
- Today: add more variety (more SKUs/suppliers/phrasing) so the demo doesn't look templated. Regenerate with `python data/generate_conversations.py`.

**3. Database** — `database/`
- `schema.sql` (conversations, clusters, failure_instances, regression_probes tables), `seed_db.py` (loads `results/*.json` into `failurelens.db`).
- Today: own the schema — extend it if the AI or backend teams need new fields. Re-seed with `python -m database.seed_db` any time `results/` changes.

**4. Backend** — `backend/`
- `main.py` — FastAPI app: `/api/summary`, `/api/clusters`, `/api/clusters/{id}/evidence`, `/api/fix-comparison`.
- Today: harden/extend endpoints as the frontend needs them. Run with `uvicorn backend.main:app --reload --port 8000`; interactive docs at `/docs`.

**5. Frontend** — `frontend/`
- React + Vite app in `frontend/src/`: `ClusterTable`, `EvidencePanel`, `Transcript`, `FixComparison` components, wired to the backend via `src/api.js`.
- Today: this is a working skeleton, not a finished UI — own the visual design, empty/loading states, and polish. Run with `npm run dev` inside `frontend/` (copy `.env.example` to `.env` first).

## Setup

```bash
# Python side (ai, database, backend)
pip install -r requirements.txt
cp .env.example .env   # optional: add NVIDIA_API_KEY for a live NIM judge

# Frontend
cd frontend && npm install && cp .env.example .env
```

## Running the full stack

```bash
# 1. (re)generate synthetic data, if you changed the generator
python data/generate_conversations.py

# 2. detect -> cluster -> prioritize -> regression probes
python -m ai.run_pipeline

# 3. load results into the database
python -m database.seed_db

# 4. start the API
uvicorn backend.main:app --reload --port 8000

# 5. start the frontend (separate terminal)
cd frontend && npm run dev
```

`data/*.json`, `results/*.json`, and `database/failurelens.db` are all committed, so steps 4-5 work immediately without re-running 1-3 — only re-run them if you change the generator or detection logic.

**Fallback demo path**: `streamlit run app.py` reads `results/*.json` directly and needs nothing else running — useful if the full stack isn't up yet during the demo.

## NVIDIA integration

The LLM-as-judge layer (`ai/llm_judge.py`) calls NVIDIA's hosted NIM chat-completions API when `NVIDIA_API_KEY` is set (get one at [build.nvidia.com](https://build.nvidia.com)). Without a key, it falls back to a deterministic offline heuristic that checks the same two things (claimed numbers match the tool's response, claimed entity matches the one requested) — so the pipeline is reproducible without any external dependency, and swapping in a live model is a one-line env var change.

## Disclosure

All conversation data is **synthetic**, generated by `data/generate_conversations.py` to represent plausible SupplyzPro workflows with deliberately seeded failure patterns. AI tools used: an LLM-as-judge (NVIDIA NIM-hosted model, or an offline heuristic fallback) for hallucination/wrong-target detection, and TF-IDF/KMeans for unsupervised root-cause clustering.

## Limitations and next steps

- Runs on synthetic data. Applied to real conversation/tool-call logs, the LLM-as-judge rubric should be validated against a hand-labeled sample before trusting it at scale.
- Severity and blast-radius weights are currently fixed; they should be tuned with input from the team that owns each workflow.
- The before/after comparison here is a simulated fix on a second synthetic batch — in production, a cluster's score would be tracked over time against the real system to verify a fix actually worked.
