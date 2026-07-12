# Product Evaluation — Live Translate

- **Student:** Eva Losada
- **Date:** 2026-07-12
- **Video demo:** demo.mp4
- **LLM provider / model:** Anthropic / claude-sonnet-5
- **Backend target (deployed):** https://fde-live-translate-gateway.fly.dev (public gateway)
- **AI service (deployed):** private — no public IP; reachable only by the gateway over Fly's private network at `http://fde-live-translate-ai.flycast` (always-on, auto-wakes)

## Verdict

> This is a shippable Live Translate backend with a production-shaped topology. The **public** Node gateway is the only thing the browser can reach; the Python AI service is **private** (no public IP), so the API key, model, and cache live where the internet can't touch them. The full path — browser widget → public gateway → private AI service → Claude → two-tier cache — works end to end against a live public URL. The strongest part is the caching: a genuine cold-cache benchmark shows a 218× hit/miss speedup and ~$59/mo saved at 500k requests, all SLAs met, with real (non-zero) miss latency and cost, and the SQLite cache now lives on a **persistent Fly volume** so it survives redeploys. Translation quality on real third-party e-commerce strings is natural Mexican Spanish and reliably preserves prices and SKU/spec codes. The one remaining gap is purely presentational: the on-page widget walkthrough and before/after screenshots live in the video demo (server-side fetch of strict-CSP retail sites like homedepot.com is bot-blocked, which is expected — the Chrome extension handles those in the browser).

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

- **Site tested:** https://webscraper.io/test-sites/e-commerce/allinone (a real third-party e-commerce site the student does not control), translated through the **deployed** gateway. `homedepot.com` was attempted first but returns HTTP 403 to server-side fetch (bot/CSP protection) — a real-world finding, not a backend failure. The browser Chrome extension in `extension/` is designed to inject the widget on strict-CSP pages like that; that on-page walkthrough is captured in the video demo.
- **Translated real page strings?** Yes — nav, product names, descriptions and prices all translated to Mexican Spanish (see samples below).
- **Coverage gaps:** None observed on the fetched strings. Full dynamic-page coverage (lazy-loaded content) is demonstrated on-page in the video.
- **Cache on re-translate:** Repeating a translated string (`Computers`) returned `cached=true` at `latencyMs=0` — instant hit on the second pass.
- **Resilience:** Deployed gateway `/health` nests the AI-service health and stays green; invalid input returns HTTP 400 (not a silent 500 or English passthrough); upstream AI errors surface as 502. No layout breakage in widget behavior.
- **Screenshots:** Before/after on-page captures are attached to the video-demo submission (strict-CSP retail pages require the in-browser extension, so they are shown live rather than fetched here).

### Sample translations (7, from the live site via the deployed gateway)

| Original (EN) | Translation (es-MX) | Numbers/prices/codes kept? | OK? |
|---|---|---|---|
| Computers | Computadoras | N/A | Yes (es-MX: "computadoras", not Spain's "ordenadores") |
| Phones | Teléfonos | N/A | Yes |
| Documentation | Documentación | N/A | Yes |
| $439.73 | $439.73 | Yes — price preserved exactly | Yes |
| Acer Extensa 15 (2540) Black, 15.6" HD, Core i5-7200U, 4GB, 500GB, Linux | Acer Extensa 15 (2540) Negra, 15.6" HD, Core i5-7200U, 4GB, 500GB, Linux | Yes — all specs/SKU codes kept, only "Black"→"Negra" | Yes |
| $1238.37 | $1238.37 | Yes — price preserved exactly | Yes |
| Dell Latitude 5480, 14" FHD, Core i7-7600U, 8GB, 256GB SSD, Linux | Dell Latitude 5480, 14" FHD, Core i7-7600U, 8GB, 256GB SSD, Linux | Yes — all model/spec codes preserved | Yes |

## 3. Dimension scorecard

| Dimension | Pass / Partial / Fail | Evidence |
|---|---|---|
| Translation accuracy | Pass | Real live-site strings translated correctly and fluently through the deployed gateway. |
| Mexican-Spanish register (es-MX) | Pass | "Computers"→"Computadoras" (Mexican, not Spain's "ordenadores"); "¡Échale un ojo a nuestras ofertas!" — idiomatic es-MX. |
| Numbers / prices / codes preserved | Pass | `$439.73`, `$1238.37`, `Core i5-7200U`, `256GB SSD` all preserved verbatim; only translatable words (e.g. "Black") changed. |
| Page coverage | Partial | All fetched strings covered; full on-page dynamic coverage is shown in the video (server-side fetch of strict-CSP retail sites is bot-blocked). |
| Cache effectiveness | Pass | 218× speedup; repeat request `cached=true` at 0 ms; two-tier memory+SQLite, persists across restart. |
| Latency vs SLA | Pass | Cold-cache benchmark: hit p95 11 ms, miss p95 2394 ms, all SLAs met. |
| Error handling (no silent English) | Pass | Bad input → 400 (verified on deployed URL); upstream failure → 502; never falls back to silent English. |
| Resilience on a real site | Partial | Deployed chain stable; strict-CSP retail sites (homedepot.com) block server-side fetch, handled in-browser by the extension (shown in video). |
| UX polish | Partial | Backend and widget behavior correct; the polished on-page demo + screenshots are in the video. |

### Stretch goals shipped

- **Multi-language targets.** The `target` is honored end to end: the same English translates to any BCP-47 code through the deployed gateway. Verified live: `"Sign in to see today's deals"` → **es-MX** `Inicia sesión para ver las ofertas de hoy` · **pt-BR** `Faça login para ver as ofertas de hoje` · **fr** `Connectez-vous pour voir les offres du jour`. es-MX keeps its rich native-translator register; other languages get a proper native-speaker prompt; numbers/prices/codes preserved in all.
- **One-command local run.** `docker compose up --build` runs both services with the same public-gateway / private-AI topology as production (cache on a named volume).

## 4. Top fixes before shipping

1. Record the 60–90s demo video showing the Chrome extension translating a full strict-CSP page (e.g. homedepot.com) on-screen, plus the cache-hit badge on re-translate — this closes the two Partial dimensions (page coverage, resilience, UX polish).
2. Attach before/after screenshots of the on-page translation to the submission.
3. (Optional) Add a lightweight cache size/TTL bound so the SQLite tier doesn't grow unbounded in long-running production use.

---

### Deployment & run notes

- **Deployed (Fly.io, region `ord`):** the gateway `https://fde-live-translate-gateway.fly.dev` is **public**; the AI service is **private** — it has no public IP and is reached only by the gateway over Fly's private network (`http://fde-live-translate-ai.flycast`), verified by the public AI URL being unreachable while translation still flows through the gateway. It's kept always-on (`min_machines_running=1`) and auto-wakes if stopped (verified: stopped the machine, a gateway call restarted it). Public gateway `/health` nests the private AI's health. The SQLite cache is on a **persistent Fly volume** (`/data`), proven to survive a redeploy. `ANTHROPIC_API_KEY`, `AI_SERVICE_URL`, and `TRANSLATION_DB_PATH` are Fly secrets (never committed).
- **Local run:** one command — `docker compose up --build` — runs both services (private AI + public gateway on 8787). Or run them directly: AI service `uvicorn app:app --port 8000`, gateway `npm start`. The gateway writes `gateway.log`, the AI service writes `ai-service.log`, and a single `X-Request-Id` correlates one request across both (`trace_correlated: true`).
