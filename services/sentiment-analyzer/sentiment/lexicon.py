"""Hand-curated Persian sentiment lexicon for Play Store review text.

See README.md ("Why a lexicon, not a model") for why this project uses a
lexicon/rule-based classifier rather than a pretrained transformer model.

Words are collected empirically from a manual sample of this project's own
`reviews` table (mostly short, colloquial reviews of Iranian apps) rather
than translated from an English sentiment list, since colloquial spoken-style
Persian differs a lot from formal written Persian (e.g. the "ه" copula
suffix: "خوبه" / "عالیه" / "بده" is how "خوب است" / "عالی است" / "بد است"
("it is good" / "excellent" / "bad") actually gets typed in a review).
Common colloquial spellings are therefore listed as their own entries
instead of relying on a stemmer to strip them.

Weights: 2 = strong sentiment, 1 = mild/ordinary sentiment. Only the sign
matters for the final 3-way decision (see classifier.py); the magnitude
only matters when intensifiers/negation are combined or multiple sentiment
words appear in the same review.
"""

POSITIVE_WORDS: dict[str, int] = {
    # excellent / great
    "عالی": 2,
    "عالیه": 2,
    "عالیست": 2,
    "فوق‌العاده": 2,
    "فوقالعاده": 2,
    "محشر": 2,
    "معرکه": 2,
    "بی‌نظیر": 2,
    "بینظیر": 2,
    "درجه‌یک": 2,
    # good / nice
    "خوب": 1,
    "خوبه": 1,
    "خوبیه": 1,
    "خوبی": 1,
    "قشنگ": 1,
    "قشنگه": 1,
    "زیبا": 1,
    "زیباست": 1,
    "روان": 1,
    "کاربردی": 1,
    "راضی": 1,
    "راضیم": 1,
    "سرگرم‌کننده": 1,
    "سرگرمکننده": 1,
    # gratitude / praise, common in reviews
    "ممنون": 1,
    "متشکرم": 1,
    "تشکر": 1,
    "آفرین": 1,
    "افرین": 1,
    "عاشقشم": 2,
    "عاشقتم": 2,
    # English loanwords that show up verbatim in this dataset
    "good": 1,
    "nice": 1,
    "great": 2,
    "excellent": 2,
    "perfect": 2,
}

NEGATIVE_WORDS: dict[str, int] = {
    # disaster / garbage
    "افتضاح": 2,
    "افتضاحه": 2,
    "مزخرف": 2,
    "مزخرفه": 2,
    "داغون": 2,
    "داغونه": 2,
    "داغونی": 2,
    "چرت": 2,
    "چرته": 2,
    # bad / broken / weak
    "بد": 1,
    "بده": 1,
    "خراب": 1,
    "خرابه": 1,
    "خرابی": 1,
    "ضعیف": 1,
    "ضعیفه": 1,
    "کند": 1,
    "بی‌کیفیت": 1,
    "بیکیفیت": 1,
    # complaints common in app reviews
    "مسدود": 1,
    "قطع": 1,
    "باگ": 1,
    "باگه": 1,
    "کلاهبرداری": 2,
    "کلاهبرداره": 2,
    "دزدی": 2,
    "دزد": 2,
    "زباله": 2,
    "هک": 1,
    "تبلیغ": 1,
    "تبلیغات": 1,
    "وحشتناک": 2,
    "نمیشه": 1,
    "نمیاد": 1,
    "نمیکنه": 1,
    # English loanwords
    "bad": 1,
    "terrible": 2,
    "awful": 2,
    "worst": 2,
    "garbage": 2,
}

# Present in the lexicon with weight 0: if one of these is the *only* signal
# found in a review, the review is neutral on its own merits rather than
# "neutral because nothing matched" -- both end in the same label today, but
# keeping them listed documents that they were considered, and stops them
# from being treated as unknown/filler tokens if the scoring logic ever
# changes to distinguish "no opinion words" from "an explicitly lukewarm one".
NEUTRAL_WORDS: dict[str, int] = {
    "متوسط": 0,
    "متوسطه": 0,
    "معمولی": 0,
    "خنثی": 0,
    "okay": 0,
    "ok": 0,
}

# Words that flip the sign of a nearby sentiment word. Persian negation
# usually follows the word it negates ("خوب نیست" = "[it's] not good"),
# unlike English, so the classifier checks *both* directions around a
# sentiment word, not just what precedes it.
NEGATION_WORDS: set[str] = {
    "نیست",
    "نبود",
    "نداره",
    "ندارد",
    "نه",
    "هیچ",
    "اصلا",
    "اصلاً",
    "ابدا",
    "ابداً",
}

# Words that scale up a neighboring sentiment word's weight. Persian
# intensifiers precede the word they modify ("خیلی خوب" = "very good").
INTENSIFIER_WORDS: dict[str, float] = {
    "خیلی": 1.5,
    "بسیار": 1.5,
    "واقعا": 1.5,
    "واقعاً": 1.5,
    "کاملا": 1.5,
    "کاملاً": 1.5,
    "فوق": 1.3,
}

# Emoji are tokenized as their own tokens by hazm's word_tokenize, so they can
# be scored the same way as words. Deliberately excludes 😂/🤣: in this
# dataset they show up at least as often as sarcasm about a complaint (e.g.
# mocking a paywall) as they do genuine amusement, so treating them as
# positive would misclassify more reviews than it correctly labels.
EMOJI_SCORES: dict[str, int] = {
    "👍": 1,
    "👌": 1,
    "❤️": 1,
    "🧡": 1,
    "💛": 1,
    "💚": 1,
    "💙": 1,
    "💜": 1,
    "💕": 1,
    "💟": 1,
    "😍": 2,
    "🥰": 2,
    "😊": 1,
    "💯": 1,
    "🔥": 1,
    "👎": -1,
    "💔": -2,
    "😡": -2,
    "😢": -1,
    "😭": -1,
    "🤮": -2,
}
