"""Download, validate, and standardize public airline feedback datasets."""

from argparse import ArgumentParser
import hashlib
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

from .config import (
    DATASET_REGISTRY,
    DATA_SOURCE_OPTIONS,
    DEFAULT_RANDOM_SEED,
    DEFAULT_SOURCE_MODE,
    DEFAULT_SYNTHETIC_ROW_COUNT,
    DEFAULT_SOURCE_FILE,
    INGESTED_FILE,
    INGESTION_OUTPUT_COLUMNS,
    PRIMARY_DATASET_KEY,
    STANDARD_REVIEW_COLUMNS,
    SYNTHETIC_SOURCE_FILE,
)
from .synthetic_data import generate_synthetic_feedback_file
from .utils import ensure_directories, write_csv


DISRUPTION_RULES = [
    ("cancellation", ["cancel", "cancelled", "canceled", "cancelation"]),
    ("rebooking", ["rebook", "re-book", "reroute", "standby", "missed connection"]),
    ("baggage", ["baggage", "luggage", "lost bag", "lost baggage", "lost luggage", "bag "]),
    ("refund", ["refund", "voucher", "credit", "reimburse", "compensation"]),
    ("customer_support", ["customer support", "call center", "chat agent", "hold time", "transferred"]),
    (
        "communication",
        [
            "no update",
            "updates",
            "communication",
            "conflicting information",
            "customer service",
            "phone support",
            "app",
        ],
    ),
    ("delay", ["delay", "delayed", "late", "hours late", "hour late", "waited"]),
]


def get_dataset_config(dataset_key: str) -> dict:
    """Return the configured dataset metadata or fail with a clear error."""
    if dataset_key not in DATASET_REGISTRY:
        available = ", ".join(sorted(DATASET_REGISTRY))
        raise ValueError(f"Unknown dataset '{dataset_key}'. Available options: {available}")
    return DATASET_REGISTRY[dataset_key]


def download_dataset(dataset_key: str, force_download: bool = False) -> Path:
    """Download the configured raw dataset file into data/raw for local reuse."""
    dataset = get_dataset_config(dataset_key)
    destination = DEFAULT_SOURCE_FILE.parent / dataset["raw_filename"]

    if destination.exists() and not force_download:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(dataset["download_url"], destination)
    return destination


def build_review_id(row: pd.Series, dataset_key: str) -> str:
    """Create a stable identifier from the original review metadata."""
    seed = " | ".join(
        [
            dataset_key,
            str(row.get("airline", "")),
            str(row.get("review_date", "")),
            str(row.get("review_title", "")),
            str(row.get("review_text", "")),
        ]
    )
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()[:12]
    return f"{dataset_key}_{digest}"


def combine_text(title: object, text: object) -> str | None:
    """Join title and body into a single raw text field for tracing decisions."""
    values = [str(value).strip() for value in [title, text] if pd.notna(value) and str(value).strip()]
    return " | ".join(values) if values else None


def infer_disruption_type(text: object) -> str | None:
    """Assign a simple disruption label from review language."""
    normalized = str(text).lower()
    if not normalized or normalized == "nan":
        return None

    for label, keywords in DISRUPTION_RULES:
        if any(keyword in normalized for keyword in keywords):
            return label
    return "other"


def standardize_recommended(value: object) -> object:
    """Normalize recommendation values into nullable booleans."""
    if pd.isna(value):
        return pd.NA
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "recommended"}:
        return True
    if text in {"0", "false", "no", "n", "not recommended"}:
        return False
    return pd.NA


def standardize_dataset(raw_df: pd.DataFrame, dataset_key: str) -> pd.DataFrame:
    """Map a raw dataset into the project-wide ingestion schema."""
    dataset = get_dataset_config(dataset_key)
    standardized = pd.DataFrame(index=raw_df.index)

    for column in STANDARD_REVIEW_COLUMNS:
        standardized[column] = pd.NA

    for target_column, source_column in dataset["column_map"].items():
        if source_column in raw_df.columns:
            standardized[target_column] = raw_df[source_column]

    standardized["source"] = dataset["source_label"]
    standardized["review_date"] = pd.to_datetime(
        standardized["review_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    standardized["rating"] = pd.to_numeric(standardized["rating"], errors="coerce")
    standardized["recommended"] = standardized["recommended"].apply(standardize_recommended)
    standardized["is_synthetic"] = False
    standardized["raw_text"] = standardized.apply(
        lambda row: combine_text(row["review_title"], row["review_text"]), axis=1
    )
    standardized["disruption_type"] = standardized["raw_text"].apply(infer_disruption_type)
    standardized["review_id"] = standardized.apply(
        lambda row: build_review_id(row, dataset_key), axis=1
    )

    # Preserve backward compatibility with the current downstream pipeline.
    standardized["feedback_text"] = standardized["review_text"]

    return standardized[INGESTION_OUTPUT_COLUMNS]


def ensure_ingestion_columns(df: pd.DataFrame, is_synthetic: bool | None = None) -> pd.DataFrame:
    """Fill missing standard columns and preserve the existing text alias."""
    standardized = df.copy()
    for column in STANDARD_REVIEW_COLUMNS:
        if column not in standardized.columns:
            standardized[column] = pd.NA

    if is_synthetic is not None:
        standardized["is_synthetic"] = is_synthetic

    standardized["raw_text"] = standardized["raw_text"].where(
        standardized["raw_text"].notna(),
        standardized.apply(lambda row: combine_text(row["review_title"], row["review_text"]), axis=1),
    )
    standardized["feedback_text"] = standardized["review_text"]
    return standardized[INGESTION_OUTPUT_COLUMNS]


def load_public_feedback(
    source_path: Path | None = None,
    dataset_key: str = PRIMARY_DATASET_KEY,
    force_download: bool = False,
) -> pd.DataFrame:
    """Load and standardize the configured public dataset."""
    source = Path(source_path) if source_path else download_dataset(dataset_key, force_download=force_download)
    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    df = pd.read_csv(source)
    standardized = standardize_dataset(df, dataset_key=dataset_key)
    return ensure_ingestion_columns(standardized, is_synthetic=False)


def load_synthetic_feedback(
    row_count: int = DEFAULT_SYNTHETIC_ROW_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
    force_regenerate: bool = False,
    source_path: Path = SYNTHETIC_SOURCE_FILE,
) -> pd.DataFrame:
    """Generate or reuse the synthetic fallback dataset and return it as a DataFrame."""
    synthetic_path = generate_synthetic_feedback_file(
        output_path=source_path,
        row_count=row_count,
        seed=random_seed,
        force_regenerate=force_regenerate,
    )
    df = pd.read_csv(synthetic_path)
    return ensure_ingestion_columns(df, is_synthetic=True)


def ingest_feedback(
    source_path: Path | None = None,
    dataset_key: str = PRIMARY_DATASET_KEY,
    source_mode: str = DEFAULT_SOURCE_MODE,
    output_path: Path = INGESTED_FILE,
    force_download: bool = False,
    synthetic_row_count: int = DEFAULT_SYNTHETIC_ROW_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
    force_synthetic_regeneration: bool = False,
) -> pd.DataFrame:
    """
    Download or load a raw CSV and write a standardized ingestion file.

    The default path uses a public downloadable CSV from the Skytrax reviews
    dataset on GitHub. The standardization layer is modular so other datasets
    can be registered later without changing the rest of the pipeline.
    """

    if source_mode not in DATA_SOURCE_OPTIONS:
        raise ValueError(f"Invalid source mode '{source_mode}'. Expected one of: {DATA_SOURCE_OPTIONS}")

    ensure_directories()
    frames: list[pd.DataFrame] = []

    if source_mode in {"public", "combined"}:
        frames.append(
            load_public_feedback(
                source_path=source_path,
                dataset_key=dataset_key,
                force_download=force_download,
            )
        )

    if source_mode in {"synthetic", "combined"}:
        frames.append(
            load_synthetic_feedback(
                row_count=synthetic_row_count,
                random_seed=random_seed,
                force_regenerate=force_synthetic_regeneration,
            )
        )

    standardized = pd.concat(frames, ignore_index=True).reset_index(drop=True)
    write_csv(standardized, output_path)
    return standardized


def main() -> None:
    """Allow the ingestion step to run as a standalone script."""
    parser = ArgumentParser(description="Ingest airline feedback data.")
    parser.add_argument("--source-mode", choices=DATA_SOURCE_OPTIONS, default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--dataset", type=str, default=PRIMARY_DATASET_KEY)
    parser.add_argument("--input", type=str, default=None, help="Optional local raw CSV to standardize")
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download the configured public file into data/raw before ingestion",
    )
    parser.add_argument("--synthetic-rows", type=int, default=DEFAULT_SYNTHETIC_ROW_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument(
        "--force-synthetic-regeneration",
        action="store_true",
        help="Rebuild the synthetic fallback CSV in data/raw before ingestion",
    )
    args = parser.parse_args()

    source_path = Path(args.input) if args.input else None
    output = ingest_feedback(
        source_path=source_path,
        dataset_key=args.dataset,
        source_mode=args.source_mode,
        force_download=args.force_download,
        synthetic_row_count=args.synthetic_rows,
        random_seed=args.seed,
        force_synthetic_regeneration=args.force_synthetic_regeneration,
    )
    print(f"Ingested {len(output)} rows to {INGESTED_FILE}")


if __name__ == "__main__":
    main()
