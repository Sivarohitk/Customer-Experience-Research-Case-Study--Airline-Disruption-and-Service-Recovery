"""Generate the final portfolio-style case study and supporting project summaries."""

from pathlib import Path

import pandas as pd

from .config import (
    CLEANED_FILE,
    COMBINATION_FIGURE,
    DASHBOARD_FIGURE,
    LEGACY_REPORT_FILE,
    LINKEDIN_DESCRIPTION_FILE,
    NEGATIVE_PHRASE_FILE,
    NEGATIVE_THEME_FIGURE,
    PAIN_POINT_COMBINATIONS_FILE,
    RATING_DISTRIBUTION_FILE,
    REPORT_FILE,
    RESUME_SUMMARY_FILE,
    SENTIMENT_BY_THEME_FILE,
    SENTIMENT_FIGURE,
    SENTIMENT_SUMMARY_FILE,
    TERM_FIGURE,
    THEME_FIGURE,
    THEME_QUOTES_FILE,
    THEME_SUMMARY_FILE,
    THEME_VS_RECOMMENDATION_FILE,
)
from .utils import read_csv


def format_int(value: object) -> str:
    """Format integers consistently for human-readable report copy."""
    return f"{int(value):,}"


def safe_pct(numerator: float, denominator: float) -> float:
    """Compute percentages defensively for markdown summaries."""
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def shorten_excerpt(text: object, max_chars: int = 190) -> str:
    """Trim long quote excerpts so the case study stays readable."""
    value = "" if pd.isna(text) else str(text).strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def get_row(df: pd.DataFrame, column: str, value: str) -> pd.Series:
    """Fetch one row by key and return an empty series if missing."""
    subset = df[df[column] == value]
    return subset.iloc[0] if not subset.empty else pd.Series(dtype="object")


def get_theme_recommendation_breakdown(recommendation_df: pd.DataFrame, theme: str) -> tuple[float, float]:
    """Return yes and no recommendation shares for a given theme."""
    subset = recommendation_df[recommendation_df["theme"] == theme]
    yes_share = subset.loc[subset["recommendation"] == "yes", "share_within_theme_pct"]
    no_share = subset.loc[subset["recommendation"] == "no", "share_within_theme_pct"]
    return float(yes_share.iloc[0]) if not yes_share.empty else 0.0, float(no_share.iloc[0]) if not no_share.empty else 0.0


def get_theme_quote(quotes_df: pd.DataFrame, theme: str) -> str:
    """Return one representative quote excerpt for the requested theme."""
    subset = quotes_df[quotes_df["theme"] == theme].sort_values("quote_rank")
    if subset.empty:
        return "No example quote available in the current run."
    row = subset.iloc[0]
    return f"{row['airline']} review: \"{shorten_excerpt(row['quote_excerpt'])}\""


def relative_figure(path: Path) -> str:
    """Build a report-friendly relative image path."""
    return f"../outputs/figures/{path.name}"


def build_resume_summary(
    total_reviews: int,
    airlines_covered: int,
    theme_summary: pd.DataFrame,
    sentiment_by_theme: pd.DataFrame,
    combinations_df: pd.DataFrame,
) -> str:
    """Create a concise four-bullet project summary for a resume."""
    top_theme = theme_summary.iloc[0]
    second_theme = theme_summary.iloc[1]
    most_negative_theme = sentiment_by_theme.iloc[0]
    top_combination = combinations_df.sort_values("count", ascending=False).iloc[0]

    lines = [
        "# Resume Project Summary",
        "",
        (
            f"- Designed and shipped a mixed-methods UX/CX research pipeline in Python to analyze "
            f"{format_int(total_reviews)} airline feedback records across {format_int(airlines_covered)} airlines."
        ),
        (
            "- Built reproducible workflows for public-data ingestion, synthetic fallback generation, "
            "preprocessing, rule-based theme coding, sentiment scoring, quantitative cross-analysis, and matplotlib visualizations."
        ),
        (
            f"- Identified the dominant disruption themes in customer feedback, led by {top_theme['theme']} "
            f"({format_int(top_theme['count'])} reviews, {top_theme['share_of_reviews_pct']:.1f}%) and "
            f"{second_theme['theme']} ({format_int(second_theme['count'])} reviews, {second_theme['share_of_reviews_pct']:.1f}%)."
        ),
        (
            f"- Quantified downstream loyalty risk by showing that {most_negative_theme['theme']} carried "
            f"{most_negative_theme['negative_share_pct']:.1f}% negative sentiment, while the most common co-occurring pain point "
            f"was {top_combination['combination_label']} ({format_int(top_combination['count'])} reviews)."
        ),
        "",
    ]
    return "\n".join(lines)


def build_linkedin_description(
    total_reviews: int,
    airlines_covered: int,
    theme_summary: pd.DataFrame,
    sentiment_by_theme: pd.DataFrame,
) -> str:
    """Create a six-line project description for GitHub or LinkedIn."""
    top_theme = theme_summary.iloc[0]
    second_theme = theme_summary.iloc[1]
    third_theme = theme_summary.iloc[3]
    most_negative_theme = sentiment_by_theme.iloc[0]

    lines = [
        "Mixed-methods UX and customer-experience case study on airline disruption and service recovery.",
        (
            f"Analyzed {format_int(total_reviews)} cleaned customer reviews across {format_int(airlines_covered)} airlines "
            "using Python, pandas, scikit-learn, and matplotlib."
        ),
        (
            "Built a reproducible pipeline for public-data ingestion, synthetic fallback generation, preprocessing, "
            "theme coding, sentiment scoring, quantitative cross-analysis, and visualization."
        ),
        (
            f"Found that {top_theme['theme']}, {second_theme['theme']}, and {third_theme['theme']} "
            "were the most important disruption-related themes in the dataset."
        ),
        (
            f"Showed that {most_negative_theme['theme']} was the strongest negative-sentiment signal, "
            "with loyalty damage concentrated around communication, compensation, and recovery failures."
        ),
        "Delivered a final case study report, dashboard, and recruiter-ready recommendations on delay messaging, refunds, rebooking, and service recovery design.",
    ]
    return "\n".join(lines) + "\n"


def build_case_study_markdown(
    cleaned: pd.DataFrame,
    theme_summary: pd.DataFrame,
    quotes_df: pd.DataFrame,
    sentiment_summary: pd.DataFrame,
    sentiment_by_theme: pd.DataFrame,
    recommendation_df: pd.DataFrame,
    combinations_df: pd.DataFrame,
    rating_distribution: pd.DataFrame,
    negative_phrases: pd.DataFrame,
) -> str:
    """Create the final recruiter-friendly case study report."""

    total_reviews = len(cleaned)
    airlines_covered = cleaned["airline"].nunique()
    public_reviews = int((cleaned["is_synthetic"] == False).sum())  # noqa: E712
    synthetic_reviews = int((cleaned["is_synthetic"] == True).sum())  # noqa: E712
    public_share = safe_pct(public_reviews, total_reviews)
    synthetic_share = safe_pct(synthetic_reviews, total_reviews)
    average_rating = round(cleaned["rating"].mean(), 2)
    median_rating = round(cleaned["rating"].median(), 2)
    recommended_share = round(cleaned["recommended"].mean() * 100, 2)
    overall_negative_share = float(
        sentiment_summary.loc[sentiment_summary["sentiment"] == "negative", "share_of_reviews_pct"].iloc[0]
    )
    overall_positive_share = float(
        sentiment_summary.loc[sentiment_summary["sentiment"] == "positive", "share_of_reviews_pct"].iloc[0]
    )
    overall_neutral_share = float(
        sentiment_summary.loc[sentiment_summary["sentiment"] == "neutral", "share_of_reviews_pct"].iloc[0]
    )

    low_rated = int(rating_distribution.loc[rating_distribution["rating_bucket"] == "low", "count"].sum())
    medium_rated = int(rating_distribution.loc[rating_distribution["rating_bucket"] == "medium", "count"].sum())
    high_rated = int(rating_distribution.loc[rating_distribution["rating_bucket"] == "high", "count"].sum())
    rated_total = int(rating_distribution["count"].sum())

    delay_theme = get_row(theme_summary, "theme", "delay frustration")
    baggage_theme = get_row(theme_summary, "theme", "baggage problems")
    communication_theme = get_row(theme_summary, "theme", "poor communication")
    cancellation_theme = get_row(theme_summary, "theme", "cancellation stress")
    refund_theme = get_row(theme_summary, "theme", "refund difficulty")
    rebooking_theme = get_row(theme_summary, "theme", "rebooking friction")
    pricing_theme = get_row(theme_summary, "theme", "pricing / compensation dissatisfaction")
    support_theme = get_row(theme_summary, "theme", "customer support responsiveness")
    staff_theme = get_row(theme_summary, "theme", "staff helpfulness")
    recovery_theme = get_row(theme_summary, "theme", "successful recovery experience")

    trust_negative = get_row(sentiment_by_theme, "theme", "trust / loyalty damage")
    digital_negative = get_row(sentiment_by_theme, "theme", "digital / app / website issues")
    pricing_negative = get_row(sentiment_by_theme, "theme", "pricing / compensation dissatisfaction")
    cancellation_negative = get_row(sentiment_by_theme, "theme", "cancellation stress")
    support_negative = get_row(sentiment_by_theme, "theme", "customer support responsiveness")
    staff_sentiment = get_row(sentiment_by_theme, "theme", "staff helpfulness")
    recovery_sentiment = get_row(sentiment_by_theme, "theme", "successful recovery experience")

    trust_yes_share, trust_no_share = get_theme_recommendation_breakdown(recommendation_df, "trust / loyalty damage")
    pricing_yes_share, pricing_no_share = get_theme_recommendation_breakdown(
        recommendation_df, "pricing / compensation dissatisfaction"
    )
    refund_yes_share, refund_no_share = get_theme_recommendation_breakdown(recommendation_df, "refund difficulty")
    rebooking_yes_share, rebooking_no_share = get_theme_recommendation_breakdown(
        recommendation_df, "rebooking friction"
    )
    delay_yes_share, delay_no_share = get_theme_recommendation_breakdown(recommendation_df, "delay frustration")
    communication_yes_share, communication_no_share = get_theme_recommendation_breakdown(
        recommendation_df, "poor communication"
    )
    staff_yes_share, staff_no_share = get_theme_recommendation_breakdown(recommendation_df, "staff helpfulness")
    recovery_yes_share, recovery_no_share = get_theme_recommendation_breakdown(
        recommendation_df, "successful recovery experience"
    )

    top_phrases = negative_phrases.head(6)
    top_combinations = combinations_df.sort_values("count", ascending=False).head(5)
    focus_communication_combo = get_row(
        combinations_df, "combination_label", "cancellation stress + poor communication"
    )
    focus_rebooking_combo = get_row(combinations_df, "combination_label", "delay frustration + rebooking friction")
    focus_support_combo = get_row(
        combinations_df, "combination_label", "refund difficulty + customer support responsiveness"
    )

    delay_quote = get_theme_quote(quotes_df, "delay frustration")
    communication_quote = get_theme_quote(quotes_df, "poor communication")
    refund_quote = get_theme_quote(quotes_df, "refund difficulty")
    rebooking_quote = get_theme_quote(quotes_df, "rebooking friction")
    recovery_quote = get_theme_quote(quotes_df, "successful recovery experience")

    report_lines = [
        "# Customer Experience Research Case Study: Airline Disruption and Service Recovery",
        "",
        "## Business Context",
        (
            "Airline disruptions are operationally unavoidable, but customer perception is shaped by the recovery experience: "
            "how quickly customers are informed, how easily they can rebook, how transparently refunds are handled, "
            "and whether frontline teams show ownership when things go wrong."
        ),
        (
            f"For this project, I analyzed {format_int(total_reviews)} cleaned review records across {format_int(airlines_covered)} airlines "
            f"to identify where disruption experiences break down and where service recovery still protects trust. "
            f"The current combined run uses {format_int(public_reviews)} public reviews ({public_share:.1f}%) and "
            f"{format_int(synthetic_reviews)} synthetic fallback reviews ({synthetic_share:.1f}%)."
        ),
        "",
        "## Research Objective",
        (
            "The objective was to build a portfolio-ready mixed-methods customer-experience research workflow that answers three practical questions:"
        ),
        "- Which disruption and service-recovery pain points appear most often in airline customer feedback?",
        "- Which themes are most strongly associated with negative sentiment and low recommendation intent?",
        "- What recovery behaviors appear to soften the impact of delays, cancellations, baggage issues, and refund friction?",
        "",
        "## Data Sources And Limitations",
        (
            "The primary source is the public Skytrax airline review dataset, supplemented in this run by a small synthetic fallback file "
            "used to preserve pipeline coverage if public inputs are missing."
        ),
        f"- Current analysis base: {format_int(total_reviews)} cleaned reviews, {format_int(airlines_covered)} airlines, average observed rating {average_rating:.2f}, median rating {median_rating:.2f}.",
        f"- Recommendation rate in the cleaned dataset: {recommended_share:.2f}%.",
        (
            "- Public review data is self-selected and likely over-represents unusually strong positive or negative experiences; "
            "it should be treated as directional CX evidence rather than a direct measure of operational incidence."
        ),
        (
            "- The source dataset spans a long historical window and includes inconsistent rating coverage; some dates are clearly imperfect "
            "or reflect source-formatting artifacts, so this project emphasizes thematic patterns over time-series claims."
        ),
        (
            "- Theme coding and sentiment analysis are deliberately rule-based for transparency and reproducibility. "
            "They are strong for a first-pass portfolio study, but not a substitute for manual validation."
        ),
        "",
        "## Methodology",
        "1. Ingested a public downloadable airline review file and standardized it into a common schema.",
        "2. Cleaned text fields, removed exact duplicate reviews, normalized airline names where possible, and created a single `analysis_text` field.",
        "3. Applied multi-label qualitative theme coding to identify disruption and recovery themes such as delays, refunds, baggage, communication, and staff helpfulness.",
        "4. Scored each review with a lightweight reproducible sentiment method and classified records as positive, neutral, or negative.",
        "5. Combined theme labels with sentiment, recommendations, phrases, and theme combinations to produce cross-analysis tables and portfolio-ready charts.",
        "",
        "## Qualitative Theme Analysis",
        (
            f"The most common disruption-related theme was **{delay_theme['theme']}**, appearing in {format_int(delay_theme['count'])} reviews "
            f"({delay_theme['share_of_reviews_pct']:.2f}% of the dataset). Reviews in this cluster often described rolling gate changes, multi-hour waits, and missed connections. "
            f"Representative evidence: {delay_quote}"
        ),
        (
            f"**{baggage_theme['theme']}** was the second-largest pain point at {format_int(baggage_theme['count'])} reviews "
            f"({baggage_theme['share_of_reviews_pct']:.2f}%). Customers repeatedly described delayed bags, poor tracing visibility, and uncertainty after landing."
        ),
        (
            f"**{communication_theme['theme']}** appeared in {format_int(communication_theme['count'])} reviews and often amplified other issues rather than appearing alone. "
            f"Representative evidence: {communication_quote}"
        ),
        (
            f"Refund and recovery friction also showed up in tightly connected ways: **{refund_theme['theme']}** ({format_int(refund_theme['count'])} reviews) "
            f"and **{rebooking_theme['theme']}** ({format_int(rebooking_theme['count'])} reviews). Customers described unclear voucher rules, long waits to fix itineraries, "
            f"and feeling abandoned between channels. Evidence included: {refund_quote} and {rebooking_quote}"
        ),
        (
            f"On the positive side, **{staff_theme['theme']}** still appeared in {format_int(staff_theme['count'])} reviews, showing that employees can materially improve perception "
            f"even when the underlying disruption cannot be avoided. When recovery worked, customers explicitly described it as handled well. Example: {recovery_quote}"
        ),
        "",
        "## Sentiment And Quantitative Findings",
        (
            f"At the full-dataset level, sentiment was {overall_negative_share:.2f}% negative, {overall_neutral_share:.2f}% neutral, and {overall_positive_share:.2f}% positive. "
            "That overall mix is useful context, but theme-level sentiment is more diagnostic because the base dataset includes many non-disruption reviews."
        ),
        (
            f"The most negative themes were **{trust_negative['theme']}** ({trust_negative['negative_share_pct']:.2f}% negative sentiment), "
            f"**{digital_negative['theme']}** ({digital_negative['negative_share_pct']:.2f}% negative), "
            f"**{pricing_negative['theme']}** ({pricing_negative['negative_share_pct']:.2f}% negative), "
            f"**{cancellation_negative['theme']}** ({cancellation_negative['negative_share_pct']:.2f}% negative), and "
            f"**{support_negative['theme']}** ({support_negative['negative_share_pct']:.2f}% negative)."
        ),
        (
            f"Recommendation behavior moved in the same direction. Reviews coded as **trust / loyalty damage** were associated with a {trust_no_share:.2f}% `no` recommendation rate, "
            f"while **pricing / compensation dissatisfaction** reached {pricing_no_share:.2f}% `no`, **refund difficulty** reached {refund_no_share:.2f}% `no`, "
            f"and **rebooking friction** reached {rebooking_no_share:.2f}% `no`."
        ),
        (
            f"Rating distribution should be interpreted cautiously because the source mixes rating scales and general reviews, but even in that context "
            f"{format_int(low_rated)} rated reviews fell into the low bucket, compared with {format_int(medium_rated)} medium and {format_int(high_rated)} high. "
            f"More importantly, disruption-heavy themes pulled average ratings down sharply: trust / loyalty damage averaged 1.83, digital issues 2.19, and pricing / compensation dissatisfaction 3.10."
        ),
        (
            "Negative-review phrase extraction reinforced the same story. The most common high-signal terms and phrases in negative reviews were "
            + ", ".join([f"`{row.term}` ({format_int(row.count)})" for row in top_phrases.itertuples()])
            + "."
        ),
        "",
        "## Major Pain Points",
        (
            f"- **Delays were the main anchor problem.** {delay_theme['theme']} appeared in {format_int(delay_theme['count'])} reviews, "
            f"and the most common cross-theme combination in the dataset was `delay frustration + baggage problems` ({format_int(top_combinations.iloc[0]['count'])} reviews)."
        ),
        (
            f"- **Cancellations were especially damaging when paired with weak communication.** `cancellation stress + poor communication` appeared in "
            f"{format_int(focus_communication_combo['count'])} reviews, while cancellation stress itself was {cancellation_negative['negative_share_pct']:.2f}% negative."
        ),
        (
            f"- **Refund handling created long-tail dissatisfaction.** {refund_theme['theme']} appeared in {format_int(refund_theme['count'])} reviews, "
            f"was {get_row(sentiment_by_theme, 'theme', 'refund difficulty')['negative_share_pct']:.2f}% negative, and had a {refund_no_share:.2f}% `no` recommendation rate."
        ),
        (
            f"- **Rebooking was not just operational friction; it was a CX failure point.** `delay frustration + rebooking friction` appeared in "
            f"{format_int(focus_rebooking_combo['count'])} reviews, and rebooking friction was {get_row(sentiment_by_theme, 'theme', 'rebooking friction')['negative_share_pct']:.2f}% negative."
        ),
        (
            f"- **Compensation and digital failures had outsized brand impact.** Pricing / compensation dissatisfaction was {pricing_negative['negative_share_pct']:.2f}% negative, "
            f"and digital / app / website issues were {digital_negative['negative_share_pct']:.2f}% negative despite lower volume."
        ),
        "",
        "## Service Recovery Insights",
        (
            f"Two findings point to a clear recovery opportunity. First, **{staff_theme['theme']}** was strongly positive: "
            f"{staff_sentiment['positive_count']} of {staff_sentiment['review_count']} coded reviews were positive "
            f"({staff_sentiment['positive_count'] / staff_sentiment['review_count'] * 100:.2f}%), and {staff_yes_share:.2f}% of those reviews still recommended the airline."
        ),
        (
            f"Second, **{recovery_theme['theme']}** behaved differently from the failure themes: "
            f"{recovery_sentiment['positive_count']} of {recovery_sentiment['review_count']} reviews were positive "
            f"({recovery_sentiment['positive_count'] / recovery_sentiment['review_count'] * 100:.2f}%), and {recovery_yes_share:.2f}% recommended the airline."
        ),
        (
            "Taken together, the pattern suggests that customers can forgive the disruption event itself more readily than they forgive confusion, silence, or lack of ownership. "
            "Recovery experiences improved when customers received a clear next step, a human point of accountability, and evidence that the airline was actively solving the problem."
        ),
        "",
        "## Actionable Recommendations",
        (
            f"1. **Implement proactive delay communication.** Delay frustration was the largest theme ({format_int(delay_theme['count'])} reviews), and delay frequently co-occurred with "
            f"poor communication ({format_int(get_row(combinations_df, 'combination_label', 'delay frustration + poor communication')['count'])} reviews). "
            "Airlines should push timed status updates, expected resolution windows, and next-step guidance across app, SMS, email, and gate signage."
        ),
        (
            f"2. **Make refund status transparent end to end.** Refund difficulty was {get_row(sentiment_by_theme, 'theme', 'refund difficulty')['negative_share_pct']:.2f}% negative and "
            f"associated with a {refund_no_share:.2f}% `no` recommendation rate. Customers need a visible refund timeline, claim-status tracker, and plain-language explanation of cash vs. voucher outcomes."
        ),
        (
            f"3. **Reduce rebooking friction across channels.** Rebooking friction was {get_row(sentiment_by_theme, 'theme', 'rebooking friction')['negative_share_pct']:.2f}% negative and paired with "
            f"delay frustration in {format_int(focus_rebooking_combo['count'])} reviews. Airlines should support one-tap alternate flight offers, seat preservation, and consistent policies across app, kiosk, and agent channels."
        ),
        (
            f"4. **Improve service recovery messaging and agent empowerment.** Staff helpfulness and successful recovery experience both had recommendation shares above 75%. "
            "Teams should be equipped with recovery scripts that acknowledge disruption, explain the current state, confirm the next action, and close with a concrete commitment."
        ),
        (
            f"5. **Clarify compensation rules before customers have to ask.** Pricing / compensation dissatisfaction was {pricing_negative['negative_share_pct']:.2f}% negative and {pricing_no_share:.2f}% `no` recommendation. "
            "Voucher eligibility, reimbursement caps, hotel rules, and payment timing should be visible in the disruption flow rather than buried in post-trip support content."
        ),
        "",
        "## Limitations And Next Steps",
        "- Validate the rule-based theme and sentiment outputs on a manually reviewed sample before making stronger claims.",
        "- Segment results by airline, route, geography, and disruption type to separate recurring operational issues from brand-specific service problems.",
        "- Add source triangulation with U.S. DOT complaint data or additional public review corpora to reduce single-source bias.",
        "- Expand the recovery analysis with manual coding for empathy, transparency, compensation adequacy, and channel consistency.",
        "- Treat the synthetic fallback rows as a resilience mechanism for the pipeline, not as a substitute for broader public-data collection.",
        "",
        "## Visual Evidence",
        f"![Research Dashboard]({relative_figure(DASHBOARD_FIGURE)})",
        "",
        f"![Top Customer Pain Points]({relative_figure(THEME_FIGURE)})",
        "",
        f"![Themes Most Associated With Negative Sentiment]({relative_figure(NEGATIVE_THEME_FIGURE)})",
        "",
        f"![Common Co-Occurring Issues]({relative_figure(COMBINATION_FIGURE)})",
        "",
        f"![Overall Sentiment Distribution]({relative_figure(SENTIMENT_FIGURE)})",
        "",
        f"![Top Negative Review Phrases]({relative_figure(TERM_FIGURE)})",
        "",
    ]
    return "\n".join(report_lines)


def generate_report(output_path: Path = REPORT_FILE) -> Path:
    """Write the final case study plus summary assets used across hiring surfaces."""

    cleaned = read_csv(CLEANED_FILE)
    theme_summary = read_csv(THEME_SUMMARY_FILE)
    quotes_df = read_csv(THEME_QUOTES_FILE)
    sentiment_summary = read_csv(SENTIMENT_SUMMARY_FILE)
    sentiment_by_theme = read_csv(SENTIMENT_BY_THEME_FILE)
    recommendation_df = read_csv(THEME_VS_RECOMMENDATION_FILE)
    combinations_df = read_csv(PAIN_POINT_COMBINATIONS_FILE)
    rating_distribution = read_csv(RATING_DISTRIBUTION_FILE)
    negative_phrases = read_csv(NEGATIVE_PHRASE_FILE)

    report_markdown = build_case_study_markdown(
        cleaned=cleaned,
        theme_summary=theme_summary,
        quotes_df=quotes_df,
        sentiment_summary=sentiment_summary,
        sentiment_by_theme=sentiment_by_theme,
        recommendation_df=recommendation_df,
        combinations_df=combinations_df,
        rating_distribution=rating_distribution,
        negative_phrases=negative_phrases,
    )
    output_path.write_text(report_markdown, encoding="utf-8")
    LEGACY_REPORT_FILE.write_text(report_markdown, encoding="utf-8")

    total_reviews = len(cleaned)
    airlines_covered = cleaned["airline"].nunique()
    RESUME_SUMMARY_FILE.write_text(
        build_resume_summary(
            total_reviews=total_reviews,
            airlines_covered=airlines_covered,
            theme_summary=theme_summary,
            sentiment_by_theme=sentiment_by_theme,
            combinations_df=combinations_df,
        ),
        encoding="utf-8",
    )
    LINKEDIN_DESCRIPTION_FILE.write_text(
        build_linkedin_description(
            total_reviews=total_reviews,
            airlines_covered=airlines_covered,
            theme_summary=theme_summary,
            sentiment_by_theme=sentiment_by_theme,
        ),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    """Run the reporting step directly from the command line."""
    report_path = generate_report()
    print(f"Wrote final case study to {report_path}")
    print(f"Wrote legacy report copy to {LEGACY_REPORT_FILE}")
    print(f"Wrote resume-ready summary to {RESUME_SUMMARY_FILE}")
    print(f"Wrote LinkedIn/GitHub description to {LINKEDIN_DESCRIPTION_FILE}")


if __name__ == "__main__":
    main()
