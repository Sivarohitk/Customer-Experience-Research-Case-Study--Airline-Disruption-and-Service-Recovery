# Theme Coding Memo

## How The Rule-Based Coding Works
- The module reads the cleaned dataset and evaluates each review against a small set of theme dictionaries defined in `src/airline_cx_case_study/theme_rules.py`.
- Each theme includes plain-language keyword phrases plus optional regex patterns for more flexible phrasing.
- A review can receive multiple theme labels when it matches more than one customer-experience pattern.
- The review-level output also stores human-readable match evidence so the coding is easy to inspect and explain in a portfolio setting.

## Current Coverage
- Reviews coded: 41790
- Reviews with at least one theme: 20321
- Reviews with no matched theme: 21469
- Top matched themes:
  - delay frustration: 8200 reviews (19.62%)
  - baggage problems: 6316 reviews (15.11%)
  - staff helpfulness: 5688 reviews (13.61%)
  - cancellation stress: 3186 reviews (7.62%)
  - poor communication: 2281 reviews (5.46%)

## Example Quotes Artifact
- Representative quotes per theme are saved to `C:\Users\sivar\OneDrive\Documents\New folder\Customer Experience Research Case Study- Airline Disruption and Service Recovery\data\processed\theme_example_quotes.csv`.
- Quotes are selected deterministically so the artifact is reproducible.

## Limitations
- Rule-based coding is explainable, but it can miss nuance, sarcasm, and context-dependent meanings.
- Keyword overlap can trigger multiple themes even when only one is central to the review.
- Some broad terms like `app`, `agent`, or `voucher` may still over- or under-trigger a theme depending on context.
- This first version does not replace manual coding or intercoder validation.

## How A Researcher Could Improve It
- Review a stratified sample of coded rows and compare the assigned themes against human judgment.
- Refine the dictionaries in `src/airline_cx_case_study/theme_rules.py` by adding domain phrases, exclusions, and airline-specific language.
- Add manual validation, intercoder agreement checks, and a small gold-standard labeled sample for benchmarking.
- Promote the most reliable rules into a documented coding protocol before making portfolio claims from the findings.
