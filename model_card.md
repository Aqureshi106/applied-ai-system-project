# Model Card - BeatMatcher Agentic Recommender

## 1. Model Name and Version
BeatMatcher Agentic Recommender v1.1

## 2. AI Feature Selection
- Primary required feature: Agentic workflow
	- Planner -> Retriever -> Ranker -> Verifier
- Optional stretch feature: Reliability and testing harness
	- Scripted benchmark scenarios with pass or fail outcomes and confidence reporting

## 3. Intended Use
This system recommends top songs from a fixed catalog based on user preferences such as genre, mood, energy, acoustic preference, and optional numeric targets. It is designed for learning and portfolio demonstration, not for production deployment.

Primary users are students, instructors, and portfolio reviewers who want transparent AI behavior and measurable reliability evidence.

## 4. System Overview
The system processes user input through four stages:
1. Planner normalizes and constrains user preferences.
2. Retriever selects likely candidate songs from the catalog.
3. Ranker applies weighted scoring across semantic and numeric features.
4. Verifier applies guardrails, deterministic ordering, and low-confidence fallback handling.

Outputs include recommended songs plus explanation text describing why each song was selected.

## 5. Data
Source data: [data/songs.csv](data/songs.csv)

Current catalog size: 18 songs

Per-song attributes include:
- title, artist, genre, mood
- energy, tempo_bpm, valence, danceability, acousticness
- popularity, release year and decade, mood tags, era descriptor

Dataset limitations:
- Genre coverage is uneven.
- Several styles have sparse representation.
- Catalog size is too small for broad personalization claims.

## 6. Reliability and Evaluation Evidence
Automated tests:
- Unit and behavior checks in [tests/test_recommender.py](tests/test_recommender.py)
- Latest result: 6 out of 6 tests passed

Reliability harness (stretch feature):
- Script: [src/eval_harness.py](src/eval_harness.py)
- Latest result: 3 out of 3 benchmark scenarios passed
- Average confidence (normalized proxy): 0.87

Additional confidence signal:
- Average top recommendation score across 5 representative profiles: 11.40
- Observed top-score range: 9.11 to 13.81

Human evaluation:
- Output quality is manually reviewed for semantic fit.
- Review findings are used to adjust weights, rules, and test coverage.

## 7. Strengths
- Transparent and explainable scoring behavior
- Deterministic and reproducible outputs under fixed inputs
- Guardrails for malformed input and invalid mode selection
- Fast iteration cycle for experimentation and testing

## 8. Limitations and Bias
- Small and synthetic catalog restricts diversity and coverage
- Numeric-over-semantic bias can appear in conflicting preference cases
- Hard thresholds can cause abrupt ranking changes near boundaries
- Weight tuning sensitivity can shift rankings substantially

## 9. Misuse Risks and Mitigations
Potential misuse:
- Presenting recommendations as objective truth despite limited data and heuristic logic
- Applying this system in high-stakes contexts it was not designed for

Mitigations implemented:
- Explanations for recommendation rationale
- Input normalization and fallback guardrails
- Logging support for warnings and decision trace points
- Human review loop for quality control
- Explicit scope statement: educational and portfolio use only

## 10. Operational Notes
Core implementation files:
- [src/recommender.py](src/recommender.py)
- [src/main.py](src/main.py)

Runtime behavior:
- Logging level can be configured with RECOMMENDER_LOG_LEVEL
- Verifier can trigger fallback ordering when confidence is weak

## 11. Future Work
- Expand and rebalance catalog coverage
- Replace threshold rules with smoother preference curves
- Add diversity-aware reranking
- Add stronger confidence calibration linked to user feedback
- Extend retrieval to multi-source metadata and compare quality against baseline

## 12. Reflection
This project showed that reliable AI systems require more than producing outputs. The key lessons were to make decision stages observable, pair automated tests with human judgment, and treat measurable confidence as a useful signal rather than proof of semantic correctness.