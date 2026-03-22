"""Clean, enrich, and quality-check the ingested airline feedback dataset."""

from argparse import ArgumentParser
from pathlib import Path
import re

import pandas as pd

from .config import CLEANED_FILE, DATA_QUALITY_REPORT_FILE, INGESTED_FILE
from .utils import normalize_text, read_csv, write_csv


MIN_WORD_COUNT = 4

DISRUPTION_MAP = {
    "delay": "delay",
    "delayed": "delay",
    "cancellation": "cancellation",
    "cancelled": "cancellation",
    "customer_support": "customer_support",
    "rebooking": "rebooking",
    "communication": "communication",
    "baggage": "baggage",
    "refund": "refund",
}

DISRUPTION_KEYWORDS = {
    "delay": ["delay", "delayed", "late", "missed connection"],
    "cancellation": ["cancel", "cancelled", "canceled"],
    "refund": ["refund", "voucher", "credit", "reimburse", "compensation"],
    "baggage": ["bag", "baggage", "luggage", "claim", "tracking"],
    "communication": ["update", "communication", "announcement", "app", "gate"],
    "rebooking": ["rebook", "rebooking", "standby", "itinerary", "kiosk"],
    "customer_support": ["customer support", "phone support", "call center", "chat", "agent"],
}

SPECIAL_AIRLINE_NAMES = {
    "air canada": "Air Canada",
    "american": "American",
    "british airways": "British Airways",
    "delta": "Delta",
    "emirates": "Emirates",
    "frontier": "Frontier",
    "jetblue": "JetBlue",
    "lufthansa": "Lufthansa",
    "southwest": "Southwest",
    "spirit": "Spirit",
    "united": "United",
}


def coerce_text(value: object) -> str:
    """Convert missing or noisy values into a clean string."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def standardize_disruption(value: object) -> str:
    """Map related labels into a small, interview-friendly disruption taxonomy."""
    text = coerce_text(value).lower()
    return DISRUPTION_MAP.get(text, text or "unknown")


def standardize_airline_name(value: object) -> str:
    """Normalize airline names from slugs or mixed casing into readable labels."""
    text = coerce_text(value).lower().replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Unknown"
    if text in SPECIAL_AIRLINE_NAMES:
        return SPECIAL_AIRLINE_NAMES[text]
    return text.title()


def parse_boolean(value: object) -> object:
    """Normalize boolean-like values into nullable booleans."""
    if pd.isna(value):
        return pd.NA
    text = coerce_text(value).lower()
    if text in {"true", "1", "1.0", "yes", "y"}:
        return True
    if text in {"false", "0", "0.0", "no", "n"}:
        return False
    return pd.NA


def parse_recommended(value: object) -> object:
    """Normalize recommendation values into nullable booleans."""
    return parse_boolean(value)


def build_analysis_text(review_title: object, review_text: object) -> str:
    """Create the main analysis text from title plus body while preserving order."""
    parts = [coerce_text(review_title), coerce_text(review_text)]
    return " | ".join([part for part in parts if part])


def create_rating_bucket(value: object) -> str:
    """Bucket ratings into compact analysis-friendly categories."""
    if pd.isna(value):
        return "unknown"
    rating = float(value)
    if rating <= 2:
        return "low"
    if rating == 3:
        return "medium"
    return "high"


def find_disruption_keywords(text: str) -> str:
    """Return a semicolon-separated list of disruption terms found in the text."""
    matches: list[str] = []
    for _, keywords in DISRUPTION_KEYWORDS.items():
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword).replace(r"\ ", r"\s+") + r"\b"
            if re.search(pattern, text) and keyword not in matches:
                matches.append(keyword)
    return "; ".join(matches)


def flag_negative_experience(row: pd.Series) -> bool:
    """Flag rows that strongly suggest a negative service-recovery experience."""
    rating = row.get("rating")
    recommended = row.get("recommended")
    keyword_count = 0
    if coerce_text(row.get("disruption_keywords_found")):
        keyword_count = len(str(row["disruption_keywords_found"]).split("; "))

    if pd.notna(rating) and float(rating) <= 2:
        return True
    if pd.notna(recommended) and bool(recommended) is False:
        return True
    if row.get("disruption_type") in {"cancellation", "refund", "customer_support"} and keyword_count >= 2:
        return True
    return False


def prepare_text_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw text columns and build the main analysis text field."""
    df = df.copy()
    df["review_title"] = df["review_title"].apply(coerce_text)
    df["review_text"] = df["review_text"].apply(coerce_text)
    df["analysis_text"] = df.apply(
        lambda row: build_analysis_text(row["review_title"], row["review_text"]),
        axis=1,
    )
    df["feedback_text"] = df["analysis_text"]
    df["clean_text"] = df["analysis_text"].apply(normalize_text)
    df["word_count"] = df["clean_text"].str.split().str.len()
    df["text_length"] = df["analysis_text"].str.len()
    return df


def prepare_core_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize key structured fields without removing rows."""
    df = df.copy()
    df["airline"] = df["airline"].apply(standardize_airline_name)
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    df["review_month"] = df["review_date"].dt.to_period("M").astype("string")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["recommended"] = df["recommended"].apply(parse_recommended)
    df["is_synthetic"] = df["is_synthetic"].apply(parse_boolean)
    df["is_synthetic"] = df["is_synthetic"].where(df["is_synthetic"].notna(), False)
    df["disruption_type"] = df["disruption_type"].apply(standardize_disruption)
    df["traveler_type"] = df["traveler_type"].apply(coerce_text).replace("", pd.NA)
    df["route"] = df["route"].apply(coerce_text).replace("", pd.NA)
    df["seat_type"] = df["seat_type"].apply(coerce_text).replace("", pd.NA)
    return df


def remove_low_quality_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Remove only clearly unusable rows and record each reduction step."""
    stats: dict[str, int] = {}

    before = len(df)
    df = df[df["clean_text"] != ""].copy()
    stats["empty_reviews_removed"] = before - len(df)

    before = len(df)
    df = df[df["word_count"] >= MIN_WORD_COUNT].copy()
    stats["short_reviews_removed"] = before - len(df)

    before = len(df)
    df = df.drop_duplicates(subset=["clean_text"], keep="first").copy()
    stats["duplicate_reviews_removed"] = before - len(df)

    return df, stats


def add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived fields used by later qualitative and quantitative analysis."""
    df = df.copy()
    df["rating_bucket"] = df["rating"].apply(create_rating_bucket)
    df["disruption_keywords_found"] = df["clean_text"].apply(find_disruption_keywords)
    df["likely_negative_experience"] = df.apply(flag_negative_experience, axis=1)
    return df


def build_quality_report(cleaned_df: pd.DataFrame, metrics: dict[str, int]) -> str:
    """Create a short markdown quality report for the processed dataset."""
    retention_rate = 0.0
    if metrics["rows_before_cleaning"]:
        retention_rate = cleaned_df.shape[0] / metrics["rows_before_cleaning"]

    key_missing = {
        "review_text": int(cleaned_df["review_text"].eq("").sum()),
        "rating": int(cleaned_df["rating"].isna().sum()),
        "traveler_type": int(cleaned_df["traveler_type"].isna().sum()),
        "route": int(cleaned_df["route"].isna().sum()),
        "seat_type": int(cleaned_df["seat_type"].isna().sum()),
    }

    source_mix = (
        cleaned_df["is_synthetic"]
        .fillna(False)
        .map({True: "synthetic", False: "public"})
        .value_counts()
        .to_dict()
    )

    report_lines = [
        "# Data Quality Summary",
        "",
        "## Row Counts",
        f"- Rows before cleaning: {metrics['rows_before_cleaning']}",
        f"- Empty reviews removed: {metrics['empty_reviews_removed']}",
        f"- Very short reviews removed (< {MIN_WORD_COUNT} words): {metrics['short_reviews_removed']}",
        f"- Duplicate reviews removed (exact duplicate normalized analysis text): {metrics['duplicate_reviews_removed']}",
        f"- Rows after cleaning: {cleaned_df.shape[0]}",
        f"- Retention rate: {retention_rate:.1%}",
        "",
        "## Missing Value Snapshot",
        *[f"- {column}: {count}" for column, count in key_missing.items()],
        "",
        "## Dataset Mix",
        *[f"- {source}: {count}" for source, count in source_mix.items()],
        "",
        "## Notes",
        "- Deduplication keeps the first row when the normalized title-plus-review text is identical.",
        "- Reviews are only removed if the combined analysis text is empty or shorter than the minimum word threshold.",
        "- The cleaned dataset preserves `feedback_text`, `analysis_text`, `clean_text`, disruption labels, and synthetic/public flags for downstream analysis.",
        "",
    ]
    return "\n".join(report_lines)


def clean_feedback(
    input_path: Path = INGESTED_FILE,
    output_path: Path = CLEANED_FILE,
    report_path: Path = DATA_QUALITY_REPORT_FILE,
) -> pd.DataFrame:
    """
    Clean the ingestion output and add fields used by later analysis steps.

    The cleaning logic is intentionally conservative: it removes only empty,
    very short, or exact duplicate normalized reviews while preserving the text
    and structured columns needed by theme coding, sentiment analysis, and
    frequency analysis.
    """

    df = read_csv(input_path).copy()
    metrics = {"rows_before_cleaning": len(df)}

    df = prepare_core_fields(df)
    df = prepare_text_fields(df)
    df, reduction_stats = remove_low_quality_rows(df)
    metrics.update(reduction_stats)
    df = add_derived_fields(df)
    df = df.sort_values(["review_date", "review_id"], na_position="last").reset_index(drop=True)

    write_csv(df, output_path)
    report_path.write_text(build_quality_report(df, metrics), encoding="utf-8")
    return df


def main() -> None:
    """Run the cleaning step directly from the command line."""
    parser = ArgumentParser(description="Clean airline feedback data.")
    parser.add_argument("--input", type=str, default=str(INGESTED_FILE))
    args = parser.parse_args()

    output = clean_feedback(Path(args.input))
    print(f"Rows before cleaning: {len(read_csv(Path(args.input)))}")
    print(f"Rows after cleaning: {len(output)}")
    print(f"Cleaned data written to {CLEANED_FILE}")
    print(f"Data quality report written to {DATA_QUALITY_REPORT_FILE}")


if __name__ == "__main__":
    main()
