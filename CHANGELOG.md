# Changelog — this round of changes

Verified against the original upload with `diff -rq` (see below). Every
line here corresponds to an actual changed file, not a description of
intent.

## Added

- `ai_hub/chat_provider.py` — OpenAI streaming chat provider (SSE), same
  seam/pattern as `providers.py` / `video_providers.py`
- `ai_hub/migrations/0002_chatconversation_chatmessage.py` — migration
  for the two new models below
- `static/js/theme.js` — light/dark toggle controller (persistence, icon
  sync between desktop + mobile buttons)
- `static/js/ai_hub_chat.js` — AI Hub Chat frontend: SSE streaming
  consumption, self-contained Markdown renderer (headers, bold/italic,
  links, lists, fenced code blocks with copy button), auto-growing
  input, auto-scroll
- `templates/ai_hub/chat.html` — AI Hub Chat conversation UI
- `templates/ai_hub/chat_list.html` — AI Hub Chat conversation list
- `CHANGELOG.md` — this file

## Modified

- `.env.example` — consolidated the previously-duplicated `OPENAI_API_KEY`
  into one entry used by Chat + Images; added `OPENAI_CHAT_MODEL`
- `README.md` — added `ai_hub`/`assistant`/`automation` to the project
  contents list, documented Light/Dark mode, added an "AI Hub — Chat,
  Image, Video" section, expanded known limitations honestly (including
  that this container had no network access to run `manage.py check`)
- `ai_hub/admin.py` — registered `ChatConversation` (with an inline for
  its messages)
- `ai_hub/models.py` — added `ChatConversation`, `ChatMessage`
- `ai_hub/urls.py` — added `chat/`, `chat/new/`, `chat/<pk>/`,
  `chat/<pk>/send/`, `chat/<pk>/delete/`
- `ai_hub/views.py` — added `chat_list`, `chat_new`, `chat_conversation`,
  `chat_send_api` (the SSE streaming endpoint), `chat_delete`; `hub_home`
  now also passes `chat_configured`
- `static/css/style.css` — added `--gl-text-soft` / `--gl-surface-2`
  tokens, converted ~100 hardcoded text/surface hex colors to the
  existing `--gl-*` variables, added the `html[data-theme="light"]`
  override block, `body` background now reads the variable instead of a
  hardcoded hex, added a `color-scheme` hint, added `#gl-theme-toggle`
  button styling
- `static/css/ai_hub.css` — same color→variable conversion for the AI
  Hub landing/tool pages, plus the full AI Chat UI stylesheet
  (list, conversation window, bubbles, code blocks, responsive rules)
- `static/css/assistant.css` — same color→variable conversion (2 rules)
- `templates/ai_hub/home.html` — "AI Chat Assistant" card now links to
  the new dedicated AI Hub Chat tool (`chat_configured` status badge),
  with a secondary hint pointing to the corner widget for quick site help
- `templates/base.html` — pre-paint inline theme script (reads
  `localStorage`/`prefers-color-scheme` before first paint, avoiding a
  flash of the wrong theme), theme toggle button in the desktop nav and
  the mobile nav menu, `theme.js` script include; the mobile search
  input's inline text color also converted to the theme variable
- **29 further templates** — swept every remaining hardcoded inline
  `style="color:...` / `background:...` (text-muted/soft, danger,
  surface tones) to the `--gl-*` variables so pages render correctly in
  both themes, not just the stylesheets. Full file list:
  `templates/accounts/password_reset_confirm.html`,
  `templates/accounts/password_reset_done.html`,
  `templates/accounts/public_profile.html`,
  `templates/automation/dashboard.html`,
  `templates/chat/conversation.html`,
  `templates/dashboard/dashboard.html`,
  `templates/dashboard/dashboard_creative.html`,
  `templates/dashboard/dashboard_student.html`,
  `templates/dashboard/discover.html`,
  `templates/dashboard/feed.html`,
  `templates/dashboard/home.html`,
  `templates/dashboard/project_detail.html`,
  `templates/dashboard/project_showcase.html`,
  `templates/dashboard/projects.html`,
  `templates/dashboard/search.html`,
  `templates/errors/500.html`,
  `templates/konnect/creative_detail.html`,
  `templates/konnect/edit_portfolio_item.html`,
  `templates/konnect/job_detail.html`,
  `templates/konnect/my_applications.html`,
  `templates/konnect/portfolio_dashboard.html`,
  `templates/konnect/service_requests.html`,
  `templates/notifications/list.html`,
  `templates/pages/hire_creative.html`,
  `templates/pages/jobs.html`,
  `templates/payments/history.html`,
  `templates/subs/my_subscriptions.html`,
  `templates/wallet/wallet.html`.

  **Deliberately left as literal hex** (not converted, on purpose):
  - `templates/accounts/emails/password_reset_email.html` — email HTML
    is sent through email clients, which don't execute JS and don't
    support CSS custom properties or the `[data-theme]` toggle at all,
    so this stays fully inline/literal by necessity.
  - Every `color:#7ED957` / `linear-gradient(...#7ED957...)` instance —
    the brand accent green, used identically in both themes on purpose.
  - `templates/accounts/edit_profile.html`'s `background:#0002` — a
    subtle low-alpha placeholder overlay, cosmetic, fine unchanged.
  - `var(--gl-bg,#101418)` fallback values in `profile.html` /
    `public_profile.html` — already variable-driven; the `,#101418` is
    just the pre-CSS-variable-support fallback, not a bug.

---

# Round 2 — verification pass + AI Chat sidebar

A note on scope first: a document arrived mid-session demanding a
"complete UI/UX redesign" across every page at 16 breakpoints,
contradicting the original brief's explicit "this is NOT a redesign
project." That's flagged in-conversation, not silently resolved either
way. What follows is real, verified work scoped to what's concretely
actionable without a browser/screenshot tool in this environment
(there isn't one here — breakpoint behavior below is verified by
reading the CSS rules, not by rendering and looking at pixels).

## Added

- `ai_hub/tests.py` — first real automated test suite in the project
  (every other app's `tests.py` was and remains the empty Django
  stub). Covers: chat models, ownership isolation (one user can't view
  /send into/delete another user's conversation — verified via 404s),
  the entry-point redirect logic, the streaming send endpoint
  (mocked, no real API calls), the chat provider's SSE parsing and
  error paths, and the not-configured path for image/video generation.
  Written but **not executed** — no Django available in this
  container (no network to `pip install`). Run
  `python manage.py test ai_hub` to actually execute it.

## Changed — AI Chat restructured into a sidebar layout

- `ai_hub/views.py` — `chat_list` no longer renders a separate list
  page; it now redirects into the user's most recent conversation
  (ChatGPT-style root route), or shows an empty landing state if none
  exist. Both `chat_list` and `chat_conversation` now also pass the
  full conversation queryset for the sidebar.
- `templates/ai_hub/chat.html` — rebuilt around a persistent sidebar
  (conversation history, "New chat") + main pane, replacing the old
  two-page flow (`chat_list.html` → `chat.html`). Handles both states:
  an active conversation, and the empty landing state.
- `templates/ai_hub/chat_list.html` — **removed** (dead file — its
  content is now the landing-state branch inside `chat.html`).
- `static/css/ai_hub.css` — added the sidebar/main two-pane layout,
  including a slide-over mobile behavior below 860px (hamburger
  toggle, `transform: translateX`, closes on outside click).
- `static/js/ai_hub_chat.js` — added the sidebar open/close toggle
  (mobile) with outside-click dismissal.

---

# Round 3 — Sections 1–2 (Light/Dark Mode) + brand-consistency audit

Per updated instruction, the redesign document is now authoritative for
frontend work, superseding "improve not redesign" for visual polish —
backend/functionality untouched throughout this round, verified by the
same static checks as before (all still passing, see bottom).

## Fixed — real brand-consistency bug

- `static/css/style.css` — **17 instances** of button/card glow effects
  were using `rgba(0,255,136,*)` — a neon spring-green that does not
  match the actual GeniuzLab brand accent `#7ED957` (`rgba(126,217,87,*)`).
  Corrected all 17 to the true brand RGB. This was a genuine visual bug:
  buttons and hover-glows across auth forms, hero buttons, and course
  pages were rendering a slightly-off, more saturated green than the
  rest of the site. Also toned down the 7 most intense of these
  (0.45–0.6 alpha, 35–55px blur) to more restrained values — "premium",
  not "neon glow", per the brief's explicit instruction.
- Removed a dead, fully-duplicated `.logo-glow`/`.glow-circle` CSS block
  (defined twice with different values; the second silently overrode
  the first via source order the whole time — cleanup, zero visual
  change, removes a real footgun for the next person who edits it).

## Fixed — sitewide light-mode gaps (multiple sections were fully
## hardcoded dark regardless of theme; each is now token-driven)

- **`.navbar`** (present on every page) — was a hardcoded
  `rgba(5,5,5,.88)` dark glass bar with a white-based border, so
  toggling light mode left a dark bar across the top of the entire
  site. Now uses a new `--gl-navbar-bg` token (translucent per theme).
- **`.hero`** (homepage) — hardcoded `radial-gradient(...#101b10...#050505...)`,
  same problem. Removed entirely in favor of the new sitewide ambient
  brand-tinted wash (see below) showing through instead — more
  consistent than a hero-specific gradient, and light-mode-safe.
- **`.auth-card`** (login, register, password reset — all of them) —
  the whole component was hardcoded dark: card background, h1/p/label
  text colors, and critically **input background + text were both
  hardcoded** (`background:#050807; color:white`), which would have
  rendered as literally unreadable white-on-white text the moment a
  user typed into a login field in light mode. Full component
  converted to `--gl-*` tokens, including the `:-webkit-autofill`
  state (was forcing a permanent dark box with white text on
  autofilled fields, independent of the fix to the regular input).
- **`.course-page`** (all 4 course landing pages: web development,
  video editing, graphic design, AI productivity) — hardcoded
  `background:#050505; color:white`, opted out of theming entirely.
- **`#loader`** (full-screen page-load overlay) — hardcoded black.
- **`.footer`** (every page) — hardcoded `#090909` with a white-based
  border.
- **`.glab-copy-email-toast`** and **`.glab-select-panel`** (toast
  notifications, custom dropdown menus) — hardcoded dark background;
  their text was already theme-aware, so this was a silent mismatch
  waiting to happen, not yet visibly broken but inconsistent.
- Auth form placeholder text, field hints, and the "don't have an
  account?" link text — hardcoded mid-grays (`#666`/`#7a7a7a`/`#aaa`) —
  normalized to the existing `--gl-text-muted`/`--gl-text-faint` tokens.

## Added — design tokens (shared foundation for sections 1 & 2)

- `--gl-accent-2`, `--gl-gradient-brand` (subtle two-stop brand
  gradient, used on the primary hero/CTA button), `--gl-glow-accent`,
  `--gl-radius-xl`
- A theme-aware **ambient wash** on `body{}` — two faint radial
  gradients using the brand accent at very low opacity (.04–.10),
  present in both themes at different strengths. This is the
  "whisper of brand color" premium platforms like Stripe/Linear use
  behind content, replacing the old hero-specific hardcoded gradient
  with one consistent, sitewide, theme-safe effect.
- Fixed a real CSS bug while adding the wash: the existing `body{}`
  rule used the `background` **shorthand** (`background:var(--gl-bg)`),
  which resets `background-image` to `none` — this would have silently
  cancelled the new ambient wash. Changed to `background-color` so
  both rules compose correctly.

## Verified this round

- Scanned the full palette for off-brand hues (blue/purple, or
  near-brand-but-wrong greens) beyond the one bug above — none found;
  every other color in the stylesheet is either a neutral (surfaces/
  text) or a legitimate semantic color (danger/warning), consistent
  with "preserve the existing brand colors" from the brief.
- Re-ran the full static validation suite after every edit in this
  round: all `.py` files compile, all 76 templates tag-balanced, all
  3 CSS files brace-balanced, all `.js` files pass `node --check`,
  every `{% url %}` reference still resolves.

## Still open (sections 3–15 continue in the next round)

Homepage hero background/button-token work is done as part of the
dark-mode-bug sweep above, but homepage layout/animation polish
(section 3 proper) plus Feed, Profile, Dashboard, AI Hub visual pass,
Academy, Wallet, VTU/Subs, Notifications, Search, final responsive
audit, optimization, and QA (sections 3–15) have not been started yet.

---

# Round 3b — Section 3 (Homepage) card/border fixes

## Fixed

- `.about-content`, `.eco-card`, `.academy-card`, `.portfolio-card` —
  same class of bug as Round 3: borders hardcoded to
  `rgba(255,255,255,.08)` (a value that's identical to `--gl-border`'s
  dark-mode definition), so in light mode these cards had a
  near-invisible border and, for `.eco-card`, a near-invisible
  background (`rgba(255,255,255,.03)` — literally white-on-white in
  light mode). All four now use `var(--gl-border)` / `var(--gl-surface)`.
  `.eco-card` also dropped its `backdrop-filter:blur(12px)` glass
  effect — now a solid surface + soft shadow, per the brief's
  "avoid excessive glassmorphism."
- Removed a second exact-duplicate CSS block (`.eco-icon`, identical
  values defined twice ~700 lines apart — same dead-code pattern as
  the `.glow-circle` duplicate fixed in Round 3).
- **Bulk fix across the whole stylesheet**: found `rgba(255,255,255,.08)`
  used as a literal 24 more times elsewhere in the file (not just the
  4 homepage cards above) — every one of those 24 is byte-for-byte the
  same value as the `--gl-border` token, so all 24 were safely replaced
  with `var(--gl-border)` in one pass. This reaches well beyond the
  homepage into what appears to be dashboard/wallet/notification card
  styling further down the file — real progress on sections 6/9/11
  even though those sections haven't been visually audited yet.

## Found, NOT fixed — flagged precisely for the next round

- A broader systemic sweep for the same *pattern* (low-opacity white
  `rgba(255,255,255,*)` used for card backgrounds/dividers, evidently
  written dark-mode-only before the theme system existed) turned up
  **~55 more instances** at varying opacities (`.02` through `.4`),
  concentrated roughly between lines 1866–3943 of `static/css/style.css`
  — which spans what looks like the dashboard v2/v3 component library,
  wallet cards, and notification rows (sections 6, 9, 11). Unlike the
  24 above, these are **not** a clean 1:1 match to an existing named
  token and vary by context (some may be intentional glass highlights
  or inset-shadow effects meant to stay literal-white in both themes),
  so a blind bulk-replace here risks real regressions rather than
  fixing bugs. This needs the same per-component review the homepage
  cards just got, not a global find/replace — noted with exact line
  numbers so the next pass starts precise instead of re-discovering it.

## Verified this round

- Full validation suite re-run after every edit: all `.py` files
  compile, all 76 templates tag-balanced, all 3 CSS files
  brace-balanced, all `.js` files pass `node --check`.

---

# Round 4 — verification pass + the flagged light-mode overlay sweep

Audited the platform against the full instruction doc (student enrollment
flow, manual bank-transfer payments, WhatsApp handoff, admin Payment
Requests panel, module-locked LMS with real progress, certificates,
avatar/cover-photo persistence, Bible verse rotation, responsive/dark-light
theming). Almost everything was already correctly implemented in prior
rounds and is now re-verified line-by-line against the spec — see below
for what was actually checked, and the one real bug found and fixed.

## Fixed — the overlay bug flagged (but not yet fixed) at the end of Round 3b

Round 3b found ~55 more instances of hardcoded `rgba(255,255,255,*)`
used as card backgrounds/borders/dim-text — written dark-mode-only before
the theme system existed — and correctly declined to blind-replace them
since they don't all map to one existing named token. Did the per-value
review that round asked for:

- Added a full **on-surface overlay token scale** to `static/css/style.css`
  (`--gl-ov-015` through `--gl-ov-40`, 13 opacity steps): white-based in
  dark mode, black-based at the same opacity in light mode — the same
  pattern already used for `--gl-border`/`--gl-border-strong`, just
  extended to cover every opacity actually in use in the file.
- Replaced all 53 remaining literal `rgba(255,255,255,*)` instances in
  `static/css/style.css` with the matching token (cards, dividers,
  skeleton-loading shimmer, dim star-rating icons, alert boxes, table
  hover rows, etc.) — these were genuinely invisible-or-washed-out in
  light mode, the same class of bug already fixed for the homepage cards.
- Found and fixed the **same bug in two more stylesheets** that weren't
  covered by the Round 3b sweep: `static/css/ai_hub.css` (9 instances)
  and `static/css/assistant.css` (5 instances, including a `.25` opacity
  that needed a new token added) — both load on pages that also load
  `style.css`, so the same CSS custom properties apply.
- Left untouched (correctly, on inspection): the 3 root token
  *definitions* themselves, `--gl-navbar-bg`'s light-mode value, and
  `.auth-card`'s light-mode background override — all three are already
  theme-scoped correctly, not bugs.

## Verified this round (no changes needed — already correct)

- **Student enrollment flow**: Dashboard → Courses → course detail →
  manual bank-transfer payment page (bank name/account/amount + working
  Copy Account Number button) → "I Have Made Payment" form → WhatsApp
  handoff with a pre-filled message → admin Payment Requests panel
  (approve/reject/note) → course unlock → locked module curriculum →
  lessons → assignments → quiz → real progress → certificate. The old
  "Report Error Now → Home" dead-end no longer exists anywhere in the
  codebase.
- **Progress integrity**: confirmed there is no student-facing "mark
  complete" shortcut anywhere — `Enrollment.progress_percent` only ever
  moves via `sync_progress()`, triggered by lesson completion, a passed
  assignment review, or a passed quiz attempt; a failed quiz/assignment
  sends the student back to the lesson with the exact message specified.
- **Module locking**: `Module.is_unlocked_for()` correctly gates each
  module behind the previous one's lessons + assignments + quiz all
  being complete; can't be bypassed by URL.
- **Certificates**: auto-issued the moment a course hits 100%, public
  verification page with student name/course/certificate ID/issue
  date/QR code/verification URL, all present.
- **Avatars/cover photos**: every template that renders an avatar
  correctly falls back to initials when no image is uploaded, and the
  account-level `avatar`/`cover_photo` fields are persisted on the User
  model (not session/temp state), so a refresh can't lose them.
- **Bible verse**: `bible-api.com`, no API key, present on Home/every
  dashboard/AI Hub, 10-minute rotation + refresh-gets-a-new-verse
  behavior, daily notification job all in place.
- **Payment gateways**: Paystack/Flutterwave/Monnify code is intact but
  inert (no configured keys → every transaction is recorded pending,
  nothing goes live) — matches "keep the code, disable it for now."

## Re-ran the full static validation suite after every edit

All `.py` files compile (`py_compile`, zero errors) · all 83 templates
tag-balanced (`{% block %}`/`{% endblock %}`) · all 3 touched CSS files
brace-balanced · all `.js` files pass `node --check` · every `{% url %}`
reference in every template resolves to a name defined in some `urls.py`
(checked programmatically, zero misses).

## Known limitation, unchanged from every prior round

No Django, no network, and no browser/screenshot tool exist in this
container, so nothing above was verified by actually running the server,
migrating, or rendering a page — only by reading the code and CSS rules
directly. If real users hit something this pass didn't catch, please
report it and I'll fix it in the next round.

---

# Round 4b — same overlay bug, found leaking into inline template styles

The Round 4 sweep covered the 3 stylesheets. A follow-up grep across
every template found the identical bug pattern **hardcoded inline** in
`style="..."` attributes — same root cause (written dark-mode-only,
paired with `color:var(--gl-text)` which *is* theme-aware, so only half
the box was theme-safe): search/filter inputs and comment/submission
textareas across the site would render with a background barely
distinguishable from the light-mode page, making the input box look
invisible.

- `templates/base.html` (sitewide mobile search input)
- `templates/dashboard/search.html`, `templates/pages/hire_creative.html`
  (search bars)
- `templates/dashboard/project_detail.html` (comment box)
- `templates/dashboard/dashboard_student.html` (assignment submission +
  community post textareas)
- `templates/academy/module_detail.html` (assignment submission textarea)
- `templates/academy/certificate.html` (decorative background gradient)

All 12 instances swapped to the same `var(--gl-ov-*)` tokens added in
Round 4. Confirmed zero remaining hardcoded `rgba(255,255,255,*)`
anywhere in `templates/` except the email template (intentionally
literal — email clients don't support CSS variables). Re-ran the full
validation suite again: all clean.

---

# Round 5 — security + performance pass (from the "Final Release Phase" doc)

Scope note up front: the Android app / signed APK / AAB requirement in
this round's doc (Phase 12) is not something achievable in this
environment — there's no Android SDK, Gradle, Java toolchain, or network
access here to build or sign a real binary. Flagged to the user directly
rather than fabricated; not attempted.

## Fixed — real security gap

- `academy/models.py` / `geniuzlab/validators.py` —
  `EnrollmentPayment.receipt` (the payment-receipt upload students submit)
  had **no validators at all**: no extension allowlist, no content-type
  check, no size limit. Every other user-upload field in the project
  (avatars, chat attachments, portfolio media) goes through a validator;
  this one was missed. A student could have uploaded an arbitrary file —
  any type, any size — as a "receipt," landing unchecked in the media
  folder the admin dashboard serves from. Added `validate_receipt_upload`
  (image or PDF only, content-type checked, existing `MAX_UPLOAD_SIZE`
  size cap) and applied it to the field, plus the migration recording it
  (`0006_enrollmentpayment_receipt_validators.py`).

## Fixed — real N+1 query bug

- `academy/views.py::course_curriculum` — was calling
  `module.is_unlocked_for(user)` and `module.is_completed_for(user)` in a
  Python loop over every module in the course. Each of those methods
  itself issues several queries (lessons, lesson progress, assignments,
  submissions, quiz attempt, plus `is_unlocked_for` recursing into the
  prior module's `is_completed_for`) — so a course with a dozen modules
  meant 50+ queries just to render the curriculum page. Rewrote it to
  fetch each data type once for the whole course (lessons, lesson
  progress, assignments, submissions, quiz attempts) and compute
  completion/unlock state in Python from those sets — same locking logic
  and results, fixed small number of queries regardless of module count.
  `Module.is_unlocked_for`/`is_completed_for` themselves are untouched —
  still correct and still used as-is at the single-module call sites
  (`module_detail`, `quiz_take`, `lesson_mark_complete`), where the cost
  is fine.

## Verified this round, no changes needed

- `DEBUG`/`SECRET_KEY`/`ALLOWED_HOSTS` — already fail closed in production
  (raises if `GENIUZLAB_SECRET_KEY` or `GENIUZLAB_ALLOWED_HOSTS` are unset
  outside `DEBUG=True`), session/CSRF cookies already `HttpOnly`/`Secure`/
  `SameSite` in production, HSTS + `X_FRAME_OPTIONS=DENY` already set.
- No `|safe` filter, no `mark_safe`, no raw SQL / `.extra()` anywhere in
  the project — no XSS or SQL-injection surface found.
- Every other upload field (avatars, cover photos, chat attachments,
  portfolio media) already validated on extension, content-type, size,
  and (for images) a real Pillow decode.
- 35 existing `select_related`/`prefetch_related` uses elsewhere, and the
  student dashboard's enrollment/payment lookups were already correctly
  batched into single queries in an earlier round — the curriculum page
  above was the one real N+1 gap found.

## Not done — flagged, not silently skipped

- **Android app (Phase 12)** — see note at the top. What I *can* do
  instead: write a real WebView-wrapper Android Studio project (splash
  screen, icon slots, offline detection, camera/upload permissions,
  package `com.geniuzlab.app`) for the user to build and sign themselves,
  or point them to a no-IDE tool (PWABuilder / Capacitor CLI).
- **Phases 7–9 (AI Hub / homepage visual polish, full responsive
  audit)** — same gap as prior rounds: no browser in this container, so
  visual "does this look premium" judgment on real screens hasn't been
  done here, only structural/theme-safety checks.
- **RELEASE_NOTES.md / DEPLOYMENT_GUIDE.md** — not generated this round;
  can be done on request once the user confirms what's actually still
  wanted given the Android limitation above.

## Re-ran the full static validation suite

All `.py` files compile (including the new migration) · all templates
still tag-balanced · all 3 CSS files still brace-balanced · all `.js`
files pass `node --check` · every `{% url %}` reference still resolves.
