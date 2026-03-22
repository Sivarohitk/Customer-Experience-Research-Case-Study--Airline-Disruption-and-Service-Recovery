"""Score airline feedback sentiment with a lightweight reproducible lexicon approach."""

from argparse import ArgumentParser
from pathlib import Path
import re

import pandas as pd

from .config import (
    CODED_FILE,
    SENTIMENT_BY_THEME_FILE,
    SENTIMENT_FILE,
    SENTIMENT_METHOD_NOTE_FILE,
    SENTIMENT_SUMMARY_FILE,
)
from .theme_rules import THEME_RULES
from .utils import read_csv, write_csv


POSITIVE_PHRASE_WEIGHTS = {
    "handled well": 2.0,
    "resolved quickly": 2.0,
    "clear updates": 1.5,
    "helpful": 1.5,
    "kind": 1.0,
    "friendly": 1.0,
    "professional": 1.0,
    "made it right": 2.0,
    "better than expected": 1.5,
    "solid recovery": 1.5,
    "rebooked me": 1.5,
    "apologized": 1.0,
    "worked well": 1.0,
    "easy to follow": 1.0,
    "efficient": 1.0,
}

NEGATIVE_PHRASE_WEIGHTS = {
    "cancelled": -2.0,
    "canceled": -2.0,
    "stranded": -2.5,
    "delay": -1.2,
    "delayed": -1.2,
    "missed connection": -1.8,
    "confusing": -1.5,
    "frustrating": -1.8,
    "no updates": -2.0,
    "conflicting information": -2.0,
    "no explanation": -1.7,
    "refund took": -1.5,
    "lost bag": -2.0,
    "lost luggage": -2.0,
    "baggage did not arrive": -2.0,
    "customer support": -0.7,
    "on hold": -1.5,
    "transferred": -1.2,
    "website crashed": -1.8,
    "app kept": -1.3,
    "not helpful": -1.7,
    "unhelpful": -1.7,
    "painful": -1.5,
    "impossible": -1.8,
    "chaotic": -1.5,
    "poor": -1.0,
    "slow": -1.0,
    "terrible": -2.0,
    "awful": -2.0,
}

POSITIVE_WORD_WEIGHTS = {
    "clear": 0.6,
    "helped": 0.8,
    "helpful": 0.9,
    "easy": 0.6,
    "resolved": 0.8,
    "smooth": 0.8,
    "polite": 0.4,
    "professional": 0.6,
    "apology": 0.4,
    "friendly": 0.4,
}

NEGATIVE_WORD_WEIGHTS = {
    "delay": -0.8,
    "cancelled": -1.4,
    "canceled": -1.4,
    "stranded": -1.8,
    "confusing": -1.0,
    "frustrating": -1.2,
    "refund": -0.6,
    "voucher": -0.4,
    "baggage": -0.8,
    "luggage": -0.8,
    "lost": -1.1,
    "painful": -1.0,
    "slow": -0.7,
    "late": -0.6,
    "chaos": -1.0,
    "poor": -0.8,
    "stuck": -0.9,
}

NEGATION_WORDS = {"no", "not", "never", "without", "hardly"}


def tokenize(text: str) -> list[str]:
    """Tokenize normalized text into simple lowercase words."""
    return re.findall(r"[a-z0-9]+", str(text).lower())


def parse_boolean_like(value: object) -> object:
    """Normalize boolean-like values from CSVs into real booleans."""
    if pd.isna(value):
        return pd.NA
    text = str(value).strip().lower()
    if text in {"true", "1", "1.0", "yes", "y"}:
        return True
    if text in {"false", "0", "0.0", "no", "n"}:
        return False
    return pd.NA


def normalized_text(row: pd.Series) -> str:
    """Prefer the existing normalized text field and fall back safely if needed."""
    value = row.get("clean_text")
    if pd.notna(value):
        return str(value)
    fallback = row.get("analysis_text") if pd.notna(row.get("analysis_text")) else row.get("feedback_text", "")
    return re.sub(r"[^a-z0-9\s]", " ", str(fallback).lower())


def score_phrase_matches(text: str, phrase_weights: dict[str, float]) -> tuple[float, list[str]]:
    """Score phrase occurrences and return matched lexicon evidence."""
    score = 0.0
    evidence: list[str] = []
    for phrase, weight in phrase_weights.items():
        pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, text):
            score += weight
            evidence.append(phrase)
    return score, evidence


def score_word_matches(tokens: list[str], word_weights: dict[str, float]) -> tuple[float, list[str]]:
    """Score token-level sentiment with basic negation handling."""
    score = 0.0
    evidence: list[str] = []
    for index, token in enumerate(tokens):
        if token not in word_weights:
            continue
        weight = word_weights[token]
        window = tokens[max(0, index - 2) : index]
        if any(word in NEGATION_WORDS for word in window):
            weight *= -1
            evidence.append(f"negated:{token}")
        else:
            evidence.append(token)
        score += weight
    return score, evidence


def adjust_with_structured_signals(row: pd.Series, score: float) -> tuple[float, list[str]]:
    """Use existing structured signals to slightly calibrate the sentiment score."""
    evidence: list[str] = []

    rating = row.get("rating")
    if pd.notna(rating):
        rating_value = float(rating)
        if rating_value <= 2:
            score -= 1.2
            evidence.append("rating<=2")
        elif rating_value >= 4:
            score += 0.8
            evidence.append("rating>=4")

    recommended = row.get("recommended")
    recommended = parse_boolean_like(recommended)
    if pd.notna(recommended):
        if recommended is True:
            score += 0.6
            evidence.append("recommended_true")
        else:
            score -= 0.8
            evidence.append("recommended_false")

    likely_negative = row.get("likely_negative_experience")
    likely_negative = parse_boolean_like(likely_negative)
    if pd.notna(likely_negative) and likely_negative is True:
        score -= 0.6
        evidence.append("likely_negative_experience")

    return score, evidence


def label_sentiment(score: float) -> str:
    """Map a continuous score into portfolio-friendly sentiment categories."""
    if score >= 1.0:
        return "positive"
    if score <= -1.0:
        return "negative"
    return "neutral"


def score_review(row: pd.Series) -> tuple[float, str, str]:
    """Generate sentiment score, label, and evidence for one review."""
    text = normalized_text(row)
    tokens = tokenize(text)

    positive_phrase_score, positive_phrases = score_phrase_matches(text, POSITIVE_PHRASE_WEIGHTS)
    negative_phrase_score, negative_phrases = score_phrase_matches(text, NEGATIVE_PHRASE_WEIGHTS)
    positive_word_score, positive_words = score_word_matches(tokens, POSITIVE_WORD_WEIGHTS)
    negative_word_score, negative_words = score_word_matches(tokens, NEGATIVE_WORD_WEIGHTS)

    score = positive_phrase_score + negative_phrase_score + positive_word_score + negative_word_score
    score, structured_evidence = adjust_with_structured_signals(row, score)
    score = round(score, 2)
    label = label_sentiment(score)

    evidence = positive_phrases + negative_phrases + positive_words + negative_words + structured_evidence
    evidence_text = "; ".join(dict.fromkeys(evidence))
    return score, label, evidence_text


def build_overall_summary(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize sentiment distribution across all reviews."""
    summary = (
        scored_df.groupby("sentiment_label", dropna=False)
        .agg(
            count=("review_id", "count"),
            avg_sentiment_score=("sentiment_score", "mean"),
        )
        .reset_index()
        .rename(columns={"sentiment_label": "sentiment"})
    )
    total = len(scored_df)
    summary["share_of_reviews_pct"] = summary["count"].apply(
        lambda count: round((count / total) * 100, 2) if total else 0.0
    )
    summary["avg_sentiment_score"] = summary["avg_sentiment_score"].round(2)
    order = {"negative": 0, "neutral": 1, "positive": 2}
    summary["sort_order"] = summary["sentiment"].map(order).fillna(99)
    return summary.sort_values("sort_order").drop(columns=["sort_order"]).reset_index(drop=True)


def build_sentiment_by_theme_summary(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize sentiment metrics for each qualitative theme."""
    rows: list[dict[str, object]] = []
    for theme in THEME_RULES:
        indicator = f"theme__{re.sub(r'[^a-z0-9]+', '_', theme.lower()).strip('_')}"
        if indicator not in scored_df.columns:
            continue

        subset = scored_df[scored_df[indicator] == 1].copy()
        if subset.empty:
            rows.append(
                {
                    "theme": theme,
                    "review_count": 0,
                    "avg_sentiment_score": pd.NA,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "positive_count": 0,
                    "negative_share_pct": 0.0,
                    "most_common_sentiment": pd.NA,
                }
            )
            continue

        counts = subset["sentiment_label"].value_counts().to_dict()
        negative_count = int(counts.get("negative", 0))
        neutral_count = int(counts.get("neutral", 0))
        positive_count = int(counts.get("positive", 0))
        review_count = int(len(subset))
        negative_share = round((negative_count / review_count) * 100, 2) if review_count else 0.0
        common_sentiment = subset["sentiment_label"].mode()

        rows.append(
            {
                "theme": theme,
                "review_count": review_count,
                "avg_sentiment_score": round(subset["sentiment_score"].mean(), 2),
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "positive_count": positive_count,
                "negative_share_pct": negative_share,
                "most_common_sentiment": common_sentiment.iloc[0] if not common_sentiment.empty else pd.NA,
            }
        )

    summary = pd.DataFrame(rows)
    summary = summary.sort_values(
        ["negative_share_pct", "avg_sentiment_score", "review_count"],
        ascending=[False, True, False],
    ).reset_index(drop=True)
    return summary


def build_method_note(scored_df: pd.DataFrame, theme_summary: pd.DataFrame) -> str:
    """Write a short portfolio-friendly note about the sentiment method."""
    most_negative = theme_summary.head(5)
    lines = [
        "# Sentiment Method Note",
        "",
        "## Why This Method Fits The Project",
        "- The project uses a lightweight lexicon-based sentiment scorer with airline-specific words and phrases instead of a heavy external model.",
        "- It is reproducible, easy to run locally, and easy to explain in a portfolio or interview setting.",
        "- The scorer combines review text with a few structured cues already in the dataset, such as rating and recommendation status, to produce more stable labels.",
        "",
        "## What The Outputs Show",
        f"- Reviews scored: {len(scored_df)}",
        "- Sentiment categories: positive, neutral, negative",
        "- Theme-level sentiment summary highlights which qualitative themes are most associated with negative sentiment.",
        "- Most negative themes in the current run:",
        *[
            f"  - {row.theme}: {row.negative_share_pct:.2f}% negative, average score {row.avg_sentiment_score}"
            for row in most_negative.itertuples()
        ],
        "",
        "## Limitations",
        "- Off-the-shelf sentiment logic can miss sarcasm, mixed sentiment, and context-specific airline language.",
        "- Reviews about disruptions often contain both negative events and positive recovery actions, which can compress into a neutral score.",
        "- Some words such as `delay`, `refund`, or `support` may describe the topic of a review rather than its emotional tone.",
        "- The method is useful as a first-pass signal, but it should be validated against hand-labeled examples before being treated as a strong research claim.",
        "",
    ]
    return "\n".join(lines)


def analyze_sentiment(
    input_path: Path = CODED_FILE,
    output_path: Path = SENTIMENT_FILE,
    summary_path: Path = SENTIMENT_SUMMARY_FILE,
    theme_summary_path: Path = SENTIMENT_BY_THEME_FILE,
    note_path: Path = SENTIMENT_METHOD_NOTE_FILE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Add sentiment scores and labels, then write overall and theme-level summaries."""

    df = read_csv(input_path).copy()
    scores = df.apply(score_review, axis=1)

    scored_df = df.copy()
    scored_df["sentiment_score"] = scores.apply(lambda value: value[0])
    scored_df["sentiment_label"] = scores.apply(lambda value: value[1])
    scored_df["sentiment_evidence"] = scores.apply(lambda value: value[2])

    overall_summary = build_overall_summary(scored_df)
    theme_summary = build_sentiment_by_theme_summary(scored_df)

    write_csv(scored_df, output_path)
    write_csv(overall_summary, summary_path)
    write_csv(theme_summary, theme_summary_path)
    note_path.write_text(build_method_note(scored_df, theme_summary), encoding="utf-8")

    return scored_df, overall_summary, theme_summary


def main() -> None:
    """Run the sentiment-analysis step directly from the command line."""
    parser = ArgumentParser(description="Analyze sentiment in airline feedback.")
    parser.add_argument("--input", type=str, default=str(CODED_FILE))
    args = parser.parse_args()

    scored, overall, by_theme = analyze_sentiment(Path(args.input))
    print(f"Scored {len(scored)} rows")
    print(f"Wrote overall sentiment summary to {SENTIMENT_SUMMARY_FILE}")
    print(f"Wrote theme-level sentiment summary to {SENTIMENT_BY_THEME_FILE}")
    print(f"Wrote sentiment method note to {SENTIMENT_METHOD_NOTE_FILE}")
    print(f"Most negative theme: {by_theme.iloc[0]['theme'] if not by_theme.empty else 'n/a'}")


if __name__ == "__main__":
    main()
