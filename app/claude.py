"""Claude helper: search planning and seller-notice drafting. Logged to rh.api_calls (sponsor "anthropic")."""
import json
import time

from anthropic import AsyncAnthropic

from . import obs
from .config import env

KEY = env("ANTHROPIC_API_KEY", "")
MODEL_FAST = env("CLAUDE_FAST_MODEL", "claude-haiku-5-5")
MODEL_WRITE = env("CLAUDE_WRITE_MODEL", "claude-sonnet-5-5")
_client: AsyncAnthropic | None = None


def enabled() -> bool:
    return bool(KEY)


def _c() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=KEY, timeout=60, max_retries=1)
    return _client


async def text(prompt: str, model: str | None = None, max_tokens: int = 1200, purpose: str = "text") -> str:
    model = model or MODEL_FAST
    t0 = time.perf_counter()
    st, out, usage = "error", "", {}
    try:
        r = await _c().messages.create(model=model, max_tokens=max_tokens,
                                       messages=[{"role": "user", "content": prompt}])
        out = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
        usage = {"in": r.usage.input_tokens, "out": r.usage.output_tokens}
        st = "200"
        return out
    except Exception as e:
        usage = {"error": str(e)[:200]}
        raise
    finally:
        obs.log_call("anthropic", model, purpose, st, int((time.perf_counter() - t0) * 1000), 1 if out else 0, 0.0,
                     usage)


async def json_out(prompt: str, model: str | None = None, max_tokens: int = 1200, purpose: str = "json") -> dict:
    txt = await text(prompt + "\n\nReply ONLY with one JSON object, no prose, no code fences.", model, max_tokens, purpose)
    return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
