"""
lib/llm.py — the LLM translation call
=====================================
One job: turn an English string into Mexican Spanish using an LLM.

Provider is Anthropic Claude (`pip install anthropic`, set ANTHROPIC_API_KEY).
To swap providers, change the client + call here; nothing else in the app cares.

FAIL LOUD: this function does NOT catch provider errors. If the call fails, the
exception propagates so the caller (app.py) returns a 502. Silently returning the
untranslated English is an automatic fail on this assignment.
"""
import os

from anthropic import AsyncAnthropic

MODEL_DEFAULT = os.getenv("MODEL", "claude-sonnet-5")

# One shared async client, created lazily on first use and reused thereafter.
# Lazy init matters: if we built the client at import time, it would run BEFORE
# app.py's load_dotenv() populated ANTHROPIC_API_KEY — so the client would have
# no key. By the time translate_text() is first called (a real request), the
# env is loaded. Reusing one client keeps a warm connection pool.
_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from the environment
    return _client

# The prompt is where translation quality lives. It pins the register to Mexican
# Spanish (ustedes, not vosotros; carro/camioneta, not coche), forbids preamble
# and quotes, and protects numbers, prices, and product codes.
SYSTEM_PROMPT = (
    "Act as a native Mexican Spanish speaker who has translated English into "
    "Mexican Spanish professionally for 49 years. Use common Mexican vocabulary — "
    'for example "carro"/"camioneta" instead of the Castilian "coche", and '
    '"ustedes" instead of the Castilian "vosotros". Output ONLY the translation: '
    'no commentary like "here is the translation", and no wrapping quotes. Leave '
    "numerical identifiers — numbers, prices, and product codes — untouched."
)


async def translate_text(text: str, target: str = "es-MX", model: str = MODEL_DEFAULT) -> str:
    """Return `text` translated into `target` (Mexican Spanish by default)."""
    msg = await _get_client().messages.create(
        model=model,
        max_tokens=1024,
        # Translation needs no reasoning. Turning thinking off keeps latency and
        # token cost down — important for the cache-miss latency SLA.
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    # Pull the text block out defensively rather than assuming content[0].
    return next(block.text for block in msg.content if block.type == "text").strip()
