"""Telem AI client: every live web search and page read in PullSignal goes through here.

search(query)  -> POST /v1/search with auto_routing; Telem picks the providers, we merge + dedupe their results.
fetch(urls)    -> POST /v1/fetch; clean page text per URL, Telem fails over across fetch providers.
Each call is logged to rh.api_calls (sponsor "telem") with the providers Telem chose and its session id.
"""
import time

import httpx

from . import obs
from .config import env

BASE = env("TELEM_BASE_URL", "https://hack.telem.ai/api").rstrip("/")
KEY = env("TELEM_API_KEY", "")


def _h() -> dict:
    return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def enabled() -> bool:
    return bool(KEY)


async def search(query: str, num: int = 8, routing: str = "accuracy", include: list[str] | None = None,
                 purpose: str = "search", timeout: float = 45) -> dict:
    """Returns {"results": [{url,title,summary,providers,rank}], "routing": [...], "session_id", "ms"}."""
    s: dict = {"auto_routing": routing, "num_results": num}
    if include:
        s = {"providers": {"include": include}, "num_results": num}
    t0 = time.perf_counter()
    st, out = "error", {"results": [], "routing": [], "session_id": None, "providers": [], "ms": 0}
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(f"{BASE}/v1/search", headers=_h(), json={"user_input": {"query": query}, "search": s})
        st = str(r.status_code)
        r.raise_for_status()
        j = r.json()
        merged: dict[str, dict] = {}
        used = []
        for run in j.get("preprocessor_runs") or []:
            prov = run.get("preprocessor_name")
            res = ((run.get("output_payload") or {}).get("results")) or []
            if run.get("status") == "succeeded":
                used.append({"provider": prov, "n": len(res), "ms": run.get("latency_ms")})
            for x in res:
                u = (x.get("url") or "").strip()
                if not u:
                    continue
                m = merged.setdefault(u, {"url": u, "title": x.get("title"), "summary": x.get("summary") or "",
                                          "providers": [], "rank": x.get("rank") or 99})
                m["providers"].append(prov)
                m["title"] = m["title"] or x.get("title")
                if len(x.get("summary") or "") > len(m["summary"]):
                    m["summary"] = x["summary"]
                m["rank"] = min(m["rank"], x.get("rank") or 99)
        # consensus ranking: URLs several independent indexes agree on come first
        results = sorted(merged.values(), key=lambda m: (-len(m["providers"]), m["rank"]))
        out = {"results": results, "routing": j.get("routing") or [], "session_id": j.get("session_id"),
               "providers": used}
        return out
    except Exception as e:
        out["error"] = str(e)[:200]
        return out
    finally:
        out["ms"] = int((time.perf_counter() - t0) * 1000)
        obs.log_call("telem", "search", f"v1/search:{purpose}", st, out["ms"], len(out["results"]), 0.0,
                     {"query": query[:160], "routing": out.get("routing"),
                      "providers": [p["provider"] for p in out.get("providers") or []],
                      "session_id": out.get("session_id")})


async def fetch(urls: list[str], purpose: str = "fetch", timeout: float = 40) -> dict[str, dict]:
    """Returns {url: {"ok": bool, "text": str, "title": str|None, "provider": str|None, "error": str|None}}."""
    urls = [u for u in urls if u][:10]
    if not urls:
        return {}
    t0 = time.perf_counter()
    st, docs, sid = "error", {}, None
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(f"{BASE}/v1/fetch", headers=_h(), json={"urls": urls, "options": {"tier": "default"}})
        st = str(r.status_code)
        r.raise_for_status()
        j = r.json()
        sid = j.get("session_id")
        for run in j.get("preprocessor_runs") or []:
            for d in ((run.get("output_payload") or {}).get("fetched_results")) or []:
                u = d.get("url") or d.get("requested_url") or (urls[0] if len(urls) == 1 else None)
                if not u:
                    continue
                text = d.get("content") or d.get("text") or d.get("markdown") or ""
                ok = bool(text) and not d.get("error") and d.get("status") not in ("failed", "error")
                docs[u] = {"ok": ok, "text": text, "title": d.get("title"),
                           "provider": d.get("provider") or d.get("provider_name"),
                           "error": d.get("error") or d.get("failure_reason"), "http_status": d.get("http_status")}
    except Exception as e:
        for u in urls:
            docs.setdefault(u, {"ok": False, "text": "", "title": None, "provider": None, "error": str(e)[:200]})
    finally:
        obs.log_call("telem", "fetch", f"v1/fetch:{purpose}", st, int((time.perf_counter() - t0) * 1000),
                     sum(1 for d in docs.values() if d.get("ok")), 0.0,
                     {"urls": [u[:120] for u in urls], "session_id": sid,
                      "providers": sorted({d.get("provider") for d in docs.values() if d.get("provider")})})
    return docs
