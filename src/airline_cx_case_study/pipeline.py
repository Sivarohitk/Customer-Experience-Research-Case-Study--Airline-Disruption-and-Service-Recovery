"""Run the airline CX research pipeline from ingestion to final report."""

from argparse import ArgumentParser
from pathlib import Path

from .clean_preprocess import clean_feedback
from .collect_data import ingest_feedback
from .config import (
    DATA_SOURCE_OPTIONS,
    DEFAULT_RANDOM_SEED,
    DEFAULT_SOURCE_MODE,
    DEFAULT_SYNTHETIC_ROW_COUNT,
    PRIMARY_DATASET_KEY,
    REPORT_FILE,
)
from .frequency_analysis import build_frequency_table
from .qualitative_theme_coding import code_themes
from .report_generation import generate_report
from .sentiment_analysis import analyze_sentiment
from .utils import ensure_directories
from .visualization import create_visualizations


def run_pipeline(
    source_path: Path | None = None,
    source_mode: str = DEFAULT_SOURCE_MODE,
    dataset_key: str = PRIMARY_DATASET_KEY,
    synthetic_row_count: int = DEFAULT_SYNTHETIC_ROW_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
    force_download: bool = False,
    force_synthetic_regeneration: bool = False,
) -> Path:
    """Execute each pipeline stage in sequence and return the report path."""

    ensure_directories()
    ingest_feedback(
        source_path=source_path,
        dataset_key=dataset_key,
        source_mode=source_mode,
        force_download=force_download,
        synthetic_row_count=synthetic_row_count,
        random_seed=random_seed,
        force_synthetic_regeneration=force_synthetic_regeneration,
    )
    clean_feedback()
    code_themes()
    analyze_sentiment()
    build_frequency_table()
    create_visualizations()
    generate_report()
    return REPORT_FILE


def main() -> None:
    """Expose the full pipeline as a command-line entry point."""
    parser = ArgumentParser(description="Run the airline CX research pipeline.")
    parser.add_argument("--source-mode", choices=DATA_SOURCE_OPTIONS, default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--dataset", type=str, default=PRIMARY_DATASET_KEY)
    parser.add_argument("--input", type=str, default=None, help="Optional raw CSV input file")
    parser.add_argument("--synthetic-rows", type=int, default=DEFAULT_SYNTHETIC_ROW_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--force-synthetic-regeneration", action="store_true")
    args = parser.parse_args()

    source_path = Path(args.input) if args.input else None
    report_path = run_pipeline(
        source_path=source_path,
        source_mode=args.source_mode,
        dataset_key=args.dataset,
        synthetic_row_count=args.synthetic_rows,
        random_seed=args.seed,
        force_download=args.force_download,
        force_synthetic_regeneration=args.force_synthetic_regeneration,
    )
    print(f"Pipeline complete. Final report written to {report_path}")


if __name__ == "__main__":
    main()
