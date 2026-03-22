"""Central project paths and shared configuration values."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
REPORTS_DIR = PROJECT_ROOT / "reports"

INGESTED_FILE = PROCESSED_DIR / "ingested_feedback.csv"
CLEANED_FILE = PROCESSED_DIR / "clean_airline_feedback.csv"
DATA_QUALITY_REPORT_FILE = PROCESSED_DIR / "data_quality_summary.md"
CODED_FILE = PROCESSED_DIR / "coded_feedback.csv"
THEME_SUMMARY_FILE = PROCESSED_DIR / "theme_summary.csv"
THEME_QUOTES_FILE = PROCESSED_DIR / "theme_example_quotes.csv"
THEME_CODING_MEMO_FILE = REPORTS_DIR / "theme_coding_memo.md"
SENTIMENT_FILE = PROCESSED_DIR / "sentiment_feedback.csv"
SENTIMENT_SUMMARY_FILE = PROCESSED_DIR / "sentiment_summary.csv"
SENTIMENT_BY_THEME_FILE = PROCESSED_DIR / "sentiment_by_theme_summary.csv"
SENTIMENT_METHOD_NOTE_FILE = REPORTS_DIR / "sentiment_method_note.md"
FREQUENCY_FILE = PROCESSED_DIR / "term_frequency.csv"
THEME_FREQUENCY_FILE = PROCESSED_DIR / "theme_frequency_summary.csv"
NEGATIVE_PHRASE_FILE = PROCESSED_DIR / "negative_review_phrase_summary.csv"
RATING_DISTRIBUTION_FILE = PROCESSED_DIR / "rating_distribution_summary.csv"
THEME_VS_SENTIMENT_FILE = PROCESSED_DIR / "theme_vs_sentiment_crosstab.csv"
THEME_VS_AIRLINE_FILE = PROCESSED_DIR / "theme_vs_airline_crosstab.csv"
THEME_VS_RECOMMENDATION_FILE = PROCESSED_DIR / "theme_vs_recommendation_crosstab.csv"
PAIN_POINT_COMBINATIONS_FILE = PROCESSED_DIR / "pain_point_combinations_summary.csv"
QUANT_ANALYSIS_SUMMARY_FILE = REPORTS_DIR / "quantitative_analysis_summary.md"
REPORT_FILE = REPORTS_DIR / "final_case_study.md"
LEGACY_REPORT_FILE = REPORTS_DIR / "final_case_study_report.md"
RESUME_SUMMARY_FILE = REPORTS_DIR / "resume_project_summary.md"
LINKEDIN_DESCRIPTION_FILE = REPORTS_DIR / "linkedin_github_project_description.md"

DISRUPTION_FIGURE = FIGURES_DIR / "disruption_type_counts.png"
THEME_FIGURE = FIGURES_DIR / "theme_counts.png"
SENTIMENT_FIGURE = FIGURES_DIR / "sentiment_distribution.png"
TERM_FIGURE = FIGURES_DIR / "top_terms.png"
NEGATIVE_THEME_FIGURE = FIGURES_DIR / "negative_sentiment_by_theme.png"
COMBINATION_FIGURE = FIGURES_DIR / "pain_point_combinations.png"
RATING_FIGURE = FIGURES_DIR / "rating_distribution.png"
DASHBOARD_FIGURE = FIGURES_DIR / "cx_research_dashboard.png"
VISUALIZATION_NOTE_FILE = REPORTS_DIR / "visualization_figure_guide.md"

DIRECTORIES = [
    RAW_DIR,
    PROCESSED_DIR,
    NOTEBOOKS_DIR,
    OUTPUTS_DIR,
    FIGURES_DIR,
    REPORTS_DIR,
]

STANDARD_REVIEW_COLUMNS = [
    "review_id",
    "source",
    "airline",
    "review_date",
    "review_title",
    "review_text",
    "rating",
    "traveler_type",
    "route",
    "seat_type",
    "recommended",
    "disruption_type",
    "raw_text",
    "is_synthetic",
]

# `feedback_text` is retained as an ingestion-time compatibility alias so the
# rest of the existing pipeline can continue to run without further changes.
PIPELINE_COMPATIBILITY_COLUMNS = ["feedback_text"]
INGESTION_OUTPUT_COLUMNS = STANDARD_REVIEW_COLUMNS + PIPELINE_COMPATIBILITY_COLUMNS

PRIMARY_DATASET_KEY = "skytrax_airline_reviews"
DATA_SOURCE_OPTIONS = ("public", "synthetic", "combined")
DEFAULT_SOURCE_MODE = "public"
DEFAULT_RANDOM_SEED = 20260321
DEFAULT_SYNTHETIC_ROW_COUNT = 420

DATASET_REGISTRY = {
    PRIMARY_DATASET_KEY: {
        "dataset_key": PRIMARY_DATASET_KEY,
        "source_label": "Skytrax User Reviews Dataset",
        "description": (
            "Public airline review CSV hosted on GitHub. It is easy to download "
            "locally and already includes airline names, dates, titles, review "
            "text, traveler type, route, cabin class, ratings, and "
            "recommendation labels."
        ),
        "download_url": (
            "https://raw.githubusercontent.com/quankiquanki/"
            "skytrax-reviews-dataset/master/data/airline.csv"
        ),
        "raw_filename": "skytrax_airline_reviews.csv",
        "file_format": "csv",
        "column_map": {
            "airline": "airline_name",
            "review_date": "date",
            "review_title": "title",
            "review_text": "content",
            "rating": "overall_rating",
            "traveler_type": "type_traveller",
            "route": "route",
            "seat_type": "cabin_flown",
            "recommended": "recommended",
        },
    }
}

DEFAULT_DATASET = DATASET_REGISTRY[PRIMARY_DATASET_KEY]
DEFAULT_SOURCE_FILE = RAW_DIR / DEFAULT_DATASET["raw_filename"]
SYNTHETIC_SOURCE_FILE = RAW_DIR / "synthetic_airline_feedback.csv"
