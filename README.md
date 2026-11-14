# PullSignal

**A product was recalled, and it's still for sale.** PullSignal finds recalled products listed across marketplaces, proves each match, and warns shoppers before they buy. **Telem AI** is the search layer.

**Live:** https://pullsignal.onrender.com (console) · https://pullsignal.onrender.com/landing.html (landing page). Hosted on Render (`render.yaml`).

| | Who | What |
|---|---|---|
| **Trust & Safety console** (`web/`) | Marketplaces, brands, regulators (B2B) | Pick a CPSC recall and press HUNT. PullSignal finds live listings, verifies them, opens a case per listing, drafts a takedown notice for a human to send, and re-checks that the listing came down |
| **PullSignal Guard** (`extension/`) | Shoppers (B2C) | A Chrome/Firefox extension that tags recalled products **while you scroll** Amazon, eBay, Walmart, Target or any schema.org store, and suggests safer alternatives |

Why it matters: about **6%** of consumers act on a recall notice, and CPSC sends takedown requests to resale sites by hand. Sources are in `RECALL_HUNTER_SPEC.md`.

## How a hunt works
1. **Plan (text + photo).** Claude (`claude-haiku-5-5`) writes the search strings a reseller would type. Recall words sellers never use ("recalled", "notice") are stripped. In parallel, Gemini looks at the **official recall photo** and writes look-based queries ("pink infant rocking sleeper bassinet") for sellers who don't know the brand.
2. **Search (Telem).** Each query becomes 5 marketplace-angled searches (`for sale`, OfferUp, eBay, Mercari, FB Marketplace). **Telem auto-routes** each one to the engines that answer it best (Exa, Tavily, Brave, Parallel, you.com, Ceramic, Seltz). Results are merged and deduplicated into unique listings.
3. **Consensus fetch (Telem).** Listings that 2+ independent engines returned are fetched first, through **Telem fetch** as clean page text, with a cap of 24 fetches per hunt and 6 slots kept for listings that only the photo queries found. Each hunt logs its funnel (raw hits → unique listings → consensus → fetched). Example run: 872 hits → 102 listings → 11 consensus → 24 fetched.
4. **Verify (Gemini).** A three-tier funnel: text screen → listing photo vs recall photo (with a label bounding box) → careful ruling. Only CONFIRMED / LIKELY matches become cases.
5. **Act.** Claude (`claude-sonnet-5-5`) drafts the seller notice; **nothing is sent automatically**. VERIFY re-reads the listing through Telem fetch to prove it came down.

## Run locally
```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
.venv/Scripts/python -m app.ingest            # pull CPSC recalls into Postgres
PYTHONPATH=. .venv/Scripts/python -m uvicorn app.main:app --port 8001
# open http://localhost:8001 → pick a recall → HUNT
```
Env (`.env`, gitignored): `TIGER_DATABASE_URL, TELEM_API_KEY, TELEM_BASE_URL, ANTHROPIC_API_KEY, GEMINI_API_KEY, GEMINI_FORCE_MODEL`, optional `TAVILY_API_KEY, SENTRY_DSN`.

Extension: `cd extension && npm install && npm run build`, then load `extension/dist-chrome` (**PullSignal Guard**, uses the Render API) or `extension/dist-chrome-local` (**PullSignal Guard Local**, uses `localhost:8001`).

## API
- `POST /api/hunt/{recall_id}` + `GET /api/hunt/{run_id}/events`: start a hunt and stream its events (QUERY, PHOTO, ROUTE, CONSENSUS, SCREEN, VISION, VERDICT).
- `GET /api/stats`: totals, including `telem` (calls, providers, p50 latency, listings found, flagged, `efficiency`).
- `POST /v2/match`: up to 40 store cards → `clean | possible | recalled`. Stage 1 runs on Postgres only (BM25 + brand/model rules), **about 300 ms for 40 cards**; Stage 2 (Gemini) confirms candidates in the background.
- `GET /v2/alternatives`: safer alternatives from Telem search, filtered against the recall index, cached for 24 h.
- `/b2b/*`: platforms, sellers, cases (open → notified → removed → verified), SLA, CSV report.

## Deploy
`render.yaml` is a Render Blueprint: one Docker web service (`Dockerfile` builds the console and serves the API on `$PORT`), health check `/api/health`, auto-deploy on push to `main`. Secrets are `sync: false` and entered in the Render dashboard.

## What each service does
| Service | Used for |
|---|---|
| **Telem AI** | All live search and page reading: routed search for the hunt and for alternatives, fetch for listing pages and takedown checks. Every call is logged with its routing and providers (Proof drawer, `rh.api_calls`) |
| **Claude** | Search planning (`claude-haiku-5-5`) and takedown notice drafts (`claude-sonnet-5-5`) |
| **Gemini** | Photo-based query planning, the three-tier verification funnel, image and text embeddings |
| **Postgres / Tiger Data** | Recalls, listings, verdicts, cases, API call log; BM25 and vector search for the recall index |
| **Sentry** | Tracing, with a span per hunt stage |
| **Bright Data** | Earlier hackathon only. Data gathered then is replayed from cache and labelled "cached"; no live calls |

## Honesty rules
- Nothing in the product path is mocked. Cached data is labelled as cached.
- The **Proof** drawer shows the last real call per service, straight from `rh.api_calls`.
- Verdicts are machine-generated leads, not legal findings. A product is only tagged RECALLED with CPSC evidence, and a human sends every notice.
