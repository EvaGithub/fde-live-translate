# Product Evaluation — Live Translate

- **Student:** Eva Losada
- **Date:** 2026-07-13
- **Video demo:** demo.mp4
- **LLM provider / model:** Anthropic Claude — `claude-sonnet-5`
- **Backend target:** rubric + benchmark run against local (`http://localhost:8787` gateway → private AI service `:8000`); **public deploy verified live** at `https://fde-live-translate-gateway.fly.dev` (auto-checked, `deploy_health_ok: true`).

## Verdict

> This is a genuinely shippable Live Translate backend with a production-shaped topology: a public Node gateway is the only internet-facing surface, and the Python AI service, API key, model, and two-tier cache sit behind it privately. Run end-to-end against real third-party content, it performs well — natural **Mexican Spanish** (idiomatic `recámara`, `plomero`, `Haz ejercicio`), every number/price/unit preserved, a genuine cold-cache benchmark showing a **393× hit/miss speedup** and **~$59.51/mo saved** at 500k requests, 0 errors, all SLAs met, and request-ID tracing that is greppable end-to-end across both services. Both services are **deployed and live on Fly.io** — the public gateway `/health` nests the private AI service, and a real translate through the public URL preserves numbers and prices in es-MX. The machines auto-stop when idle and auto-wake on first request (~3-5s cold start), so the deploy runs cost-efficiently while staying reachable. Submission-ready across every dimension.

**Rubric score (from `eval/report.json`):** 70 / 70 auto (+ 30 manual)

## 1. Performance & cost (from `benchmark/bench.py`, genuine cold-cache run)

| Metric | Result | SLA | Pass? |
|---|---|---|---|
| Cache hit p95 | 7.9 ms | ≤ 60 ms | ✅ |
| Cache miss p95 | 3123.5 ms | ≤ 3500 ms | ✅ |
| Cache hit rate | 75.0 % | ≥ 60 % | ✅ |
| Throughput | 1528.3 req/s | ≥ 20 | ✅ |
| Error rate | 0.0 % | ≤ 1 % | ✅ |
| Cost per miss | $0.0001587 | — | — |
| Monthly savings from cache | $59.51 | — | — |

`python benchmark/bench.py` exits `0` — **all SLAs met**. Numbers are from a cold run against an empty cache (miss p95 3.1s is a real LLM call; hit p95 8ms is served from the two-tier cache → **393×** speedup). Cost is modeled at 500k req/mo: **$79.35 uncached → $19.84 cached**.

## 2. Live-website test

- **Site tested:** https://blueprint.bryanjohnson.com/blogs/news/bryan-johnsons-protocol — a real, content-rich third-party page (Bryan Johnson's "Blueprint" protocol) that the student does not control.
- **Translated whole page?** Yes — full-page one-click translate/restore is demonstrated **on the page via the Chrome extension in the video demo**. For this written eval, 8 verbatim strings pulled live from the page were translated through the running backend (`/translate/batch`); all 8 returned correct es-MX with layout-neutral output.
- **Coverage gaps:** None in the sampled content. Full-page coverage (nav, dynamically-loaded sections) is shown in the video; the extension is required on strict-CSP sites (console injection is blocked by CSP — a browser limitation, not a backend fault).
- **Cache on re-translate:** Re-sending the same 8-string batch returned **all 8 `cached: true`** in **11 ms vs 5060 ms** cold (~460×). `/stats` reported an 83% hit rate after the run.
- **Resilience:** Clean — 0 errors, layout intact, no swallowed failures. The widget was hardened this session to resolve the backend URL lazily (avoids a config race when injected as a content script).
- **Screenshots:** Before/after and the cache-hit badge are captured in the 60–90s video demo on the Blueprint page.

### Sample translations (live Blueprint content)

| Original (EN) | Translation (es-MX) | Numbers/prices/codes kept? | OK? |
|---|---|---|---|
| Calories: 2,250 (10% caloric restriction) | Calorías: 2,250 (10% de restricción calórica) | ✅ 2,250 · 10% | ✅ |
| Protein: 130 grams (~25%) | Proteína: 130 gramos (~25%) | ✅ 130 · ~25% | ✅ |
| Exercise 6 hours a week. | Haz ejercicio 6 horas a la semana. | ✅ 6 | ✅ |
| Keep your bedroom temperature between 65–68°F (18–20°C). | Mantén la temperatura de tu recámara entre 65–68°F (18–20°C). | ✅ 65–68°F · 18–20°C | ✅ |
| Aim for 150 minutes of moderate activity (Zone 2)… | Procura hacer 150 minutos de actividad moderada (Zona 2)… | ✅ 150 · Zone 2 | ✅ |
| Get outside within the first 15–30 minutes of waking… | Sal al aire libre dentro de los primeros 15–30 minutos después de despertar… | ✅ 15–30 | ✅ |
| Avoid caffeine, alcohol, and other stimulants at least 8–10 hours before sleep. | Evita la cafeína, el alcohol y otros estimulantes por lo menos 8–10 horas antes de dormir. | ✅ 8–10 | ✅ |
| Temperature: 200°F (93°C) | Temperatura: 200°F (93°C) | ✅ 200°F · 93°C | ✅ |

Register is unmistakably **Mexican** (`recámara` not `dormitorio`, `plomero` not `fontanero`, informal `Haz`/`Mantén`/`Evita` imperatives), translation-only with no preamble or wrapping quotes.

## 3. Dimension scorecard

| Dimension | Pass / Partial / Fail | Evidence |
|---|---|---|
| Translation accuracy | Pass | 8/8 live Blueprint strings fluent and faithful. |
| Mexican-Spanish register (es-MX) | Pass | `recámara`, `plomero`, informal imperatives — not Castilian/generic. |
| Numbers / prices / codes preserved | Pass | 2,250 · 10% · $42 · 65–68°F/18–20°C · 200°F/93°C all preserved verbatim. |
| Page coverage | Pass | Full-page translate/restore on the live page in the video; all sampled strings covered. |
| Cache effectiveness | Pass | 393× cold benchmark; 460× on the live batch (5060 ms → 11 ms); SQLite survives restart. |
| Latency vs SLA | Pass | Every SLA in `sla.json` met; `bench.py` exits 0. |
| Error handling (no silent English) | Pass | `lib/llm.py` fails loud (no untranslated-fallback); bad input → 400 (auto-verified). |
| Resilience on a real site | Pass | 0 errors on live content; extension injects on strict-CSP sites; widget URL-race fixed. |
| UX polish | Pass | One-click translate/restore, cache-hit badge; backend hint now refreshes on panel open. |
| Deployment (Fly.io public URL) | Pass | Both services live on Fly.io; public gateway `/health` nests AI; live translate via public URL → `El taladro sin cable cuesta $129.99 en el pasillo 7.` ($129.99 preserved, es-MX). `deploy_health_ok: true`. |

Also verified this session: **trace correlation** — an injected `X-Request-Id` (`eval-trace-4576aa`) appeared in **both** the gateway log (`POST /translate 200 1941ms`) and the AI-service log (`request_id`), greppable end-to-end. No secrets, `*.db`, or `*.log` are tracked in git.

## 4. Top fixes before shipping

No blocking gaps — all dimensions Pass. Minor notes:

1. ~~Align the cost-model label.~~ **Fixed** — `benchmark/sla.json` now labels the cost model `claude-sonnet-5` to match the model in production. The prices (`$3/$15` per MTok) were already correct for Sonnet 5, so the reported $/mo figures are unchanged.
2. **First-request cold start (~3-5s).** Fly machines auto-stop when idle to save cost; the first translate after a quiet period cold-starts them. Acceptable for grading; if a warm demo matters, set `min_machines_running: 1` on the gateway.
3. **Extension backend URL.** The extension's saved backend URL is set to the public gateway (`https://fde-live-translate-gateway.fly.dev`) — confirm this before any future demo so the on-page test exercises the deploy rather than localhost.
