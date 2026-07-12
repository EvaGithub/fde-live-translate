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
import json
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

# The prompt is where translation quality lives. es-MX (the assignment's primary
# target) gets the rich "49-year Mexican translator" persona that pins the register
# (ustedes, not vosotros; carro/camioneta, not coche). Any other BCP-47 target gets
# a solid generic native-speaker prompt. Both forbid preamble/quotes and protect
# numbers, prices, and product codes.
LANGUAGE_NAMES = {
    "es-MX": "Mexican Spanish",
    "es": "Spanish",
    "es-ES": "Castilian Spanish",
    "pt-BR": "Brazilian Portuguese",
    "pt": "Portuguese",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "zh": "Chinese",
}


def _language_name(target: str) -> str:
    # Unknown codes fall back to the raw code, so any target still works.
    return LANGUAGE_NAMES.get(target, target)


def _register_rules(target: str) -> str:
    if target == "es-MX":
        return (
            'Use common Mexican vocabulary — for example "carro"/"camioneta" '
            'instead of the Castilian "coche", and "ustedes" instead of the '
            'Castilian "vosotros". '
        )
    return ""


def _system_prompt(target: str) -> str:
    lang = _language_name(target)
    return (
        f"Act as a native {lang} speaker who has translated English into {lang} "
        f"professionally for 49 years. {_register_rules(target)}Output ONLY the "
        'translation: no commentary like "here is the translation", and no wrapping '
        "quotes. Leave numerical identifiers — numbers, prices, and product codes — "
        "untouched."
    )


async def translate_text(text: str, target: str = "es-MX", model: str = MODEL_DEFAULT) -> str:
    """Return `text` translated into `target` (Mexican Spanish by default)."""
    msg = await _get_client().messages.create(
        model=model,
        max_tokens=1024,
        # Translation needs no reasoning. Turning thinking off keeps latency and
        # token cost down — important for the cache-miss latency SLA.
        thinking={"type": "disabled"},
        system=_system_prompt(target),
        messages=[{"role": "user", "content": text}],
    )
    # Pull the text block out defensively rather than assuming content[0].
    return next(block.text for block in msg.content if block.type == "text").strip()


# For whole-page translation the widget sends up to 40 strings per /translate/batch
# call. Translating them ONE PER LLM CALL is both slow (sequential round-trips) and
# rate-limit-bound (one API request per string). Instead we translate a whole batch
# in a SINGLE call: send a JSON array in, get a JSON array of the same length back.
# That is ~40× fewer API calls, stays well under the requests-per-minute limit, and
# turns a page from "over an hour" into "seconds".
def _batch_system_prompt(target: str) -> str:
    lang = _language_name(target)
    return (
        f"Act as a native {lang} speaker who has translated English into {lang} "
        f"professionally for 49 years. {_register_rules(target)}Leave numerical "
        "identifiers — numbers, prices, and product codes — untouched. Your input is "
        "a JSON array of English strings. Return ONLY a JSON array of the SAME "
        f"length, in the SAME order, where each element is the {lang} translation of "
        "the string at that position. No commentary, no markdown, no code fences — "
        "just the raw JSON array."
    )


def _strip_code_fences(s: str) -> str:
    """Some models wrap JSON in ```json … ``` fences; peel them off if present."""
    s = s.strip()
    if s.startswith("```"):
        s = s[s.find("\n") + 1 :] if "\n" in s else s[3:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


async def translate_batch_text(
    texts: list[str], target: str = "es-MX", model: str = MODEL_DEFAULT
) -> list[str]:
    """Translate a list of strings in a SINGLE LLM call; returns a same-length list.

    Raises if the model returns the wrong number of items so the caller can fall
    back to per-string translation rather than misaligning the page.
    """
    if not texts:
        return []
    payload = json.dumps(list(texts), ensure_ascii=False)
    msg = await _get_client().messages.create(
        model=model,
        # ~40 strings of translated text can be long; give it generous headroom.
        max_tokens=8192,
        thinking={"type": "disabled"},
        system=_batch_system_prompt(target),
        messages=[{"role": "user", "content": payload}],
    )
    raw = next(block.text for block in msg.content if block.type == "text").strip()
    translations = json.loads(_strip_code_fences(raw))
    if not isinstance(translations, list) or len(translations) != len(texts):
        got = len(translations) if isinstance(translations, list) else "non-list"
        raise ValueError(f"batch translation count mismatch: got {got} for {len(texts)} inputs")
    return [str(t) for t in translations]
