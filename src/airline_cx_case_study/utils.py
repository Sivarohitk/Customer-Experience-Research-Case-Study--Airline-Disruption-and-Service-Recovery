"""Utility helpers shared across the case-study pipeline."""

from pathlib import Path
import re

import pandas as pd

from .config import DIRECTORIES


def ensure_directories() -> None:
    """Create expected project directories so scripts can run independently."""
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)


def normalize_text(text: str) -> str:
    """Lowercase text and remove punctuation to support simple text analysis."""
    cleaned = str(text).lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Persist a DataFrame to disk and ensure the parent directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file using pandas and return the DataFrame."""
    return pd.read_csv(path, low_memory=False)
