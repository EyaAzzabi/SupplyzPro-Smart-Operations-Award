# X-Ray

**Finding the Hidden Failures** — sees through a confident-sounding agent response to what the tool actually returned. Built for SupplyzPro's "Come Build with AI" hackathon challenge.

> We don't just find bugs in AI-agent conversations — we group them by root cause, rank them by real impact, and prove a fix works.

## The problem

Most agent failures never throw an error. A tool call "succeeds" with an empty or wrong result, the agent smooths it over with a confident sentence, and the only trace is a customer getting the wrong answer. X-Ray finds that gap between what a tool returned and what the agent claimed — not just counts of exceptions.

## Architecture

```
ai/          The AI system: detection, clustering, prioritization, regression probes
data/        Synthetic conversation generator (feeds the AI system)
results/     ai/ layer's JSON output, consumed by database/seed_db.py
evaluation/  Computes the required metrics against ground truth -> evaluation/results/
database/    SQLite — conversations, tool calls, detected failures, clusters, probes
backend/     FastAPI — REST API in front of the database
frontend/    React (Vite) — the dashboard
app.py       Streamlit dashboard (kept as a zero-setup fallback demo)
```

Data flow: `data/` generates conversations → `ai/` detects/clusters/prioritizes them into `results/*.json` → `database/seed_db.py` loads that into SQLite → `backend/` serves it over REST → `frontend/` renders it. `evaluation/` runs the same AI layer against ground truth separately, to score it rather than just run it.

## Team task split (5 people, work in parallel)

Everyone can start immediately — the layers are already wired together end to end with synthetic data, so no one is blocked waiting on anyone else. Pull latest, then work in your own folder.

**1. AI/Detection** — `ai/`
- `rules.py` (error codes, timeouts, retry-loop duplicate calls), `llm_judge.py` (hallucination + wrong-target detection), `behavioral.py` (context collapse, user frustration), `cluster.py` (TF-IDF/KMeans root-cause grouping), `prioritize.py` (the scoring formula), `regression_probes.py` (fix verification).
- Today: set `NVIDIA_API_KEY` in `.env` (see `.env.example`) so `llm_judge.py` calls a real NVIDIA NIM model instead of the offline fallback heuristic. Sanity-check detection quality; tune clustering if categories look muddy. Re-run with `python -m ai.run_pipeline`.

**2. Data** — `data/`
- `generate_conversations.py` — the synthetic conversation generator (60 "before" / 60 "after" conversations, 6 seeded failure types, plus legitimate-retry and self-correction-recovery cases that should *not* be flagged).
- Today: add more variety (more SKUs/suppliers/phrasing) so the demo doesn't look templated. Regenerate with `python data/generate_conversations.py`.

**3. Database** — `database/`
- `schema.sql` (conversations, clusters, failure_instances, regression_probes tables), `seed_db.py` (loads `results/*.json` into `xray.db`).
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

`data/*.json`, `results/*.json`, and `database/xray.db` are all committed, so steps 4-5 work immediately without re-running 1-3 — only re-run them if you change the generator or detection logic.

**Fallback demo path**: `streamlit run app.py` reads `results/*.json` directly and needs nothing else running — useful if the full stack isn't up yet during the demo.

## NVIDIA integration

The LLM-as-judge layer (`ai/llm_judge.py`) calls NVIDIA's hosted NIM chat-completions API when `NVIDIA_API_KEY` is set (get one at [build.nvidia.com](https://build.nvidia.com)). Without a key, it falls back to a deterministic offline heuristic that checks the same two things (claimed numbers match the tool's response, claimed entity matches the one requested) — so the pipeline is reproducible without any external dependency, and swapping in a live model is a one-line env var change.

## Evaluation

```bash
python -m evaluation.run_evaluation
```

Computes the six required metrics against the synthetic ground truth in `data/conversations_before.json` and writes `evaluation/results/metrics.json` / `metrics.md`:

| Metric | Result (local-only run) |
|---|---|
| Failure detection precision / recall | 1.00 / 1.00 (28 true positives, 0 false positives, 0 false negatives) |
| Cluster precision / recall (pairwise) | 1.00 / 1.00 |
| Root-cause accuracy | 1.00 |
| Silent-failure recall | 1.00 |
| Analysis latency | detection ~0.002s, clustering ~1.7s, prioritization ~0s for 60 conversations |
| Cost per analysis | $0 (offline heuristic judge); with `NVIDIA_API_KEY` set, ~1 LLM call per tool call, free tier during the hackathon |

These numbers are close to 1.0 because the dataset is synthetic and deliberately clean-labeled — they demonstrate the pipeline is internally consistent (it doesn't cry wolf on the legitimate-retry/self-correction-recovery cases mixed into the same batch), not that it would score this well on messy real-world logs. See below for that check.

### Real-world validation set

To test on data we didn't design ourselves: `data/fetch_real_world_sample.py` pulls 30 real GPT-4o agent transcripts (15 genuinely failed, 15 genuinely succeeded, per its own task grader) from [tau-bench](https://github.com/sierra-research/tau-bench) (Sierra Research, MIT license) — a public benchmark of retail customer-service agent conversations, a different domain than ours with different tools and response shapes.

```bash
python data/fetch_real_world_sample.py       # downloads and converts the sample
python -m evaluation.run_real_world_evaluation
```

Result: **13% recall, 13% false-positive rate** against tau-bench's `reward` signal — much lower than the synthetic 1.00/1.00, for two honest reasons documented in `evaluation/results/real_world_metrics.json`: (1) the domain-specific parts of the LLM-judge heuristic (tuned for our supply-chain schema) don't transfer to retail's tool/response shapes without adaptation, and (2) `reward` measures task *completion*, not deception — several "failed" transcripts are the agent honestly telling the user it's stuck, which is a legitimate incomplete task, not a hidden failure, and our detector is correct to stay quiet on those. Investigating the false positives here also caught and fixed two real detector bugs (`ai/rules.py`'s silent-failure check wasn't looking past same-turn text; `ai/behavioral.py`'s frustration check was counting shared stopwords as repetition) — both fixed without any regression on the synthetic set.

## Disclosure

Most conversation data is **synthetic**, generated by `data/generate_conversations.py` to represent plausible SupplyzPro workflows with deliberately seeded failure patterns. A 30-conversation **real-world validation set** (`data/conversations_real_world.json`) comes from [tau-bench](https://github.com/sierra-research/tau-bench) (Sierra Research, MIT license), a public benchmark of real GPT-4o retail customer-service agent transcripts — used only to sanity-check the detector against data we didn't design, not fed into the main dashboard. AI tools used: an LLM-as-judge (NVIDIA NIM-hosted model, or an offline heuristic fallback) for hallucination/wrong-target detection, and TF-IDF/KMeans for unsupervised root-cause clustering. **NVIDIA Brev: not used** — no GPU compute was required for this project; the LLM-as-judge calls hosted inference (NIM) rather than running a model locally.

## Limitations and next steps

- **Uncertainty**: the LLM-as-judge (or its offline heuristic stand-in) gives a binary verdict per tool call, not a confidence score — a real deployment should surface confidence and let low-confidence verdicts fall back to human review.
- **Runtime**: end-to-end detection + clustering + prioritization over 60 conversations runs in under 2 seconds locally (see Evaluation above); this should scale roughly linearly with conversation count for the rule/behavioral layers, and linearly with tool-call count for the LLM-judge layer if it's calling a live API (each call adds hosted-inference latency, typically under 1s).
- **Processing cost**: $0 with the offline fallback judge; with a live NVIDIA NIM key, cost is one hosted inference call per tool call in the dataset — free tier during the hackathon, see build.nvidia.com pricing for sustained use.
- Runs on synthetic data. Applied to real conversation/tool-call logs, the LLM-as-judge rubric should be validated against a hand-labeled sample before trusting it at scale — real logs will have far messier language and ambiguous cases than our seeded scenarios.
- Severity and blast-radius weights are currently fixed; they should be tuned with input from the team that owns each workflow.
- The before/after comparison here is a simulated fix on a second synthetic batch — in production, a cluster's score would be tracked over time against the real system to verify a fix actually worked.
