# PullSignal — SearchHack submission

**Tagline:** Recalled products keep selling online. PullSignal finds them across every marketplace, proves it, and warns shoppers before they buy.

**Tracks:** Search routing · Agentic search (plan → search → verify → synthesize) · Efficient search · Multimodal search · Personalized search

## The problem
The U.S. CPSC recalls about 10 products a week: infant sleepers, magnets, French presses that shatter. Only about 6% of consumers act on a recall notice, and the products keep selling on OfferUp, eBay, Mercari, Facebook Marketplace and Amazon. Regulators send takedown requests by hand.

## What it does
1. **Hunt (B2B console).** Pick a recall and press HUNT. Claude plans the search strings a reseller would type. Each one becomes several marketplace-angled searches that **Telem routes** to the search engines that answer it best (Exa, Tavily, Brave, Parallel, you.com, Ceramic, Seltz). Results from independent engines are merged; listings that several engines agree on are read first, through **Telem fetch** as clean page text.
2. **Verify.** A Gemini funnel compares each listing against the recall (model, size, photo) and only CONFIRMED / LIKELY matches become cases. Out-of-scope models are rejected (e.g. Bodum 3-cup presses vs the recalled 8- and 12-cup).
3. **Act.** Each match becomes a case with evidence. Claude drafts the seller notice (a human always sends it). **VERIFY** re-reads the listing through Telem fetch to prove it came down.
4. **Shoppers (browser extension).** PullSignal Guard tags recalled products while you scroll Amazon, eBay, Walmart, Target. 40 products are checked in about 300 ms against a local BM25 + vector index, so the web is only touched when needed. Safer alternatives come from Telem search.

## Why it needs Telem
- One API, many search indexes, one result format: the hunt asks 5–10 angled queries per recall and Telem fans each out to ~7 providers. Building and maintaining that ourselves is weeks of work.
- **Consensus ranking**: a listing found by several independent engines is fetched first, which cuts wasted page reads.
- **Fetch with failover**: marketplace pages (OfferUp, eBay, Target) come back as clean text, which feeds the verifier directly.
- **Observability**: every search and fetch is a trace in Telem's console, and each call is also logged with its routing in our Proof drawer.

## Results (live run, 14 Nov 2026)
- Rock 'n Play Sleeper (recalled after infant deaths, CPSC #23088): the Telem hunt found **10 listings**, **6 confirmed** still for sale on OfferUp, several new since yesterday ($15–$70, AZ, WA, NC, CA, NV).
- Bodum 8-/12-cup French press: **24 candidates** across Amazon, Target, eBay, Mercari, OfferUp, FB Marketplace, Walmart → **7 confirmed, 11 likely, 6 rejected**.
- Across both hunts: 33 Telem calls, 34 listings found, 24 flagged.

## Stack
Telem AI (search routing + fetch) · Claude (search planning, notice drafting) · Gemini (verification funnel, embeddings) · Postgres/TimescaleDB with BM25 and vector search (recall index, evidence history) · FastAPI · React · MV3 extension. Data gathered earlier with Bright Data is replayed from cache and labelled as cached.

## Business
Customers: resale marketplaces (compliance + trust & safety), brands running a recall (measure recall effectiveness), regulators (online market surveillance). SaaS per monitored recall / catalog size; the consumer extension is free and is the funnel.
