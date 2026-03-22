# Data Quality Summary

## Row Counts
- Rows before cleaning: 41816
- Empty reviews removed: 0
- Very short reviews removed (< 4 words): 0
- Duplicate reviews removed (exact duplicate normalized analysis text): 26
- Rows after cleaning: 41790
- Retention rate: 99.9%

## Missing Value Snapshot
- review_text: 0
- rating: 4529
- traveler_type: 38993
- route: 39030
- seat_type: 2871

## Dataset Mix
- public: 41370
- synthetic: 420

## Notes
- Deduplication keeps the first row when the normalized title-plus-review text is identical.
- Reviews are only removed if the combined analysis text is empty or shorter than the minimum word threshold.
- The cleaned dataset preserves `feedback_text`, `analysis_text`, `clean_text`, disruption labels, and synthetic/public flags for downstream analysis.
