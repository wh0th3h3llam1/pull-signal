# PullSignal — 2-minute SearchHack demo

**Run locally:** `PYTHONPATH=. .venv/Scripts/python -m uvicorn app.main:app --port 8001` → landing `http://localhost:8001/landing.html`, console `http://localhost:8001/`. Extension: load `extension/dist-chrome` (talks to `localhost:8001`).

| Time | Show | Say |
|---|---|---|
| 0:00 | Landing hero | "Every week the CPSC recalls about ten dangerous products. They keep selling online. Only 6% of people act on a recall." |
| 0:15 | Scroll to "Route the hunt" | "PullSignal finds them. The hard part is search: the same product is listed a hundred ways across a dozen marketplaces." |
| 0:25 | Console → Rock 'n Play recall → **HUNT** | "Claude writes the searches a reseller would type. Each one goes to **Telem**, which routes it to the engines that answer best: Exa, Tavily, Brave, Parallel, you.com." |
| 0:40 | Live log: **ROUTE** lines | "Here's the routing, live. We merge results from independent engines, and listings several engines agree on get read first, through Telem fetch, as clean text." |
| 0:55 | Results: OfferUp listings CONFIRMED | "Gemini verifies each listing against the recall. Six Rock 'n Play sleepers, recalled after infant deaths, for sale right now on OfferUp." |
| 1:10 | Open a case → **DRAFT NOTICE** → **VERIFY** | "Each match becomes a case. Claude drafts the notice, a human sends it, and Verify re-reads the page through Telem to prove it came down." |
| 1:25 | **PROOF** drawer | "Every Telem call, with the providers it chose, is logged and traceable in Telem's console." |
| 1:35 | Extension on Amazon Bodum search | "For shoppers, the extension tags recalled products while you scroll: 40 products in 300 ms from a local index, so we only hit the web when needed." |
| 1:50 | Landing CTA | "Marketplaces, brands and regulators pay for this. PullSignal." |
