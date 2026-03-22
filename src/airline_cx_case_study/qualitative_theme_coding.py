"""Apply rule-based qualitative theme coding to cleaned airline feedback."""

from argparse import ArgumentParser
from pathlib import Path
import re

import pandas as pd

from .config import (
    CLEANED_FILE,
    CODED_FILE,
    THEME_CODING_MEMO_FILE,
    THEME_QUOTES_FILE,
    THEME_SUMMARY_FILE,
)
from .theme_rules import THEME_RULES
from .utils import read_csv, write_csv


DEFAULT_QUOTES_PER_THEME = 3


def indicator_column(theme: str) -> str:
    """Convert a theme label into a stable binary indicator column name."""
    slug = re.sub(r"[^a-z0-9]+", "_", theme.lower()).strip("_")
    return f"theme__{slug}"


def compile_keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Compile a word-boundary regex for a theme keyword or phrase."""
    pattern = r"\b" + re.escape(keyword).replace(r"\ ", r"\s+") + r"\b"
    return re.compile(pattern)


def compile_theme_rules() -> dict[str, dict[str, object]]:
    """Compile keyword and regex patterns once so coding stays fast and transparent."""
    compiled: dict[str, dict[str, object]] = {}
    for theme, rule in THEME_RULES.items():
        compiled[theme] = {
            "description": rule["description"],
            "keyword_patterns": [
                (keyword, compile_keyword_pattern(keyword)) for keyword in rule.get("keywords", [])
            ],
            "regex_patterns": [
                (pattern, re.compile(pattern)) for pattern in rule.get("regex", [])
            ],
            "exclude_patterns": [
                compile_keyword_pattern(keyword) for keyword in rule.get("exclude_keywords", [])
            ],
        }
    return compiled


def detect_themes(text: str, compiled_rules: dict[str, dict[str, object]]) -> tuple[list[str], dict[str, list[str]]]:
    """Return matched themes plus the evidence phrases that triggered them."""
    normalized_text = str(text or "")
    matched_themes: list[str] = []
    evidence_by_theme: dict[str, list[str]] = {}

    for theme, rule in compiled_rules.items():
        if any(pattern.search(normalized_text) for pattern in rule["exclude_patterns"]):
            continue

        evidence: list[str] = []
        for keyword, pattern in rule["keyword_patterns"]:
            if pattern.search(normalized_text):
                evidence.append(keyword)
        for regex_pattern, compiled_pattern in rule["regex_patterns"]:
            if compiled_pattern.search(normalized_text):
                evidence.append(f"regex:{regex_pattern}")

        if evidence:
            matched_themes.append(theme)
            evidence_by_theme[theme] = sorted(set(evidence))

    return matched_themes, evidence_by_theme


def format_theme_evidence(evidence_by_theme: dict[str, list[str]]) -> str:
    """Format match evidence into a readable string for review-level output."""
    if not evidence_by_theme:
        return ""
    sections = [f"{theme}: {', '.join(matches)}" for theme, matches in evidence_by_theme.items()]
    return " | ".join(sections)


def expand_theme_columns(df: pd.DataFrame, theme_lists: pd.Series) -> pd.DataFrame:
    """Add one binary indicator column per theme for later analysis."""
    expanded = df.copy()
    for theme in THEME_RULES:
        column = indicator_column(theme)
        expanded[column] = theme_lists.apply(lambda values: int(theme in values))
    return expanded


def build_theme_summary(coded_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize overall theme prevalence across all matched labels."""
    rows: list[dict[str, object]] = []
    total_reviews = len(coded_df)

    for theme, rule in THEME_RULES.items():
        indicator = indicator_column(theme)
        theme_rows = coded_df[coded_df[indicator] == 1]
        count = int(len(theme_rows))
        share = (count / total_reviews * 100) if total_reviews else 0.0
        avg_rating = theme_rows["rating"].mean() if count else float("nan")
        rows.append(
            {
                "theme": theme,
                "description": rule["description"],
                "count": count,
                "share_of_reviews_pct": round(share, 2),
                "avg_rating": round(avg_rating, 2) if pd.notna(avg_rating) else pd.NA,
            }
        )

    summary = pd.DataFrame(rows).sort_values(["count", "theme"], ascending=[False, True]).reset_index(drop=True)
    return summary


def truncate_quote(text: str, max_chars: int = 280) -> str:
    """Trim a quote to a readable excerpt while keeping it deterministic."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def build_theme_quotes(coded_df: pd.DataFrame, quotes_per_theme: int = DEFAULT_QUOTES_PER_THEME) -> pd.DataFrame:
    """Select a few representative quotes per theme for a portfolio-friendly artifact."""
    quote_rows: list[dict[str, object]] = []

    for theme in THEME_RULES:
        theme_column = indicator_column(theme)
        subset = coded_df[coded_df[theme_column] == 1].copy()
        if subset.empty:
            continue

        # Prefer public examples first, then medium-length quotes that are easier to read.
        subset["quote_length_score"] = (subset["text_length"] - 320).abs()
        subset["quote_excerpt"] = subset["analysis_text"].fillna("").apply(truncate_quote)
        subset = subset.sort_values(
            ["is_synthetic", "quote_length_score", "review_date", "review_id"],
            ascending=[True, True, False, True],
        )
        subset = subset.drop_duplicates(subset=["quote_excerpt"]).head(quotes_per_theme)

        for rank, (_, row) in enumerate(subset.iterrows(), start=1):
            quote_rows.append(
                {
                    "theme": theme,
                    "quote_rank": rank,
                    "review_id": row["review_id"],
                    "airline": row["airline"],
                    "source": row["source"],
                    "review_date": row["review_date"],
                    "rating": row["rating"],
                    "is_synthetic": row["is_synthetic"],
                    "quote_excerpt": row["quote_excerpt"],
                }
            )

    return pd.DataFrame(quote_rows)


def build_theme_coding_memo(coded_df: pd.DataFrame, summary_df: pd.DataFrame, quotes_path: Path) -> str:
    """Write a short transparent memo about how the rule-based coding works."""
    unmatched_reviews = int((coded_df["theme_count"] == 0).sum())
    top_themes = summary_df[summary_df["count"] > 0].head(5)

    memo_lines = [
        "# Theme Coding Memo",
        "",
        "## How The Rule-Based Coding Works",
        "- The module reads the cleaned dataset and evaluates each review against a small set of theme dictionaries defined in `src/airline_cx_case_study/theme_rules.py`.",
        "- Each theme includes plain-language keyword phrases plus optional regex patterns for more flexible phrasing.",
        "- A review can receive multiple theme labels when it matches more than one customer-experience pattern.",
        "- The review-level output also stores human-readable match evidence so the coding is easy to inspect and explain in a portfolio setting.",
        "",
        "## Current Coverage",
        f"- Reviews coded: {len(coded_df)}",
        f"- Reviews with at least one theme: {len(coded_df) - unmatched_reviews}",
        f"- Reviews with no matched theme: {unmatched_reviews}",
        "- Top matched themes:",
        *[
            f"  - {row.theme}: {int(row.count)} reviews ({row.share_of_reviews_pct:.2f}%)"
            for row in top_themes.itertuples()
        ],
        "",
        "## Example Quotes Artifact",
        f"- Representative quotes per theme are saved to `{quotes_path}`.",
        "- Quotes are selected deterministically so the artifact is reproducible.",
        "",
        "## Limitations",
        "- Rule-based coding is explainable, but it can miss nuance, sarcasm, and context-dependent meanings.",
        "- Keyword overlap can trigger multiple themes even when only one is central to the review.",
        "- Some broad terms like `app`, `agent`, or `voucher` may still over- or under-trigger a theme depending on context.",
        "- This first version does not replace manual coding or intercoder validation.",
        "",
        "## How A Researcher Could Improve It",
        "- Review a stratified sample of coded rows and compare the assigned themes against human judgment.",
        "- Refine the dictionaries in `src/airline_cx_case_study/theme_rules.py` by adding domain phrases, exclusions, and airline-specific language.",
        "- Add manual validation, intercoder agreement checks, and a small gold-standard labeled sample for benchmarking.",
        "- Promote the most reliable rules into a documented coding protocol before making portfolio claims from the findings.",
        "",
    ]
    return "\n".join(memo_lines)


def code_themes(
    input_path: Path = CLEANED_FILE,
    output_path: Path = CODED_FILE,
    summary_path: Path = THEME_SUMMARY_FILE,
    quotes_path: Path = THEME_QUOTES_FILE,
    memo_path: Path = THEME_CODING_MEMO_FILE,
    quotes_per_theme: int = DEFAULT_QUOTES_PER_THEME,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Assign reusable CX themes to each review and write supporting artifacts."""

    df = read_csv(input_path).copy()
    compiled_rules = compile_theme_rules()
    text_series = df["clean_text"].fillna("")

    detected = text_series.apply(lambda text: detect_themes(text, compiled_rules))
    theme_lists = detected.apply(lambda item: item[0])
    evidence = detected.apply(lambda item: item[1])

    coded_df = df.copy()
    coded_df["themes"] = theme_lists.apply(lambda values: "; ".join(values))
    coded_df["theme_count"] = theme_lists.apply(len)
    coded_df["primary_theme"] = theme_lists.apply(lambda values: values[0] if values else "unclassified")
    coded_df["theme_evidence"] = evidence.apply(format_theme_evidence)
    coded_df = expand_theme_columns(coded_df, theme_lists)

    summary_df = build_theme_summary(coded_df)
    quotes_df = build_theme_quotes(coded_df, quotes_per_theme=quotes_per_theme)

    write_csv(coded_df, output_path)
    write_csv(summary_df, summary_path)
    write_csv(quotes_df, quotes_path)
    memo_path.write_text(build_theme_coding_memo(coded_df, summary_df, quotes_path), encoding="utf-8")

    return coded_df, summary_df, quotes_df


def main() -> None:
    """Run the theme-coding step directly from the command line."""
    parser = ArgumentParser(description="Code airline feedback themes.")
    parser.add_argument("--input", type=str, default=str(CLEANED_FILE))
    parser.add_argument("--quotes-per-theme", type=int, default=DEFAULT_QUOTES_PER_THEME)
    args = parser.parse_args()

    coded, summary, quotes = code_themes(
        input_path=Path(args.input),
        quotes_per_theme=args.quotes_per_theme,
    )
    print(f"Coded {len(coded)} rows")
    print(f"Wrote {len(summary)} theme summary rows to {THEME_SUMMARY_FILE}")
    print(f"Wrote {len(quotes)} example quotes to {THEME_QUOTES_FILE}")
    print(f"Wrote theme memo to {THEME_CODING_MEMO_FILE}")


if __name__ == "__main__":
    main()
