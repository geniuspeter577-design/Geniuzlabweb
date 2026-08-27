"""Seeds one fully-authored, published starter module into each Academy
course that currently has zero curriculum (Video Editing, Web Development,
AI & Productivity — Graphic Design already has its own showcase module via
seed_showcase_lms_module).

Why this exists: the full curriculum for these three courses is meant to
come from academy/course_generator.py (generate_academy_phase5), but that
requires OPENAI_API_KEY and network access to api.openai.com, neither of
which is available in every environment. Without it, these three courses
show zero modules to students, which breaks the "student can learn"
workflow end to end. This command closes that gap with real, hand-written
teaching content — not placeholder text — following the exact same
Module -> Lesson -> Assignment -> Quiz shape and quality bar as the
existing Graphic Design showcase module, so students always have at least
one real module to start on immediately.

This does NOT replace generate_academy_phase5 — an admin can still run
that (with an API key configured) to add more AI-drafted modules on top,
which stay in draft until reviewed and published, exactly as designed.

Idempotent: matches on (course slug, module title), so re-running this
command creates nothing new once each course already has its starter
module.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from academy.models import (
    Assignment, Course, Lesson, Module, Quiz, QuizChoice, QuizQuestion,
    ensure_default_courses,
)

# --------------------------------------------------------------------------
# Video Editing
# --------------------------------------------------------------------------
VE_LESSON_1 = """Welcome to your first lesson in Video Editing! Before you touch any software, \
you need to understand the one core idea behind every edit you'll ever make: editing is \
storytelling through selection and timing, not just "cutting clips together."

Think about it this way. If you filmed an entire birthday party from start to finish and \
showed someone the raw, unedited footage, they'd be bored in two minutes — even though \
something genuinely fun happened. Editing is what turns three hours of raw footage into a \
90-second highlight reel that actually makes someone feel the excitement of being there. \
You're not just trimming; you're deciding what the viewer sees, in what order, and for how \
long, so that a feeling comes through.

Every edit you make should answer one question: does this cut help the story, or does it \
just exist because that's where the raw footage happened to end? A cut that lingers a beat \
too long feels slow. A cut that's too fast feels chaotic and hard to follow. Finding that \
right rhythm — called "pacing" — is the single skill that separates amateur edits from \
professional ones, and it's something you build with practice, not a setting you turn on.

Here's the basic workflow every editor follows, regardless of software: first, you import \
and organize your footage (nothing kills momentum like hunting for the right clip in a messy \
folder). Second, you do a "rough cut" — roughly assembling clips in order, focused purely on \
story and pacing, ignoring colour and effects completely. Third, you refine: tightening cuts, \
adding transitions only where they earn their place, and layering in music and sound effects. \
Finally, you polish: colour grading, titles, and export settings.

A common beginner mistake is trying to do all four steps at once — picking the perfect \
transition for a clip before you've even decided if that clip belongs in the video at all. \
Resist that urge. Get the story right first with a rough cut using plain hard cuts only, no \
effects. Everything else is decoration on top of a story that already works.

For your practice task: take any 10 short clips you have on your phone (even random daily \
life clips are fine) and assemble them into a 20-30 second sequence using only hard cuts — no \
transitions, no music yet. Focus entirely on order and timing. Watch it back and ask: does \
each cut feel like it happens at the right moment, or too early/too late?

To sum up: editing is storytelling through selection and timing. Master the rough-cut-first \
workflow, and every tool you learn after this will slot into a process that already makes \
sense."""

VE_LESSON_2 = """In your last lesson, you learned that editing is about story and pacing, and \
you built a rough cut using nothing but hard cuts. In this lesson, we'll add two things that \
instantly make an edit feel more professional: intentional transitions and basic audio \
levelling — both frequently misused by beginners, so we'll cover exactly when (and when not) \
to use them.

Let's start with transitions. A hard cut (footage simply switches from one clip to the next) \
is your default — it's invisible to the viewer and keeps the story moving. A cross-dissolve \
(one clip fades into the next) signals "time has passed" or "a mood has softened" — use it \
between scenes, not within one continuous moment. A whip pan or fast-motion blur transition \
signals energy and should be reserved for high-energy content like sports or hype reels. The \
beginner mistake is using a flashy transition on every single cut "because it looks cool" — \
this actually makes footage harder to watch, because the viewer's brain has to process a \
special effect every couple of seconds instead of following the story.

Now, audio. Here is a rule that instantly upgrades any edit: your background music should \
never be louder than dialogue, and it should duck (lower in volume automatically or manually) \
whenever someone is speaking. A simple way to check this without fancy tools: if you can't \
clearly understand every word of dialogue on a phone speaker at normal volume, your music is \
too loud. Most video editing software has a "duck under voice" or you can manually keyframe \
the music volume down by about 60% during dialogue, then back up between lines.

Let's also talk about clip length and variety. Watching the exact same shot for more than 3-4 \
seconds in fast-paced content (like a reel) starts to feel slow, because the viewer's eye has \
already absorbed everything in the frame. Varying your shot types — a wide shot, then a \
close-up, then a different angle — keeps visual interest even if the underlying footage is \
simple.

For your practice task: take the 20-30 second rough cut from Lesson 1 and add: (1) exactly one \
cross-dissolve, placed only where it makes sense (a mood or time shift, not mid-action), and \
(2) any background music track, with the volume lowered under any dialogue or key sound in \
your clips.

To sum up: transitions should be chosen for what they communicate, not for how flashy they \
look, and background music exists to support your footage, never to compete with it."""

VE_ASSIGNMENT = """Edit a 45-60 second highlight reel from any footage you have (phone clips \
of an event, a walk, cooking — anything works). Requirements: use a rough-cut-first workflow \
(assemble with hard cuts before adding anything else), include at least one intentional \
cross-dissolve used correctly, add a background music track with the volume kept below any \
dialogue or key sound, and vary your shot lengths so no single clip runs longer than 4 \
seconds. Submit the final export plus 2-3 sentences explaining what story or feeling you were \
going for and one editing decision you're proud of."""

VE_QUIZ = [
    {"text": "What should every cut in an edit be justified by, according to this module?",
     "choices": [("Whether it helps tell the story", True), ("Whether the raw footage happened to end there", False),
                 ("How flashy the available transition looks", False), ("Matching the length of the previous clip exactly", False)]},
    {"text": "When should a cross-dissolve transition generally be used?",
     "choices": [("Between scenes to signal a time or mood shift", True), ("On every single cut, for a consistent look", False),
                 ("Only during fast action sequences", False), ("Never — hard cuts are always correct", False)]},
    {"text": "What is the recommended rule for background music under dialogue?",
     "choices": [("It should be lowered so dialogue stays clearly audible", True), ("It should stay at a constant volume throughout", False),
                 ("It should be louder than dialogue for energy", False), ("Music and dialogue should never be used together", False)]},
]

# --------------------------------------------------------------------------
# Web Development
# --------------------------------------------------------------------------
WD_LESSON_1 = """Welcome to Web Development! Before writing a single line of code, you need a \
mental model of what a website actually is, because that model will make every tool you learn \
afterward click into place instead of feeling like memorized magic.

A website is just three layers working together. HTML is the structure — think of it as the \
walls, rooms, and doors of a house: it defines what exists (a heading here, a paragraph there, \
a button over here) with no opinion on how it looks. CSS is the styling — the paint, \
furniture, and layout of those rooms: it decides colours, spacing, fonts, and positioning. \
JavaScript is the behaviour — the electricity and plumbing: it makes things respond when a \
visitor clicks, types, or scrolls. Every website you have ever used is built from exactly \
these three layers, no matter how complex it looks.

Let's make HTML concrete. An HTML document is a tree of "elements," each wrapped in tags: \
`<h1>Welcome</h1>` is a top-level heading containing the text "Welcome." Elements nest inside \
each other — a `<div>` (a generic container) can hold a `<h1>`, a couple of `<p>` (paragraph) \
elements, and a `<button>`. That nesting is not decorative; it's literally the structure the \
browser uses to know what belongs to what, exactly the way a `<div class="card">` containing \
a heading and paragraph tells the browser "these three things form one visual card."

A beginner mistake is trying to make things look right using only HTML — for example, adding \
extra blank lines in the HTML to create spacing. The browser ignores most whitespace in HTML \
by design; spacing, colour, and layout are CSS's job, not HTML's. Keep that separation in your \
head from day one and a huge amount of future confusion disappears.

Here's a small real example. This structure: a `<header>` with a site name, a `<main>` with a \
`<h1>` and a `<p>`, and a `<footer>` with copyright text, is the actual skeleton of most simple \
websites you've ever visited — news sites, blogs, portfolios. Complexity comes from repeating \
and combining these same basic building blocks, not from some entirely different set of rules.

For your practice task: using any plain text editor, write an HTML file with a `<header>` \
(containing your name), a `<main>` (containing one `<h1>` and two `<p>` elements about \
yourself), and a `<footer>` (containing the current year and "All rights reserved"). Open it \
in a browser by double-clicking the file — no server needed yet.

To sum up: HTML is structure, CSS is style, JavaScript is behaviour. Every website, no matter \
how advanced, is built from that same three-layer idea — you're now looking at every website \
you visit with new eyes."""

WD_LESSON_2 = """In Lesson 1 you built a plain HTML page — functional, but visually plain, \
because HTML alone carries no styling. In this lesson, you'll connect CSS to that page and \
learn the one CSS concept that trips up more beginners than any other: the box model.

First, connecting CSS. The cleanest way is a separate file: create `style.css` in the same \
folder as your HTML, then link it inside the HTML's `<head>` with \
`<link rel="stylesheet" href="style.css">`. Keeping CSS in its own file (rather than inline on \
each element) means one rule can style every matching element on the page at once — change it \
in one place, and every `<p>` on your whole site updates together.

Now, the box model — the single most important CSS concept to internalize early. Every HTML \
element the browser renders is treated as a rectangular box made of four layers, from the \
inside out: content (the actual text or image), padding (space between the content and the \
box's edge), border (a visible or invisible line around the padding), and margin (space \
outside the border, between this box and its neighbours). A button that looks "too cramped" \
usually needs more padding. Two boxes sitting "too close together" usually need more margin. \
Confusing padding and margin is the single most common beginner CSS mistake — padding pushes \
the box's own content inward; margin pushes other boxes away.

Selectors are how CSS finds elements to style. `h1 { color: navy; }` styles every `<h1>` on \
the page. `.card { padding: 16px; }` styles every element with `class="card"` — classes (the \
dot syntax) are how you style specific groups of elements rather than every element of a tag. \
This is why real projects rely heavily on classes: you rarely want to style every single \
`<div>` on a page identically.

A quick real-world habit: browsers include DevTools (right-click -> Inspect) that let you see \
exactly which CSS rule is affecting an element and its box model visually, live, without \
editing the file and refreshing repeatedly. Get comfortable opening DevTools early — it turns \
CSS from guesswork into direct observation.

For your practice task: link a `style.css` file to your Lesson 1 page. Give your `<header>` a \
background colour and padding, give your `<main>` a max-width and centre it, and give your two \
`<p>` elements distinct margin spacing so they don't sit flush against each other. Use \
DevTools to confirm your padding and margin values are doing what you expect.

To sum up: CSS connects via a linked stylesheet, and every element is a box of content, \
padding, border, and margin — understand that model and layout stops being mysterious."""

WD_ASSIGNMENT = """Build a simple one-page personal profile site using only HTML and CSS (no \
JavaScript yet). Requirements: a `<header>` with your name and a background colour, a `<main>` \
with at least one heading, two paragraphs about yourself, and one list (ordered or unordered) \
of three skills or interests, and a `<footer>` with the current year. Style it with a linked \
`style.css`: use at least one class selector, and correctly apply padding (inside spacing) and \
margin (outside spacing) so nothing looks cramped or squished together. Submit your HTML and \
CSS files (or a link if hosted) plus one sentence on a layout decision you made and why."""

WD_QUIZ = [
    {"text": "In the HTML/CSS/JavaScript model, what is CSS responsible for?",
     "choices": [("Styling — colour, spacing, layout", True), ("Structure — what elements exist", False),
                 ("Behaviour — responding to clicks", False), ("Storing website data", False)]},
    {"text": "In the CSS box model, what does 'padding' control?",
     "choices": [("Space between the content and the box's own edge", True), ("Space between this box and neighbouring boxes", False),
                 ("The colour of the box's border", False), ("Whether the box is visible at all", False)]},
    {"text": "What is the recommended way to connect CSS to an HTML page for a real project?",
     "choices": [("A linked external stylesheet file", True), ("Retyping styles inline on every element", False),
                 ("Extra blank lines and spaces in the HTML", False), ("CSS cannot be connected to HTML", False)]},
]

# --------------------------------------------------------------------------
# AI & Productivity
# --------------------------------------------------------------------------
AI_LESSON_1 = """Welcome to AI & Productivity! This first lesson isn't about any specific tool \
— it's about the one mental shift that determines whether AI tools actually save you time or \
just become another distraction: treating AI as a first draft generator, not a finished-work \
generator.

Here's the core idea. Modern AI chat tools (like ChatGPT, Claude, or Gemini) are extremely \
good at producing a reasonable first attempt at almost anything — an email, a summary, a \
brainstorm, a plan — instantly. They are not reliably good at producing a perfect final \
answer on the first try, especially for anything specific to your exact situation. The \
productivity gain doesn't come from the AI being "always right" — it comes from never having \
to stare at a blank page again. Editing a decent draft is dramatically faster than creating \
something from nothing.

This changes how you should prompt. A vague request like "write me an email" forces the AI to \
guess at your tone, audience, and goal, so you'll spend more time fixing the result than if \
you'd written it yourself. A specific request — who it's for, what outcome you want, what tone \
fits, any key facts to include — gets you a draft close enough to your actual need that editing \
takes two minutes instead of twenty.

Let's make this concrete with a real before/after. Weak prompt: "Write a follow-up email." \
Strong prompt: "Write a short, friendly follow-up email to a client who hasn't replied in 5 \
days about a quote I sent for a logo design project. Keep it to 3 sentences, no pressure tone, \
end with an easy yes/no question." The second version gives the AI everything it needs to \
skip the guessing and go straight to something close to usable.

A common beginner mistake is trusting AI output on facts, numbers, or anything you'll be held \
accountable for, without checking it. AI tools can state incorrect information confidently — \
this is a known limitation, not a rare glitch. Treat factual claims from AI the way you'd treat \
a claim from a stranger: useful as a starting point, but worth a quick verification before you \
rely on it for anything important.

For your practice task: pick one task you do repeatedly (an email type, a social caption, a \
summary format) and write one weak, vague prompt and one strong, specific prompt for it in any \
AI chat tool. Compare the two outputs and note which details in your strong prompt made the \
biggest difference to the result.

To sum up: AI is a first-draft generator, not a final-answer machine. Specific prompts turn a \
generic draft into a near-final one, and confident-sounding AI output on facts always deserves \
a quick check before you rely on it."""

AI_LESSON_2 = """In Lesson 1, you learned to treat AI as a first-draft tool and to write \
specific prompts. In this lesson, we'll build an actual repeatable workflow — because a single \
good prompt saves you minutes, but a saved, reusable prompt template saves you that same time \
every single time you do the task again.

Here's the workflow: template, don't retype. Once you've found a prompt structure that \
reliably produces a good first draft for a recurring task, save it somewhere (a notes app, a \
doc, a pinned message) with blanks for the parts that change. For the follow-up email example \
from Lesson 1, a template might read: "Write a short, [TONE] follow-up email to [WHO] about \
[WHAT], [LENGTH] sentences, ending with [DESIRED ACTION]." Filling in four blanks takes 15 \
seconds; writing a fresh prompt from scratch every time does not.

Next, chaining tools. Real productivity gains often come from combining two different AI tools \
for two different strengths rather than expecting one tool to do everything. For example: use \
a transcription tool to turn a voice note or meeting recording into text, then feed that text \
into a chat AI with the prompt "summarize this into 3 action items with owners and deadlines if \
mentioned." Each tool does the one thing it's actually best at, instead of forcing a single \
tool outside its strength.

Let's also cover a very practical habit: the "good enough" checkpoint. Not every task needs a \
perfect AI output — a quick internal note might be fine at 80% quality straight from the AI, \
while a client-facing document needs a careful human edit pass on top. Deciding up front how \
much polish a task actually needs (before you start editing) prevents two failure modes: \
over-polishing low-stakes work, and under-checking high-stakes work.

Finally, time tracking makes the gain visible and keeps you honest about what's actually \
working. For one week, jot down (even roughly) how long a task took before vs. after using an \
AI-assisted workflow for it. This turns "AI feels helpful" into a concrete before/after number, \
which is also exactly the evidence you'll use for your capstone project.

For your practice task: write one reusable prompt template (with blanks) for a task you do at \
least weekly, then use it twice on two different real examples of that task, noting how long \
each took start to finish.

To sum up: save your best prompts as reusable templates, chain tools together for their \
individual strengths, and match your editing effort to how much a task actually matters."""

AI_ASSIGNMENT = """Design and document a real personal or work workflow that uses at least two \
different AI tools together (for example: a transcription tool plus a chat AI, or an AI \
scheduling tool plus a chat AI for drafting). Your submission must include: the reusable \
prompt template(s) you used (with blanks marked), a short description of which tool did which \
part of the job, and a rough before/after time estimate for the task with vs. without this \
workflow. Submit the documentation plus one worked example showing the workflow run start to \
finish on a real task."""

AI_QUIZ = [
    {"text": "According to this module, what should you treat AI chat output as?",
     "choices": [("A first draft to edit, not a finished final answer", True), ("Always factually correct without checking", False),
                 ("Only useful for creative writing, nothing practical", False), ("A replacement for deciding your own goals", False)]},
    {"text": "What makes a prompt 'strong' rather than 'weak', per this module?",
     "choices": [("It specifies audience, goal, tone, and key details", True), ("It is written in the fewest possible words", False),
                 ("It avoids mentioning the desired outcome", False), ("It asks the AI multiple unrelated questions at once", False)]},
    {"text": "What is the benefit of saving a prompt as a reusable template?",
     "choices": [("It saves the same setup time every time you repeat the task", True), ("It guarantees a perfect result every time", False),
                 ("It removes the need to ever edit AI output", False), ("It only works with one specific AI tool", False)]},
]

STARTER_MODULES = {
    "video-editing": {
        "title": "Editing Fundamentals: Story, Pacing and Polish",
        "description": "The core editing workflow, plus transitions and audio levelling done right.",
        "lessons": [
            ("Editing Is Storytelling: The Rough-Cut Workflow", VE_LESSON_1),
            ("Transitions and Audio: Small Touches, Big Difference", VE_LESSON_2),
        ],
        "assignment_title": "Edit a 45-60 Second Highlight Reel",
        "assignment": VE_ASSIGNMENT,
        "quiz": VE_QUIZ,
    },
    "web-development": {
        "title": "Web Foundations: HTML Structure and CSS Styling",
        "description": "The three-layer model of the web, and the CSS box model that governs every layout.",
        "lessons": [
            ("HTML, CSS and JavaScript: The Three Layers of Every Website", WD_LESSON_1),
            ("Connecting CSS and Mastering the Box Model", WD_LESSON_2),
        ],
        "assignment_title": "Build a One-Page HTML/CSS Profile Site",
        "assignment": WD_ASSIGNMENT,
        "quiz": WD_QUIZ,
    },
    "ai-productivity": {
        "title": "AI-Assisted Work: Prompts, Templates and Workflows",
        "description": "Treating AI as a first-draft tool, and building reusable, chained AI workflows.",
        "lessons": [
            ("AI as a First-Draft Tool: Prompting With Precision", AI_LESSON_1),
            ("Templates and Tool-Chaining for Repeatable Wins", AI_LESSON_2),
        ],
        "assignment_title": "Document an End-to-End AI Workflow",
        "assignment": AI_ASSIGNMENT,
        "quiz": AI_QUIZ,
    },
}


class Command(BaseCommand):
    help = (
        "Seeds one fully-authored, published starter module (2 lessons, 1 assignment, "
        "1 quiz) into each of Video Editing, Web Development and AI & Productivity — "
        "the three Academy courses with no curriculum yet. Idempotent — safe to re-run."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        ensure_default_courses()
        created_any = False

        for slug, data in STARTER_MODULES.items():
            try:
                course = Course.objects.get(slug=slug)
            except Course.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Course '{slug}' not found — skipping."))
                continue

            if course.modules.filter(title=data["title"]).exists():
                self.stdout.write(self.style.WARNING(
                    f"{course.title}: starter module already exists — skipped (safe to re-run)."
                ))
                continue

            next_order = (course.modules.order_by("-order").values_list("order", flat=True).first() or 0) + 1

            module = Module.objects.create(
                course=course, title=data["title"], description=data["description"],
                order=next_order, status="published", is_ai_generated=False,
            )
            for i, (lesson_title, content) in enumerate(data["lessons"], start=1):
                Lesson.objects.create(module=module, title=lesson_title, content=content, order=i)

            Assignment.objects.create(
                course=course, module=module,
                title=data["assignment_title"], description=data["assignment"],
            )

            quiz = Quiz.objects.create(module=module, title=f"{module.title} Quiz", pass_percent=70)
            for i, q in enumerate(data["quiz"], start=1):
                question = QuizQuestion.objects.create(quiz=quiz, text=q["text"], order=i)
                for choice_text, is_correct in q["choices"]:
                    QuizChoice.objects.create(question=question, text=choice_text, is_correct=is_correct)

            created_any = True
            self.stdout.write(self.style.SUCCESS(
                f"{course.title}: seeded '{module.title}' — {len(data['lessons'])} lessons, "
                f"1 assignment, {len(data['quiz'])} quiz questions — published."
            ))

        if not created_any:
            self.stdout.write(self.style.SUCCESS("Nothing to do — every course already has its starter module."))
