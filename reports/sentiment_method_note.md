# Sentiment Method Note

## Why This Method Fits The Project
- The project uses a lightweight lexicon-based sentiment scorer with airline-specific words and phrases instead of a heavy external model.
- It is reproducible, easy to run locally, and easy to explain in a portfolio or interview setting.
- The scorer combines review text with a few structured cues already in the dataset, such as rating and recommendation status, to produce more stable labels.

## What The Outputs Show
- Reviews scored: 41790
- Sentiment categories: positive, neutral, negative
- Theme-level sentiment summary highlights which qualitative themes are most associated with negative sentiment.
- Most negative themes in the current run:
  - trust / loyalty damage: 95.22% negative, average score -4.36
  - digital / app / website issues: 89.66% negative, average score -5.22
  - pricing / compensation dissatisfaction: 86.13% negative, average score -4.45
  - cancellation stress: 84.90% negative, average score -5.57
  - customer support responsiveness: 82.10% negative, average score -5.02

## Limitations
- Off-the-shelf sentiment logic can miss sarcasm, mixed sentiment, and context-specific airline language.
- Reviews about disruptions often contain both negative events and positive recovery actions, which can compress into a neutral score.
- Some words such as `delay`, `refund`, or `support` may describe the topic of a review rather than its emotional tone.
- The method is useful as a first-pass signal, but it should be validated against hand-labeled examples before being treated as a strong research claim.
