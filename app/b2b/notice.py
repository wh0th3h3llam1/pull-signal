"""Seller notice drafting: Claude, Gemini Flash-Lite fallback. Drafts only; a human always sends."""
import time

import httpx
from pydantic import BaseModel

from .. import config, obs

DO_MODEL = "openai-gpt-oss-120b"
DO_PRODUCT = f"serverless-inference:{DO_MODEL}"


class NoticeOut(BaseModel):
    notice_text: str


def _platform_name(p: str | None) -> str:
    return {"ebay": "eBay", "amazon": "Amazon", "fb_marketplace": "Facebook Marketplace",
            "google_shopping": "Google Shopping"}.get(p or "", p or "the marketplace")


def build_prompt(c: dict) -> str:
    plat = _platform_name(c.get("platform"))
    seller = c.get("seller_name") or "Seller"
    return (
        f"You are writing on behalf of the {plat} Trust & Safety team. Draft a short, professional, neutral notice to a "
        f"seller about one of their listings. Rules:\n"
        f"- Do not accuse the seller of wrongdoing or bad intent. Say the listing \"appears to match\" the recalled product.\n"
        f"- Reference the U.S. CPSC recall number, the recall title, the hazard, the remedy, and the CPSC recall URL.\n"
        f"- Reference the listing title and listing URL.\n"
        f"- Ask the seller to remove the listing within 48 hours and to reply to confirm removal, or to reply with "
        f"information (e.g. model or lot number) showing the item is not covered by the recall.\n"
        f"- Include a subject line, a greeting, and a sign-off from \"{plat} Trust & Safety\". Plain text only, no markdown, "
        f"no placeholders in square brackets, under 230 words.\n\n"
        f"Seller: {seller}\n"
        f"Listing title: {c.get('listing_title') or ''}\n"
        f"Listing URL: {c.get('listing_url') or ''}\n"
        f"CPSC recall number: {c.get('recall_number') or ''}\n"
        f"Recall title: {c.get('recall_title') or ''}\n"
        f"Product: {c.get('product_name') or ''}\n"
        f"Hazard: {c.get('hazard') or ''}\n"
        f"Remedy: {c.get('remedy') or ''}\n"
        f"CPSC recall URL: {c.get('recall_url') or ''}\n"
        f"Match strength: {'high (confirmed match)' if c.get('severity') == 'CONFIRMED' else 'moderate (likely match)'}\n\n"
        f"Reply with the notice text only."
    )


async def _claude(prompt: str, case_id: str) -> tuple[str, int, str]:
    from .. import claude
    t0 = time.perf_counter()
    txt = (await claude.text(prompt, model=claude.MODEL_WRITE, max_tokens=900, purpose="b2b_notice")).strip()
    if not txt:
        raise ValueError("empty notice")
    return txt, int((time.perf_counter() - t0) * 1000), claude.MODEL_WRITE


async def draft(c: dict) -> dict:
    """-> {notice_text, model, latency_ms, fallback_error?}"""
    prompt = build_prompt(c)
    try:
        txt, ms, model = await _claude(prompt, c["case_id"])
        return {"notice_text": txt, "model": model, "provider": "anthropic", "latency_ms": ms}
    except Exception as e:
        err = str(e)[:300]
    from ..gemini.funnel import _gen
    from ..config import M_SCREEN
    data, ms = await _gen(M_SCREEN, "b2b_notice", prompt, NoticeOut, sample_extra={"case_id": c["case_id"],
                                                                                    "fallback_from": "claude"})
    return {"notice_text": (data.get("notice_text") or "").strip(), "model": M_SCREEN, "provider": "gemini",
            "latency_ms": ms, "fallback_error": err}
