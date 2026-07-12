# Known Issues / Next Fixes

## 1. Whole-page translation is slow on very large pages

**Symptom.** On a normal page (a product page, a short article) the widget flips
to Mexican Spanish in a few seconds. On a *very* large page — e.g. the Wikipedia
"Coffee" article, which has ~5,500 separate text chunks — it can take several
minutes, showing a slow `translating… 160/5499`-style counter.

**Root cause.** The frontend widget is provided and must not be edited. It walks
the whole DOM, collects every text node, and sends them to my backend in
**sequential slices of ~40** (`POST /translate/batch`), waiting for each slice to
come back before sending the next. So a 5,500-chunk page is ~138 slices done one
after another — the latency is dominated by that sequential round-trip chain, not
by any single translation.

**What I already did.** I made each slice as cheap as possible: the batch endpoint
now translates a whole slice of misses in a **single LLM call** (JSON array in,
same-length JSON array out) instead of one call per string. That's ~40× fewer API
calls per slice, keeps me under the provider's per-minute rate limit, and drops a
40-string slice from ~60s to ~8s cold. Cache hits are served for free, so a
re-translate of the same page is instant. This makes normal pages fast; it does
not remove the sequential-slice ceiling on huge pages.

**Options to fix next (owning the service end to end).**
1. **Server-side fan-out + streaming.** Add a whole-page endpoint that accepts all
   chunks at once and translates them with bounded concurrency on the AI service
   (a semaphore sized to the rate limit), streaming results back as they finish so
   the page fills in progressively instead of slice-by-slice.
2. **Viewport-first / progressive translation.** Translate the visible text first
   and lazily translate the rest as the user scrolls, so the page *appears*
   translated almost immediately.
3. **Persistent/shared cache.** Back the SQLite tier with a shared store (e.g.
   Redis) so popular pages are warm across users and most slices are cache hits.

**Impact today.** None for realistic pages or for any re-translation (cache hit).
The only slow path is a first-time translation of an unusually large page.
