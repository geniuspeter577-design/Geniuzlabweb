from django.core.management.base import BaseCommand
from django.db import transaction

from academy.models import (
    Assignment, Course, Lesson, Module, Quiz, QuizChoice, QuizQuestion,
    ensure_default_courses,
)

LESSON_1_CONTENT = """Welcome to your very first lesson in Graphic Design! By the end of \
this lesson, you'll understand what graphic design actually is, and why it matters so \
much in the world around you — even if you've never opened a design app before today.

Let's start with the concept. Graphic design is the practice of arranging images, text, \
colour, and shapes to communicate an idea or a message clearly. That's it — no complicated \
jargon needed. If you've ever chosen a nice font for a WhatsApp status, or picked colours \
that "just look right" together, you've already done a little bit of graphic design.

So why does this matter? Because everything you see was designed by someone, on purpose. \
The logo on your favourite drink, the poster for a church programme, the menu at a \
restaurant, the app icons on your phone — all of it is graphic design doing its job: \
grabbing your attention and telling you something, fast, before you even finish reading \
the words.

Here's a real-life example to make this click. Imagine you're scrolling through Instagram \
and you see two flyers for the same event. One is cluttered — ten different fonts, colours \
that clash, and text crammed into every corner. The other is clean — one bold headline, a \
clear date and time, and colours that match the mood of the event. Which one do you trust \
more? Which one makes you want to attend? That difference — the trust, the attention, the \
"want to attend" feeling — is what good graphic design creates.

Now let's walk through it step by step, using that same flyer example. First, the designer \
decides on ONE main message (e.g. "Free Career Workshop, Saturday 10am"). Second, they pick \
one bold font for that message so it's the first thing your eye lands on. Third, they choose \
two or three colours that work well together — never more, or it starts to feel noisy. \
Fourth, they leave empty space around the text on purpose, because empty space (designers \
call it "white space") helps the eye rest and actually makes the important text easier to \
read, not harder. Finally, they place a smaller line of supporting details (location, who \
it's for) below the main message, in a smaller size, so there's a clear order of importance.

Here's a small exercise before you move on: open any social media app right now and find \
one flyer, ad, or poster. Look at it for 10 seconds and ask yourself — what is the ONE main \
message it wants me to notice first? If you can answer that in one sentence, that flyer did \
its job.

For your practice task: find three flyers or posters online (a quick search for "event \
flyer" works well) and, for each one, write one sentence describing what you think its main \
message is, and one sentence about whether the design makes that message easy or hard to \
find.

To sum up: graphic design isn't about being "artistic" — it's about communicating one clear \
idea using images, text, colour, and space, on purpose. Every choice a designer makes should \
answer the question "does this help my main message stand out?" Keep that question in mind \
for every lesson from here on — it's the single most useful habit you'll build in this \
course."""

LESSON_2_CONTENT = """In your first lesson, you learned that graphic design is about \
communicating one clear message on purpose. In this lesson, we'll go one level deeper: \
colour, and how to choose colours that work well together, even if you've never studied \
colour theory before.

Here's the concept in plain terms: colours can feel "friendly" together or "fight" with \
each other, depending on where they sit on something called the colour wheel — a circle \
that arranges all colours in order (red, orange, yellow, green, blue, purple, and back to \
red). You don't need to memorise the wheel today. You just need three simple combination \
rules that professional designers rely on constantly.

Why does this matter? Because the wrong colour combination can make even a great message \
hard to read, or make a design feel unprofessional — even if everything else about it is \
well done. Getting colour right is one of the fastest ways to make your work look more \
polished, immediately.

Real-life example: think about a "Sale" sign in a shop window. It's almost always red or \
orange text on a white or yellow background — never, say, dark blue text on a dark green \
background. That's not an accident. Red and orange are "warm" colours that grab attention \
fast, and pairing them with a light background keeps the text easy to read from a distance. \
The shop owner (or their designer) chose that combination on purpose, using the same rules \
you're about to learn.

Let's go step by step through the three rules. Rule one: complementary colours — pick two \
colours from opposite sides of the colour wheel (like blue and orange, or red and green). \
These create strong contrast and are great for making one element (like a "Buy Now" button) \
pop against a calmer background. Rule two: analogous colours — pick two or three colours \
that sit next to each other on the wheel (like blue, teal, and green). These feel calm and \
harmonious, and work well for backgrounds or anything that shouldn't shout for attention. \
Rule three: the 60-30-10 split — once you've picked your colours, use one as 60% of the \
design (the dominant background colour), a second as 30% (supporting elements), and a third \
as just 10% (small accents, like a button or an icon). This split alone makes almost any \
colour combination look intentional rather than random.

Try this exercise right now: think of your favourite brand (a phone company, a drink, a \
football club). Picture its logo. Can you name its two main colours? Are they complementary, \
or analogous? Most strong brands only use two or three colours, consistently, everywhere.

For your practice task: using Canva (the free version works fine) or even paper and coloured \
pens, create three small colour palettes of three colours each — one complementary, one \
analogous, and one using the 60-30-10 idea. Label which is which. There's no need to design \
anything else yet — just the palettes.

To sum up: you now have three simple, professional rules for choosing colours — \
complementary for contrast, analogous for harmony, and the 60-30-10 split for balance. Try \
applying one of these rules the next time you're picking colours for anything, and notice \
how much more "put together" the result feels."""

ASSIGNMENT_DESCRIPTION = """Using Canva, Photoshop, or even a pen-and-paper sketch you \
photograph afterwards, design ONE simple event flyer for a made-up event of your choice \
(a workshop, a birthday, a product launch — anything). Your flyer must include: one clear \
main message, no more than three colours (applying what you learned about colour \
combinations), and clear visual hierarchy (the most important text should be the biggest / \
boldest). Submit a short write-up explaining: what your main message was, which colour rule \
you used, and why you arranged the text the way you did."""

QUIZ_QUESTIONS = [
    {
        "text": "What is the main goal of graphic design, according to this module?",
        "choices": [
            ("Communicating one clear message on purpose", True),
            ("Using as many colours and fonts as possible", False),
            ("Making something look artistic, regardless of clarity", False),
            ("Copying whatever design is currently trending", False),
        ],
    },
    {
        "text": "Which colour pairing is described as 'complementary'?",
        "choices": [
            ("Two colours from opposite sides of the colour wheel", True),
            ("Two colours that sit right next to each other on the wheel", False),
            ("Any two shades of the same colour", False),
            ("Black and white only", False),
        ],
    },
    {
        "text": "In the 60-30-10 rule, what does the 60% represent?",
        "choices": [
            ("The dominant background colour", True),
            ("The smallest accent colour, like a button", False),
            ("The font size of the headline", False),
            ("The amount of white space on the page", False),
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Seeds one fully-authored, published showcase module (Getting Started with "
        "Design Thinking) into the Graphic Design course, demonstrating the required "
        "lesson-quality standard end to end. Idempotent — safe to re-run."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        ensure_default_courses()
        try:
            course = Course.objects.get(slug="graphic-design")
        except Course.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                "Graphic Design course not found — run this after the app has migrated."
            ))
            return

        next_order = (course.modules.order_by("-order").values_list("order", flat=True).first() or 0) + 1

        if course.modules.filter(title="Getting Started with Design Thinking").exists():
            self.stdout.write(self.style.WARNING(
                "Showcase module already exists — nothing to do (safe to re-run)."
            ))
            return

        module = Module.objects.create(
            course=course,
            title="Getting Started with Design Thinking",
            description=(
                "What graphic design actually is, why it matters, and how to choose "
                "colours that work well together — no prior experience needed."
            ),
            order=next_order,
            status="published",
            is_ai_generated=False,
        )

        Lesson.objects.create(
            module=module, title="What Is Graphic Design, Really?",
            content=LESSON_1_CONTENT, order=1,
        )
        Lesson.objects.create(
            module=module, title="Choosing Colours That Work Together",
            content=LESSON_2_CONTENT, order=2,
        )

        Assignment.objects.create(
            course=course, module=module,
            title="Design Your First Event Flyer",
            description=ASSIGNMENT_DESCRIPTION,
        )

        quiz = Quiz.objects.create(module=module, title="Module 1 Quiz", pass_percent=70)
        for i, q in enumerate(QUIZ_QUESTIONS, start=1):
            question = QuizQuestion.objects.create(quiz=quiz, text=q["text"], order=i)
            for choice_text, is_correct in q["choices"]:
                QuizChoice.objects.create(question=question, text=choice_text, is_correct=is_correct)

        self.stdout.write(self.style.SUCCESS(
            "Seeded 'Getting Started with Design Thinking' — 2 lessons, 1 practical "
            "assignment, 1 quiz — published and ready for students."
        ))
