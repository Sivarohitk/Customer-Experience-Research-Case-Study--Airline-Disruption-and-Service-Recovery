"""Convenience entry point for running the full case-study pipeline."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from airline_cx_case_study.pipeline import main  # noqa: E402


if __name__ == "__main__":
    main()

