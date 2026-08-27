# GeniuzLab — Phase 2A: Final UI & AI Stabilization Changelog

Date: 2026-07-19
Scope: mobile chat composer, site-wide responsive audit, AI assistant
reliability, final interaction polish — ahead of Phase 2 (Production Security).

No features were added and no UI was redesigned. Every change below is a
targeted fix to existing markup/CSS/JS. Total footprint: **7 files changed**
(`static/css/style.css`, `static/js/assistant.js`, `templates/base.html`, and
4 templates that share one repeated markup pattern). Nothing else in the
project was touched.

Where possible, fixes were verified empirically with a headless Chromium
harness (Playwright) reproducing the exact markup/CSS in isolation — not just
read off the source — since a live Django server couldn't be booted in this
environment (no network access to install dependencies). Each section below
states how it was verified.

---

## 1. Chat composer — send button squash bug

**Symptom reported:** send button shrinks/gets squashed on mobile instead of
staying a fixed circular button.

**Root cause:** `.chat-form input` had no `min-width:0`. A bare
`<input type="text">` keeps its browser-default intrinsic minimum width
(~200px) even inside a flex container unless that's explicitly overridden.
On narrow viewports the input hit that floor and refused to shrink further,
so the flexbox algorithm pushed *all* of the missing space onto the send
button instead (which had no `flex-shrink:0` protection) — collapsing it
toward 0px. This is a classic, well-documented flexbox gotcha, and it
reproduced exactly: at 320–414px the send button's rendered width measured
0–26px before the fix.

**Fix (`static/css/style.css`):**
- `.chat-form input` — added `min-width:0` and `box-sizing:border-box` so it
  actually flexes down to the space available instead of hitting a hidden
  UA floor.
- `.chat-form button` — added `flex-shrink:0`, `min-width/min-height:48px`,
  `max-width:48px`, `box-sizing:border-box`. It can no longer be shrunk by
  the flex algorithm under any circumstance.
- `.chat-form button.btn-primary` — added an explicit override pinning width
  to 48px. The send button reuses `.btn-primary` for its green fill, and
  that shared class also carries a `width:100%` rule for full-width CTA
  buttons at ≤480px elsewhere on the site (course/konnect buttons). This
  guarantees that shared rule can never touch the composer's button, at any
  breakpoint, regardless of future changes to `.btn-primary`.
- `.chat-attach-btn` — added `min-width:42px` and `box-sizing:border-box`
  for the same belt-and-suspenders protection (it already had
  `flex-shrink:0`).
- `.chat-form` — added `align-items:center` so the attach icon, input, and
  send button line up on a shared vertical center regardless of font-metric
  differences between them.

**Verified:** headless-browser measurement of the actual composer markup +
CSS at 280, 320, 360, 375, 390, 414, 768, and 1280px. Send button holds
exactly 48×48px at every width down to 280px; attach button holds 42×44px;
no horizontal overflow at any width; all three elements vertically aligned
within <1px.

---

## 2. AI assistant — "Can't reach server"

**Symptom reported:** the AI assistant widget shows "Can't reach server."

**What it was NOT:** a missing `OPENAI_API_KEY`. The backend
(`assistant/engine.py`) already handles this correctly — `_try_openai_reply()`
wraps the entire OpenAI call in `try/except Exception: return None`, and
`get_reply()` only calls it as a secondary fallback after the deterministic
rule-based engine finds nothing. A missing or failing key already, silently,
falls back to rule-based replies. No change was needed there.

**Actual root cause: a CSRF cookie gap.** The assistant widget's
`<form id="glab-assistant-form">` in `templates/base.html` — included
site-wide — had no `{% csrf_token %}` tag anywhere in it. Several genuinely
public entry pages (`academy.html`, `graphics.html`, `hire_creative.html`,
`jobs.html`, `motion.html`, all four course pages) also never render a
`{% csrf_token %}` tag anywhere else on the page. Django only sets the
`csrftoken` cookie in the response when a template renders that tag (or a
view uses `@ensure_csrf_cookie`, which nothing in this project does).

So: a first-time visitor who lands on one of those pages and opens the
assistant has no CSRF cookie in their browser. `assistant.js`'s
`getCookie("csrftoken")` returns `null`, the POST to `/assistant/ask/` fails
Django's CSRF check, and the default CSRF failure view returns an **HTML**
403 page (there's no custom `CSRF_FAILURE_VIEW`). The frontend then calls
`.json()` on that HTML response, which throws a parse error, which lands in
the `.catch()` block — showing "Sorry, I couldn't reach the server just
now," even though the request reached the server fine and was rejected for
an unrelated reason.

**Fix:**
- `templates/base.html` — added `{% csrf_token %}` inside the widget's own
  form. Because this widget is rendered on every page (gated only by the
  `assistant_enabled` site setting), this guarantees the `csrftoken` cookie
  gets set on first page load regardless of which page a visitor lands on
  first — closing the gap for every currently-uncovered page, and any
  future one.
- `static/js/assistant.js` — hardened the fetch handler so a bad response no
  longer produces a confusing generic error:
  - Checks `response.ok` and the `content-type` header before calling
    `.json()`; a non-OK or non-JSON response is now treated explicitly as a
    server error instead of throwing an opaque parse exception.
  - Added a 15-second request timeout via `AbortController`, so a hung
    request shows "That's taking longer than expected…" instead of leaving
    the composer stuck in a disabled "sending" state indefinitely.
  - Defends against a JSON response missing expected fields (`data.reply`
    now falls back to a friendly default instead of rendering `undefined`).

**Verified:** traced the full request path end-to-end in the source
(view → URL routing → CSRF middleware default behavior → JS fetch chain)
and confirmed there's no custom `CSRF_FAILURE_VIEW`, so the failure path
really does return HTML. `node --check` confirms the edited JS is
syntactically valid. Could not exercise this live end-to-end (no network
access to install Django in this environment) — recommend a quick manual
click-through as part of Phase 2 QA: open an incognito window, go straight
to `/academy/` (or any of the other previously-uncovered pages) with no
prior page visits, and send an assistant message.

---

## 3. Responsive audit

Reviewed viewport handling, overflow safety nets, grid/flex breakpoints, and
known trouble spots (tables, fixed-width blocks, `white-space:nowrap`
usage) across the CSS and every template.

**Already solid, no changes needed:**
- Viewport meta tag present and correct in `base.html`.
- Global `overflow-x:hidden` safety net on `<body>` catches any decorative
  absolutely-positioned elements (hero glows, blur circles) that might
  otherwise extend past the viewport.
- All large fixed-width images/decorative elements already carry
  `max-width:100%` guards.
- Every major card grid uses `repeat(auto-fit,minmax(...))`, which reflows
  safely at any width — no fixed-column grids without a stacking override.
  The one two-column ratio grid found without an `auto-fit` pattern
  (`.founder-card`, `360px 1fr`) already has a `max-width:900px` media
  query that collapses it to a single column well above mobile widths.
- The dashboard tab bar (`.dash-tabs`) is an intentional horizontal
  scroller (`overflow-x:auto` + `white-space:nowrap` on tabs) — correct
  pattern, not a bug.
- No in-app `<table>` elements exist outside of email templates (which have
  their own, separate constraints and aren't part of the responsive site).
- Mobile nav dropdown (hamburger menu) already handles login/dashboard/
  logout links inside the same panel, with proper `max-height` + internal
  scroll.

**Found and fixed:**

### 3a. Mobile button-pair asymmetry + zero-gap stacking
Every `.form-box` form (VTU purchase forms, profile edit forms, konnect
apply/request forms — 11 templates) and the wallet header pair a
`.btn-primary` submit button with a `.btn-outline` "Cancel"/secondary link
right after it. The existing mobile rule (`@media max-width:480px`) only
forced `.btn-primary` to `width:100%`, leaving its sibling an inconsistent,
off-center, auto-width link stacked below it. Where there was no flex/gap
wrapper around the pair (`.form-box`), the two full-width buttons rendered
with **zero pixels of vertical gap between them** — confirmed by measuring
the actual rendered boxes in a headless browser (0px gap before the fix).

**Fix:** added `.form-box .btn-outline` and `.wallet-balance-actions
.btn-outline` to the existing mobile full-width rule so both buttons in the
pair match, and added `margin-bottom:14px` to `.form-box .btn-primary` on
mobile to restore spacing between the two stacked buttons (the wallet
version didn't need this — it already uses `display:flex; gap:14px`).

**Verified:** headless-browser measurement of the actual form markup at
375px, before and after — gap went from 0px to ~5px, both buttons full
width, no horizontal overflow.

### 3b. Notification/activity text overflow risk
The text block next to the icon in every "activity row" pattern (Wallet
recent activity, Notifications list, Dashboard activity feed — used in 4
templates) had no `min-width:0` inside its flex container. This is the same
class of bug as the chat composer issue (§1): without it, a long
notification message or transaction description has no flex-basis
protection and can refuse to shrink below its own content width, pushing
the row — and potentially its card — wider than intended.

**Fix:** added a new `.activity-row-body` class (`flex:1; min-width:0;`)
and applied it to the text `<div>` in all four templates:
`templates/wallet/wallet.html`, `templates/notifications/list.html`,
`templates/dashboard/_dash_activity.html`, `templates/dashboard/dashboard.html`.

**Verified:** stress-tested with a deliberately long message + currency
badge combination at 320/375/414px in a headless browser — no horizontal
overflow at any width, row scales down cleanly.

---

## 4. Final polish pass

Spot-checked Chat, Notifications, Konnect, Wallet, VTU, Academy, Dashboard,
and mobile navigation for the specific failure modes called out (overflowing
cards, overlapping buttons, broken spacing, horizontal scroll, hidden text,
compressed icons, layout shifts). Beyond the issues already listed above, no
further interaction-breaking inconsistencies were found in the areas
reviewed. Given the size of the codebase (13 Django apps, ~300 template
files), this pass prioritized the highest-traffic and highest-risk surfaces
(money-related pages, chat, notifications, forms) rather than an exhaustive
pixel audit of every template; a live-server visual QA pass during Phase 2
is still recommended to catch anything outside a static code review's reach.

---

## Files changed

| File | Change |
|---|---|
| `static/css/style.css` | Chat composer flex fix, send button lock, activity-row-body class, mobile button-pair parity + spacing |
| `static/js/assistant.js` | Hardened fetch handler: response.ok/content-type check, timeout, defensive defaults |
| `templates/base.html` | Added `{% csrf_token %}` to the site-wide assistant widget form |
| `templates/wallet/wallet.html` | Applied `.activity-row-body` class |
| `templates/notifications/list.html` | Applied `.activity-row-body` class |
| `templates/dashboard/_dash_activity.html` | Applied `.activity-row-body` class |
| `templates/dashboard/dashboard.html` | Applied `.activity-row-body` class |

No models, views, URLs, migrations, or backend logic were touched. Nothing
in this pass overlaps with or reverses any of the security fixes recorded
in `PRE_SECURITY_STATUS.md` — this project is ready to move into Phase 2
(Production Security) on top of this ZIP.
