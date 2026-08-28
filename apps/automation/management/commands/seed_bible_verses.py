from django.core.management.base import BaseCommand

from apps.automation.models import BibleVerse

# A curated starter pool (KJV/public-domain-style phrasing) so the daily
# verse feature works offline with zero external dependencies or API
# keys. Add, edit, or remove verses from the admin at any time — this
# command is idempotent (safe to re-run) and only fills in ones that
# are missing.
DEFAULT_VERSES = [
    ("Philippians 4:13", "I can do all things through Christ which strengtheneth me."),
    ("Jeremiah 29:11", "For I know the thoughts that I think toward you, saith the LORD, thoughts of peace, and not of evil, to give you an expected end."),
    ("Psalm 23:1", "The LORD is my shepherd; I shall not want."),
    ("Proverbs 3:5-6", "Trust in the LORD with all thine heart; and lean not unto thine own understanding. In all thy ways acknowledge him, and he shall direct thy paths."),
    ("Isaiah 41:10", "Fear thou not; for I am with thee: be not dismayed; for I am thy God: I will strengthen thee; yea, I will help thee."),
    ("Joshua 1:9", "Have not I commanded thee? Be strong and of a good courage; be not afraid, neither be thou dismayed: for the LORD thy God is with thee whithersoever thou goest."),
    ("Romans 8:28", "And we know that all things work together for good to them that love God, to them who are the called according to his purpose."),
    ("Psalm 46:1", "God is our refuge and strength, a very present help in trouble."),
    ("Matthew 6:33", "But seek ye first the kingdom of God, and his righteousness; and all these things shall be added unto you."),
    ("2 Timothy 1:7", "For God hath not given us the spirit of fear; but of power, and of love, and of a sound mind."),
    ("Psalm 118:24", "This is the day which the LORD hath made; we will rejoice and be glad in it."),
    ("Galatians 6:9", "And let us not be weary in well doing: for in due season we shall reap, if we faint not."),
    ("Proverbs 16:3", "Commit thy works unto the LORD, and thy thoughts shall be established."),
    ("Isaiah 40:31", "But they that wait upon the LORD shall renew their strength; they shall mount up with wings as eagles."),
    ("John 14:27", "Peace I leave with you, my peace I give unto you: not as the world giveth, give I unto you. Let not your heart be troubled, neither let it be afraid."),
    ("Psalm 37:4", "Delight thyself also in the LORD; and he shall give thee the desires of thine heart."),
    ("Philippians 4:6-7", "Be careful for nothing; but in every thing by prayer and supplication with thanksgiving let your requests be made known unto God."),
    ("Romans 12:2", "And be not conformed to this world: but be ye transformed by the renewing of your mind, that ye may prove what is that good, and acceptable, and perfect, will of God."),
    ("Psalm 34:18", "The LORD is nigh unto them that are of a broken heart; and saveth such as be of a contrite spirit."),
    ("Deuteronomy 31:6", "Be strong and of a good courage, fear not, nor be afraid of them: for the LORD thy God, he it is that doth go with thee; he will not fail thee, nor forsake thee."),
    ("James 1:5", "If any of you lack wisdom, let him ask of God, that giveth to all men liberally, and upbraideth not; and it shall be given him."),
    ("Psalm 27:1", "The LORD is my light and my salvation; whom shall I fear? the LORD is the strength of my life; of whom shall I be afraid?"),
    ("1 Corinthians 13:4-5", "Charity suffereth long, and is kind; charity envieth not; charity vaunteth not itself, is not puffed up."),
    ("Proverbs 18:10", "The name of the LORD is a strong tower: the righteous runneth into it, and is safe."),
    ("Psalm 121:1-2", "I will lift up mine eyes unto the hills, from whence cometh my help. My help cometh from the LORD, which made heaven and earth."),
    ("Matthew 11:28", "Come unto me, all ye that labour and are heavy laden, and I will give you rest."),
    ("Romans 15:13", "Now the God of hope fill you with all joy and peace in believing, that ye may abound in hope, through the power of the Holy Ghost."),
    ("Psalm 143:8", "Cause me to hear thy lovingkindness in the morning; for in thee do I trust: cause me to know the way wherein I should walk."),
    ("Nahum 1:7", "The LORD is good, a strong hold in the day of trouble; and he knoweth them that trust in him."),
    ("Colossians 3:23", "And whatsoever ye do, do it heartily, as to the Lord, and not unto men."),
]


class Command(BaseCommand):
    help = "Seed the default pool of daily Bible verses (idempotent — safe to re-run)."

    def handle(self, *args, **options):
        created_count = 0
        for reference, text in DEFAULT_VERSES:
            _, created = BibleVerse.objects.get_or_create(
                reference=reference, defaults={"text": text, "is_active": True}
            )
            if created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created_count} new verses created "
            f"({len(DEFAULT_VERSES) - created_count} already existed)."
        ))
