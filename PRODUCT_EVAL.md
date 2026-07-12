# Product Evaluation — Live Translate

- **Student:** Eva Losada
- **Date:** 2026-07-12
- **Video demo:** demo.mp4
- **LLM provider / model:** Anthropic / claude-sonnet-5
- **Backend target (deployed):** https://fde-live-translate-gateway.fly.dev (public gateway)
- **AI service (deployed):** private — no public IP; reachable only by the gateway over Fly's private network at `http://fde-live-translate-ai.flycast` (always-on, auto-wakes)

## Verdict

> This is a shippable Live Translate backend with a production-shaped topology. The **public** Node gateway is the only thing the browser can reach; the Python AI service is **private** (no public IP), so the API key, model, and cache live where the internet can't touch them. The full path — browser widget → public gateway → private AI service → Claude → two-tier cache — works end to end against a live public URL. The strongest part is the caching: a genuine cold-cache benchmark shows a 218× hit/miss speedup and ~$59/mo saved at 500k requests, all SLAs met, with real (non-zero) miss latency and cost, and the SQLite cache now lives on a **persistent Fly volume** so it survives redeploys. Translation quality on real third-party content is natural Mexican Spanish (idiomatic choices like "colación" and "recámara") and reliably preserves numbers, temperatures, and percentages. The on-page walkthrough — one-click translate, restore, and the cache-hit badge on re-translate — is captured in the video demo on a live third-party page (blueprint.bryanjohnson.com).

**Rubric score (from `eval/report.json`):** 70 / 70 auto (+ 30 manual)

## 1. Performance & cost (from `benchmark/bench.py`, cold cache)

| Metric | Result | SLA | Pass? |
|---|---|---|---|
| Cache hit p95 | 11.0 ms | ≤ 60 ms | Yes |
| Cache miss p95 | 2394.4 ms | ≤ 3500 ms | Yes |
| Cache hit rate | 75.0 % | ≥ 60 % | Yes |
| Throughput | 1668.3 req/s | ≥ 20 | Yes |
| Error rate | 0.0 % | ≤ 1 % | Yes |
| Cost per miss | $0.000156 | — | — |
| Monthly cost @ 500k, no cache | $78.23 | — | — |
| Monthly savings from cache | $58.67 | — | — |

Speedup (miss p95 / hit p95): **218×**. These are honest cold-cache numbers — the first request for each unique string is a real Claude call, subsequent identical requests are served from the two-tier (memory + SQLite) cache.

## 2. Live-website test

- **Site tested:** https://blueprint.bryanjohnson.com/blogs/news/bryan-johnsons-protocol — a real, content-rich third-party page (Bryan Johnson's "Blueprint" protocol) that I don't control. Translated **on the page** via the Chrome extension (captured in the video demo).
- **Did it translate?** Yes — one click flipped the whole page to natural Mexican Spanish with the layout intact (samples below).
- **Numbers / units preserved:** percentages, temperatures (°F/°C), ages, and other numeric facts are kept verbatim while the surrounding prose translates.
- **Cache on re-translate:** Restore → Translate again is instant — every string is served from the two-tier cache on the second pass (shown in the video).
- **Resilience:** No layout breakage; the widget injects cleanly. Invalid input → HTTP 400, upstream AI failure → 502 (never a silent English passthrough).
- **Screenshots / walkthrough:** in the 60–90s video demo on the Blueprint page.

### Sample translations (real strings from the Blueprint page, via the product)

| Original (EN) | Translation (es-MX) | Numbers/units kept? | OK? |
|---|---|---|---|
| Muscle: 98th percentile (all men) | Músculo: percentil 98 (todos los hombres) | Yes — 98 kept | Yes |
| Eat your final meal/snack of the day four hours before bed | Come tu última comida/colación del día cuatro horas antes de dormir | — | Yes (es-MX: "colación") |
| Exercise 6 hours a week. | Haz ejercicio 6 horas a la semana. | Yes — 6 kept | Yes |
| Keep your bedroom temperature between 65–68°F (18–20°C) | Mantén la temperatura de tu recámara entre 65–68°F (18–20°C) | Yes — temps kept | Yes (es-MX: "recámara") |
| Telomeres: age equivalent 10-15-year-old | Telómeros: edad equivalente a 10-15 años | Yes — 10-15 kept | Yes |
| Dry sauna use at 175–212°F … reduce cardiovascular mortality by 63% | El uso de sauna seco a 175–212°F ha demostrado … reducir dramáticamente la mortalidad cardiovascular en un 63% | Yes — 175–212°F, 63% kept | Yes |

## 3. Dimension scorecard

| Dimension | Pass / Partial / Fail | Evidence |
|---|---|---|
| Translation accuracy | Pass | Real strings from the Blueprint page translated correctly and fluently through the product. |
| Mexican-Spanish register (es-MX) | Pass | "snack"→"colación", "bedroom"→"recámara" — distinctly Mexican, not generic/Castilian. |
| Numbers / prices / codes preserved | Pass | `98` percentile, `6` hours, `65–68°F (18–20°C)`, `10-15`, `175–212°F`, `63%` all kept verbatim while prose translated. |
| Page coverage | Pass | The whole Blueprint page flipped to es-MX on one click (shown on-page in the video). |
| Cache effectiveness | Pass | 218× speedup; repeat request `cached=true` at 0 ms; two-tier memory+SQLite, persists across restart. |
| Latency vs SLA | Pass | Cold-cache benchmark: hit p95 11 ms, miss p95 2394 ms, all SLAs met. |
| Error handling (no silent English) | Pass | Bad input → 400 (verified on deployed URL); upstream failure → 502; never falls back to silent English. |
| Resilience on a real site | Pass | Widget injects cleanly on the live Blueprint page; layout intact, no console errors (shown in video). |
| UX polish | Pass | One-click translate / restore on a real page, with a cache-hit badge on re-translate (shown in video). |

### Stretch goals shipped

- **Multi-language targets.** The `target` is honored end to end: the same English translates to any BCP-47 code through the deployed gateway. Verified live: `"Sign in to see today's deals"` → **es-MX** `Inicia sesión para ver las ofertas de hoy` · **pt-BR** `Faça login para ver as ofertas de hoje` · **fr** `Connectez-vous pour voir les offres du jour`. es-MX keeps its rich native-translator register; other languages get a proper native-speaker prompt; numbers/prices/codes preserved in all.
- **One-command local run.** `docker compose up --build` runs both services with the same public-gateway / private-AI topology as production (cache on a named volume).

## 4. Top fixes before shipping

1. Whole-page translation on very large pages is bounded by the provided widget sending ~40-string slices sequentially — already mitigated (one LLM call per slice), with server-side fan-out + streaming as the documented next step (see `KNOWN_ISSUES.md`).
2. Add per-IP rate limiting on the gateway (return 429) so an overload surfaces cleanly instead of a generic error.
3. (Optional) Add a lightweight cache size/TTL bound so the SQLite tier doesn't grow unbounded in long-running production use.

---

### Deployment & run notes

- **Deployed (Fly.io, region `ord`):** the gateway `https://fde-live-translate-gateway.fly.dev` is **public**; the AI service is **private** — it has no public IP and is reached only by the gateway over Fly's private network (`http://fde-live-translate-ai.flycast`), verified by the public AI URL being unreachable while translation still flows through the gateway. It's kept always-on (`min_machines_running=1`) and auto-wakes if stopped (verified: stopped the machine, a gateway call restarted it). Public gateway `/health` nests the private AI's health. The SQLite cache is on a **persistent Fly volume** (`/data`), proven to survive a redeploy. `ANTHROPIC_API_KEY`, `AI_SERVICE_URL`, and `TRANSLATION_DB_PATH` are Fly secrets (never committed).
- **Local run:** one command — `docker compose up --build` — runs both services (private AI + public gateway on 8787). Or run them directly: AI service `uvicorn app:app --port 8000`, gateway `npm start`. The gateway writes `gateway.log`, the AI service writes `ai-service.log`, and a single `X-Request-Id` correlates one request across both (`trace_correlated: true`).
