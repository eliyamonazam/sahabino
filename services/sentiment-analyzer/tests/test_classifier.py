"""Classification-decision tests against hand-picked, real-style Persian
review text (some copied near-verbatim from this project's own `reviews`
table). No mocking is needed here: the classifier is a plain lexicon/rule
engine with no heavy model dependency to isolate tests from (see README.md
for why that approach was chosen), so these tests exercise the real
preprocessing + scoring path end to end.
"""

from sentiment.classifier import classify_sentiment, score_tokens


class TestClearlyPositive:
    def test_single_word_praise(self):
        assert classify_sentiment("عالی") == "positive"

    def test_colloquial_copula_form(self):
        assert classify_sentiment("خیلی خوبیه، ممنون از سازنده") == "positive"

    def test_elongated_praise(self):
        # A common way reviewers emphasize praise: stretching the word out.
        assert classify_sentiment("عالیییییی نصبش کنید حتما") == "positive"

    def test_intensified_praise(self):
        assert classify_sentiment("بسیار عالی و کاربردی") == "positive"

    def test_positive_emoji_only(self):
        assert classify_sentiment("👍👍") == "positive"

    def test_negation_of_a_negative_word_reads_positive(self):
        # "بد نیست" ("[it's] not bad") -- Persian negation follows the word
        # it negates, unlike English.
        assert classify_sentiment("بد نیست من بهش ۱۰۰ هزار ستاره میدم") == "positive"

    def test_english_loanword(self):
        assert classify_sentiment("very good") == "positive"


class TestClearlyNegative:
    def test_single_word_complaint(self):
        assert classify_sentiment("افتضاحه") == "negative"

    def test_negation_of_a_positive_word_reads_negative(self):
        assert classify_sentiment("خوب نیست کد نمی‌ده تا تلگرام نصب بشه") == "negative"

    def test_account_blocked_complaint(self):
        assert classify_sentiment("حساب من مسدود شده و پشتیبانی جواب نمیده") == "negative"

    def test_theft_complaint(self):
        assert classify_sentiment("ایرانسل دزدی می‌کنه") == "negative"

    def test_negative_emoji_only(self):
        assert classify_sentiment("😡") == "negative"

    def test_wont_install(self):
        assert classify_sentiment("نصب نمیشه") == "negative"


class TestNeutralOrMixed:
    def test_no_opinion_words(self):
        assert classify_sentiment("سید احمد") == "neutral"

    def test_empty_content(self):
        assert classify_sentiment("") == "neutral"

    def test_none_content(self):
        assert classify_sentiment(None) == "neutral"

    def test_neither_good_nor_bad_cancels_out(self):
        assert classify_sentiment("نه خوب نه بد") == "neutral"

    def test_a_request_with_no_sentiment_words(self):
        assert classify_sentiment("لطفاً رمز واتساپ من را ارسال کنین") == "neutral"

    def test_ambiguous_laughing_emoji_is_not_treated_as_positive(self):
        # In this dataset 😂/🤣 show up mocking a complaint about as often as
        # they show up as genuine amusement -- deliberately excluded from
        # the emoji lexicon (see lexicon.py), so a review that is otherwise
        # signal-free stays neutral rather than being guessed as positive.
        assert classify_sentiment("🤣🤣🤣") == "neutral"


class TestScoringInternals:
    def test_intensifier_scales_up_magnitude_without_flipping_sign(self):
        base = score_tokens(["خوب"])
        intensified = score_tokens(["خیلی", "خوب"])
        assert intensified > base > 0

    def test_negation_flips_sign_regardless_of_direction(self):
        assert score_tokens(["خوب", "نیست"]) < 0
        assert score_tokens(["نیست", "خوب"]) < 0

    def test_negation_only_applies_within_the_window(self):
        # "نیست" four tokens away from "خوب" is out of range and shouldn't
        # affect it.
        far_apart = ["خوب", "الف", "ب", "پ", "ت", "نیست"]
        assert score_tokens(far_apart) > 0
