"""Build quantitative summaries that complement the qualitative coding layer."""

from argparse import ArgumentParser
from itertools import combinations
from pathlib import Path
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

from .config import (
    FREQUENCY_FILE,
    NEGATIVE_PHRASE_FILE,
    PAIN_POINT_COMBINATIONS_FILE,
    QUANT_ANALYSIS_SUMMARY_FILE,
    RATING_DISTRIBUTION_FILE,
    SENTIMENT_BY_THEME_FILE,
    SENTIMENT_FILE,
    THEME_FREQUENCY_FILE,
    THEME_VS_AIRLINE_FILE,
    THEME_VS_RECOMMENDATION_FILE,
    THEME_VS_SENTIMENT_FILE,
)
from .theme_rules import THEME_RULES
from .utils import read_csv, write_csv


NEGATIVE_REVIEW_STOP_WORDS = ENGLISH_STOP_WORDS.union(
    {
        "airline",
        "flight",
        "flights",
        "review",
        "airways",
        "airport",
        "seat",
        "cabin",
        "class",
        "crew",
        "staff",
    }
)

# Keep a few generic airline words out of the top phrase list so the output
# highlights pain points instead of obvious domain terms.
FOCUS_COMBINATIONS = [
    ("cancellation stress", "poor communication"),
    ("delay frustration", "rebooking friction"),
    ("refund difficulty", "customer support responsiveness"),
]

PAIN_POINT_THEMES = {
    "delay frustration",
    "cancellation stress",
    "refund difficulty",
    "rebooking friction",
    "poor communication",
    "baggage problems",
    "customer support responsiveness",
    "pricing / compensation dissatisfaction",
    "digital / app / website issues",
    "trust / loyalty damage",
}

NEGATIVE_PHRASE_SEED_TERMS = [
    "customer service",
    "gate agent",
    "gate agents",
    "mobile app",
    "website",
    "wait time",
    "long wait",
    "missed connection",
    "lost bag",
    "lost luggage",
    "delayed bag",
    "bag claim",
    "refund process",
    "travel credit",
    "meal voucher",
    "hotel voucher",
]


def indicator_column(theme: str) -> str:
    """Convert a theme label into the review-level binary column name."""
    slug = re.sub(r"[^a-z0-9]+", "_", theme.lower()).strip("_")
    return f"theme__{slug}"


def parse_boolean_like(value: object) -> str:
    """Convert recommendation values into clean yes/no/unknown labels."""
    if pd.isna(value):
        return "unknown"
    text = str(value).strip().lower()
    if text in {"true", "1", "1.0", "yes", "y"}:
        return "yes"
    if text in {"false", "0", "0.0", "no", "n"}:
        return "no"
    return "unknown"


def build_theme_frequency_summary(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Count how often each theme appears in the review-level coded dataset."""
    total_reviews = len(scored_df)
    rows: list[dict[str, object]] = []

    for theme, rule in THEME_RULES.items():
        column = indicator_column(theme)
        count = int(scored_df[column].fillna(0).astype(int).sum()) if column in scored_df.columns else 0
        share = round((count / total_reviews) * 100, 2) if total_reviews else 0.0
        rows.append(
            {
                "theme": theme,
                "description": rule["description"],
                "count": count,
                "share_of_reviews_pct": share,
            }
        )

    return pd.DataFrame(rows).sort_values(["count", "theme"], ascending=[False, True]).reset_index(drop=True)


def build_negative_phrase_summary(scored_df: pd.DataFrame, max_features: int = 40) -> pd.DataFrame:
    """Extract high-signal disruption phrases from reviews labeled as negative."""
    negative_reviews = scored_df[scored_df["sentiment_label"] == "negative"].copy()
    texts = negative_reviews["clean_text"].fillna("")
    if texts.empty:
        return pd.DataFrame(columns=["term", "count"])

    candidate_terms = set(NEGATIVE_PHRASE_SEED_TERMS)
    for theme in PAIN_POINT_THEMES:
        candidate_terms.update(THEME_RULES.get(theme, {}).get("keywords", []))

    rows: list[dict[str, object]] = []
    total_negative = len(negative_reviews)
    for term in sorted(candidate_terms):
        normalized_term = term.strip().lower()
        if len(normalized_term) < 4:
            continue
        pattern = r"\b" + re.escape(normalized_term).replace(r"\ ", r"\s+") + r"\b"
        count = int(texts.str.contains(pattern, regex=True, na=False).sum())
        if count == 0:
            continue
        rows.append(
            {
                "term": normalized_term,
                "count": count,
                "share_of_negative_reviews_pct": round((count / total_negative) * 100, 2) if total_negative else 0.0,
                "source": "seeded_phrase_count",
            }
        )

    if rows:
        return (
            pd.DataFrame(rows)
            .sort_values(["count", "term"], ascending=[False, True])
            .head(max_features)
            .reset_index(drop=True)
        )

    texts_list = [text for text in texts.tolist() if str(text).strip()]
    if not texts_list:
        return pd.DataFrame(columns=["term", "count"])

    # Fallback to general n-gram extraction if the seeded phrase list finds no matches.
    min_df = 3 if len(texts) >= 500 else 2 if len(texts) >= 100 else 1
    vectorizer = CountVectorizer(
        stop_words=list(NEGATIVE_REVIEW_STOP_WORDS),
        ngram_range=(1, 2),
        max_features=max_features,
        min_df=min_df,
    )
    try:
        matrix = vectorizer.fit_transform(texts_list)
    except ValueError:
        return pd.DataFrame(columns=["term", "count"])
    counts = np.asarray(matrix.sum(axis=0)).ravel()

    return (
        pd.DataFrame({"term": vectorizer.get_feature_names_out(), "count": counts})
        .sort_values("count", ascending=False)
        .reset_index(drop=True)
    )


def build_rating_distribution_summary(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize the observed rating distribution without assuming a single rating scale."""
    rated = scored_df[scored_df["rating"].notna()].copy()
    if rated.empty:
        return pd.DataFrame(columns=["rating", "rating_bucket", "count", "share_of_rated_reviews_pct"])

    distribution = (
        rated.groupby(["rating", "rating_bucket"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("rating")
        .reset_index(drop=True)
    )
    total_rated = int(distribution["count"].sum())
    distribution["share_of_rated_reviews_pct"] = distribution["count"].apply(
        lambda count: round((count / total_rated) * 100, 2) if total_rated else 0.0
    )
    return distribution


def expand_theme_rows(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Convert wide theme indicators into a long review-theme table for cross-tabs."""
    rows: list[pd.DataFrame] = []
    for theme in THEME_RULES:
        column = indicator_column(theme)
        if column not in scored_df.columns:
            continue

        indicator_values = pd.to_numeric(scored_df[column], errors="coerce").fillna(0).astype(int)
        subset = scored_df[indicator_values == 1].copy()
        if subset.empty:
            continue

        subset["theme"] = theme
        subset["recommendation_label"] = subset["recommended"].apply(parse_boolean_like)
        subset["airline"] = subset["airline"].fillna("Unknown airline")
        rows.append(
            subset[
                [
                    "review_id",
                    "theme",
                    "sentiment_label",
                    "airline",
                    "recommendation_label",
                    "rating",
                ]
            ]
        )

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def add_share_within_theme(df: pd.DataFrame, count_column: str = "count") -> pd.DataFrame:
    """Add percentage share within each theme for cleaner cross-tab interpretation."""
    if df.empty:
        return df
    totals = df.groupby("theme")[count_column].transform("sum")
    df = df.copy()
    df["share_within_theme_pct"] = np.where(totals > 0, (df[count_column] / totals) * 100, 0.0)
    df["share_within_theme_pct"] = df["share_within_theme_pct"].round(2)
    return df


def build_theme_vs_sentiment_crosstab(theme_rows: pd.DataFrame) -> pd.DataFrame:
    """Create a long-form theme by sentiment cross-tab."""
    if theme_rows.empty:
        return pd.DataFrame(columns=["theme", "sentiment", "count", "share_within_theme_pct"])
    crosstab = (
        theme_rows.groupby(["theme", "sentiment_label"], dropna=False)
        .size()
        .reset_index(name="count")
        .rename(columns={"sentiment_label": "sentiment"})
        .sort_values(["theme", "count"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return add_share_within_theme(crosstab)


def build_theme_vs_airline_crosstab(theme_rows: pd.DataFrame) -> pd.DataFrame:
    """Create a long-form theme by airline cross-tab."""
    if theme_rows.empty:
        return pd.DataFrame(columns=["theme", "airline", "count", "share_within_theme_pct"])
    crosstab = (
        theme_rows.groupby(["theme", "airline"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["theme", "count", "airline"], ascending=[True, False, True])
        .reset_index(drop=True)
    )
    return add_share_within_theme(crosstab)


def build_theme_vs_recommendation_crosstab(theme_rows: pd.DataFrame) -> pd.DataFrame:
    """Create a long-form theme by recommendation cross-tab."""
    if theme_rows.empty:
        return pd.DataFrame(columns=["theme", "recommendation", "count", "share_within_theme_pct"])
    crosstab = (
        theme_rows.groupby(["theme", "recommendation_label"], dropna=False)
        .size()
        .reset_index(name="count")
        .rename(columns={"recommendation_label": "recommendation"})
        .sort_values(["theme", "count"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return add_share_within_theme(crosstab)


def build_pain_point_combinations(scored_df: pd.DataFrame) -> pd.DataFrame:
    """Count common pairs of pain-point themes across reviews."""
    pair_counts: dict[tuple[str, str], int] = {}
    theme_order = list(THEME_RULES.keys())
    theme_columns = {
        theme: pd.to_numeric(scored_df[indicator_column(theme)], errors="coerce").fillna(0).astype(int)
        for theme in theme_order
        if theme in PAIN_POINT_THEMES and indicator_column(theme) in scored_df.columns
    }

    # A review can express more than one failure at once, so pair counts surface
    # common bundles of pain points that matter for service-recovery design.
    for row_index in scored_df.index:
        matched_themes = [
            theme
            for theme in theme_order
            if theme in theme_columns and int(theme_columns[theme].loc[row_index]) == 1
        ]
        for theme_a, theme_b in combinations(matched_themes, 2):
            pair_counts[(theme_a, theme_b)] = pair_counts.get((theme_a, theme_b), 0) + 1

    total_reviews = len(scored_df)
    rows: list[dict[str, object]] = []
    for pair in set(pair_counts) | set(FOCUS_COMBINATIONS):
        count = pair_counts.get(pair, 0)
        rows.append(
            {
                "theme_a": pair[0],
                "theme_b": pair[1],
                "combination_label": f"{pair[0]} + {pair[1]}",
                "count": count,
                "share_of_reviews_pct": round((count / total_reviews) * 100, 2) if total_reviews else 0.0,
                "is_focus_combination": pair in FOCUS_COMBINATIONS,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["is_focus_combination", "count", "combination_label"], ascending=[False, False, True])
        .reset_index(drop=True)
    )


def build_quantitative_summary_markdown(
    theme_frequency: pd.DataFrame,
    sentiment_by_theme: pd.DataFrame,
    negative_phrases: pd.DataFrame,
    rating_distribution: pd.DataFrame,
    pain_point_combinations: pd.DataFrame,
) -> str:
    """Create a concise markdown summary that can feed the final case-study report."""
    top_themes = theme_frequency.head(5)
    most_negative_themes = sentiment_by_theme.head(5) if not sentiment_by_theme.empty else pd.DataFrame()
    top_phrases = negative_phrases.head(10)
    top_combinations = pain_point_combinations.head(5)
    focus_pairs = pain_point_combinations[pain_point_combinations["is_focus_combination"]].head(10)

    lines = [
        "# Quantitative Analysis Summary",
        "",
        "## Theme Frequency",
        *[
            f"- {row.theme}: {int(row.count)} reviews ({row.share_of_reviews_pct:.2f}%)"
            for row in top_themes.itertuples()
        ],
        "",
        "## Most Negative Themes",
        *[
            f"- {row.theme}: {row.negative_share_pct:.2f}% negative sentiment, average score {row.avg_sentiment_score}"
            for row in most_negative_themes.itertuples()
        ],
        "",
        "## Top Phrases In Negative Reviews",
        *[f"- {row.term}: {int(row.count)}" for row in top_phrases.itertuples()],
        "",
        "## Rating Distribution Note",
        "- Ratings are summarized as observed because the public and synthetic datasets use different numeric ranges.",
        f"- Distinct rating values present: {rating_distribution['rating'].nunique() if not rating_distribution.empty else 0}",
        "",
        "## Common Pain-Point Combinations",
        *[
            f"- {row.combination_label}: {int(row.count)} reviews ({row.share_of_reviews_pct:.2f}%)"
            for row in top_combinations.itertuples()
        ],
        "",
        "## Focus Combination Checks",
        *[
            f"- {row.combination_label}: {int(row.count)} reviews ({row.share_of_reviews_pct:.2f}%)"
            for row in focus_pairs.itertuples()
        ],
        "",
    ]
    return "\n".join(lines)


def build_frequency_table(
    input_path: Path = SENTIMENT_FILE,
    output_path: Path = FREQUENCY_FILE,
    max_features: int = 40,
) -> pd.DataFrame:
    """
    Build the quantitative summary layer while preserving the old term-frequency output.

    The returned DataFrame is still a term-frequency table so existing
    visualization and report-generation steps continue to work unchanged.
    """

    scored_df = read_csv(input_path).copy()
    theme_frequency = build_theme_frequency_summary(scored_df)
    negative_phrases = build_negative_phrase_summary(scored_df, max_features=max_features)
    rating_distribution = build_rating_distribution_summary(scored_df)
    theme_rows = expand_theme_rows(scored_df)
    theme_vs_sentiment = build_theme_vs_sentiment_crosstab(theme_rows)
    theme_vs_airline = build_theme_vs_airline_crosstab(theme_rows)
    theme_vs_recommendation = build_theme_vs_recommendation_crosstab(theme_rows)
    pain_point_combinations = build_pain_point_combinations(scored_df)

    sentiment_by_theme = read_csv(SENTIMENT_BY_THEME_FILE) if SENTIMENT_BY_THEME_FILE.exists() else pd.DataFrame()

    write_csv(theme_frequency, THEME_FREQUENCY_FILE)
    write_csv(negative_phrases, output_path)
    write_csv(negative_phrases, NEGATIVE_PHRASE_FILE)
    write_csv(rating_distribution, RATING_DISTRIBUTION_FILE)
    write_csv(theme_vs_sentiment, THEME_VS_SENTIMENT_FILE)
    write_csv(theme_vs_airline, THEME_VS_AIRLINE_FILE)
    write_csv(theme_vs_recommendation, THEME_VS_RECOMMENDATION_FILE)
    write_csv(pain_point_combinations, PAIN_POINT_COMBINATIONS_FILE)
    QUANT_ANALYSIS_SUMMARY_FILE.write_text(
        build_quantitative_summary_markdown(
            theme_frequency=theme_frequency,
            sentiment_by_theme=sentiment_by_theme,
            negative_phrases=negative_phrases,
            rating_distribution=rating_distribution,
            pain_point_combinations=pain_point_combinations,
        ),
        encoding="utf-8",
    )

    return negative_phrases


def main() -> None:
    """Run the quantitative analysis step directly from the command line."""
    parser = ArgumentParser(description="Build quantitative summaries for airline feedback.")
    parser.add_argument("--input", type=str, default=str(SENTIMENT_FILE))
    parser.add_argument("--max-features", type=int, default=40)
    args = parser.parse_args()

    output = build_frequency_table(Path(args.input), max_features=args.max_features)
    print(f"Wrote {len(output)} negative review phrases to {NEGATIVE_PHRASE_FILE}")
    print(f"Wrote theme frequency summary to {THEME_FREQUENCY_FILE}")
    print(f"Wrote rating distribution summary to {RATING_DISTRIBUTION_FILE}")
    print(f"Wrote theme vs sentiment cross-tab to {THEME_VS_SENTIMENT_FILE}")
    print(f"Wrote theme vs airline cross-tab to {THEME_VS_AIRLINE_FILE}")
    print(f"Wrote theme vs recommendation cross-tab to {THEME_VS_RECOMMENDATION_FILE}")
    print(f"Wrote pain-point combinations to {PAIN_POINT_COMBINATIONS_FILE}")
    print(f"Wrote markdown summary to {QUANT_ANALYSIS_SUMMARY_FILE}")


if __name__ == "__main__":
    main()
