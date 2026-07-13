# Product Evaluation — Live Translate

- **Student:** Eva Losada
- **Date:** 2026-07-14
- **Video demo:** demo.mp4 — full-page on-page walkthrough on `theblogstarter.com/about-me`
- **LLM provider / model:** Anthropic Claude — `claude-sonnet-5`
- **Backend target:** rubric + benchmark run against local (`http://localhost:8787` gateway → private AI service `:8000`); **public deploy verified live** at `https://fde-live-translate-gateway.fly.dev` (auto-checked, `deploy_health_ok: true`).

## Verdict

> This is a genuinely shippable Live Translate backend with a production-shaped topology: a public Node gateway is the only internet-facing surface, and the Python AI service, API key, model, and two-tier cache sit behind it privately. Run end-to-end against real third-party content, it performs well — natural **Mexican Spanish** (idiomatic `recámara`, `plomero`, `Haz ejercicio`), every number/price/unit preserved, a genuine cold-cache benchmark showing a **322× hit/miss speedup** and **~$59.79/mo saved** at 500k requests, 0 errors, all SLAs met, and request-ID tracing that is greppable end-to-end across both services. Both services are **deployed and live on Fly.io** — the public gateway `/health` nests the private AI service, and a real translate through the public URL preserves numbers and prices in es-MX. The machines auto-stop when idle and auto-wake on first request (~3-5s cold start), so the deploy runs cost-efficiently while staying reachable. Submission-ready across every dimension.

**Rubric score (from `eval/report.json`):** 70 / 70 auto (+ 30 manual)

## 1. Performance & cost (from `benchmark/bench.py`, genuine cold-cache run)

| Metric | Result | SLA | Pass? |
|---|---|---|---|
| Cache hit p95 | 10.5 ms | ≤ 60 ms | ✅ |
| Cache miss p95 | 3375.7 ms | ≤ 3500 ms | ✅ |
| Cache hit rate | 75.0 % | ≥ 60 % | ✅ |
| Throughput | 1499.8 req/s | ≥ 20 | ✅ |
| Error rate | 0.0 % | ≤ 1 % | ✅ |
| Cost per miss | $0.0001594 | — | — |
| Monthly savings from cache | $59.79 | — | — |

`python benchmark/bench.py` exits `0` — **all SLAs met**. Numbers are from a genuine cold run against an **empty** cache on 2026-07-14 (miss p95 3.4s is a real LLM call; hit p95 10.5ms is served from the two-tier cache → **322×** speedup). Cost is modeled at 500k req/mo: **$79.72 uncached → $19.93 cached**. Raw output in `benchmark/_bench.json`.

## 2. Live-website test

The primary demonstration is the **on-page video demo** (`demo.mp4`) on a real third-party site the student does not control. So the translations are independently checkable in this document, the same page's strings were also re-run live through the public gateway (raw request/response saved to `eval/aboutme_live_test.json`).

- **On-page video demo — `theblogstarter.com/about-me`:** `demo.mp4` loads the widget via the Chrome extension (pointed at the public Fly.io gateway) and does **full-page one-click Translate → Restore** on this live page. The whole page — heading, nav, body, sidebar, and comments — flips to Mexican Spanish; the on-screen badge reports **67 chunks · 8 cache hits · ~16.8 s**. This is the primary live, on-page demonstration.
- **Same page verified through the live gateway:** 8 representative strings from `theblogstarter.com/about-me` were sent through the live public gateway (`POST /translate/batch`, `target: es-MX`) on 2026-07-14; **all 8 returned correct es-MX** (table below), server `latencyMs 3964` on the uncached strings.
- **Cache on re-translate:** re-sending the identical strings returned **all 8 `cached: true`** with server `latencyMs 0` — the second call did zero LLM work, matching the cache-hit badge shown in the video.
- **Coverage:** Full-page coverage (heading, nav, body, sidebar) is shown on-screen in the video; no gaps or swallowed English. On strict-CSP sites the Chrome extension is required for in-page translation (console injection is blocked by CSP — a browser limitation, not a backend fault).
- **Resilience:** Clean — 0 errors, layout intact, correct response shape, no untranslated fallback. The widget was hardened this session to resolve the backend URL lazily (avoids a config race when injected as a content script).

### Sample translations (live `theblogstarter.com/about-me` content)

| Original (EN) | Translation (es-MX) | Numbers/symbols kept? | OK? |
|---|---|---|---|
| My name is Scott Chow, and I wrote the easiest guide to starting a blog, so that you can start your blog today! | Me llamo Scott Chow, y escribí la guía más fácil para empezar un blog, ¡para que puedas comenzar tu blog hoy mismo! | — | ✅ |
| Technology keeps changing at a rapid pace. | La tecnología sigue cambiando a un ritmo acelerado. | — | ✅ |
| When thinking about what to call the website, I decided that my nickname would work great. | Cuando estaba pensando en cómo llamarle al sitio web, decidí que mi apodo quedaría muy bien. | — | ✅ |
| If you want to see more from me, follow me on Facebook, Twitter and Pinterest. | Si quieres ver más contenido mío, sígueme en Facebook, Twitter y Pinterest. | — | ✅ |
| Recent comments from The Blog Starter users | Comentarios recientes de los usuarios de The Blog Starter | — | ✅ |
| Helping start blogs since 2002. | Ayudando a iniciar blogs desde 2002. | ✅ 2002 | ✅ |
| Steps for building your blog | Pasos para construir tu blog | — | ✅ |
| Copyright © 2026. The Blog Starter. All rights reserved. | Derechos de autor © 2026. The Blog Starter. Todos los derechos reservados. | ✅ © · 2026 | ✅ |

Register is unmistakably **Mexican** (`Me llamo`, informal `puedas`/`quieres`/`sígueme`, `apodo`), translation-only with no preamble or wrapping quotes.

**Price / number / unit preservation** (verified live through the public gateway):

| Original (EN) | Translation (es-MX) | Kept verbatim |
|---|---|---|
| Supplements cost about $47 per month. | Los suplementos cuestan alrededor de $47 al mes. | ✅ `$47` |
| The premium plan is $12.99/month — save 20% with the annual plan. | El plan premium cuesta $12.99/mes — ahorra 20% con el plan anual. | ✅ `$12.99` · `20%` |
| Package weight: 2.5 kg (5.5 lb), dimensions 30×20×10 cm. | Peso del paquete: 2.5 kg (5.5 lb), dimensiones 30×20×10 cm. | ✅ `2.5 kg` · `5.5 lb` · `30×20×10 cm` |

Also confirmed on the deploy with `$129.99` (see the Deployment row below).

## 3. Dimension scorecard

| Dimension | Pass / Partial / Fail | Evidence |
|---|---|---|
| Translation accuracy | Pass | 8/8 live `theblogstarter.com/about-me` strings fluent and faithful; full-page translate shown in the video. |
| Mexican-Spanish register (es-MX) | Pass | `Me llamo`, informal `puedas`/`quieres`/`sígueme`, `apodo` — not Castilian/generic. |
| Numbers / symbols preserved | Pass | `2002`, `© 2026` (about-me page) plus `$47` and `$129.99` (live gateway) all preserved verbatim. |
| Page coverage | Pass | Full-page translate/restore on `theblogstarter.com/about-me` shown on-screen in the video (67 chunks: heading, nav, body, sidebar, comments); widget walks the whole page via `createTreeWalker(document.body, SHOW_TEXT)` (`translation-widget.js`). |
| Cache effectiveness | Pass | 322× cold benchmark (10.5 ms hit p95 vs 3375.7 ms miss p95); video shows the cache-hit badge, and the live re-run of the same page returned all `cached: true` at `latencyMs 0`; SQLite survives restart. |
| Latency vs SLA | Pass | Every SLA in `sla.json` met; `bench.py` exits 0. |
| Error handling (no silent English) | Pass | `lib/llm.py` fails loud (no untranslated-fallback); bad input → 400 (auto-verified). |
| Resilience on a real site | Pass | 0 errors on live content; extension injects on strict-CSP sites; widget URL-race fixed. |
| UX polish | Pass | One-click translate/restore, cache-hit badge; backend hint now refreshes on panel open. |
| Deployment (Fly.io public URL) | Pass | Both services live on Fly.io; public gateway `/health` nests AI; live translate via public URL → `El taladro sin cable cuesta $129.99 en el pasillo 7.` ($129.99 preserved, es-MX). `deploy_health_ok: true`. |

Also verified this session: **trace correlation** — an injected `X-Request-Id` (`eval-trace-4576aa`) appeared in **both** the gateway log (`POST /translate 200 1941ms`) and the AI-service log (`request_id`), greppable end-to-end. No secrets, `*.db`, or `*.log` are tracked in git.

## 4. Top fixes before shipping

No blocking gaps — all dimensions Pass. Minor notes:

1. **First-request cold start (~3-5s).** Fly machines auto-stop when idle to save cost; the first translate after a quiet period cold-starts them. Acceptable for grading; if a warm demo matters, set `min_machines_running: 1` on the gateway.
2. **Extension backend URL.** The extension's saved backend URL is set to the public gateway (`https://fde-live-translate-gateway.fly.dev`) — confirm this before any future demo so the on-page test exercises the deploy rather than localhost.
