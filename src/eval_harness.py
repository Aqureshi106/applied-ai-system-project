from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

from src.recommender import load_songs, recommend_songs


def _confidence_from_score(score: float, max_score_hint: float = 15.0) -> float:
    """Map raw match score to a 0-1 confidence proxy for reporting."""
    if max_score_hint <= 0:
        return 0.0
    value = score / max_score_hint
    return max(0.0, min(1.0, value))


@dataclass
class EvalCase:
    name: str
    profile: Dict
    mode: str
    check: Callable[[Dict, float], bool]
    expectation: str


def run_harness() -> Tuple[int, int, float]:
    songs = load_songs("data/songs.csv")

    # These checks are intentionally simple and transparent for portfolio review.
    cases: List[EvalCase] = [
        EvalCase(
            name="High-energy pop alignment",
            profile={
                "genre": "pop",
                "mood": "happy",
                "energy": 0.85,
                "likes_acoustic": False,
                "target_tempo": 128.0,
                "target_valence": 0.86,
                "target_danceability": 0.82,
                "target_popularity": 90.0,
            },
            mode="balanced",
            check=lambda song, score: song.get("genre", "").lower() == "pop" and score >= 10.0,
            expectation="Top song should be pop with strong score (>= 10).",
        ),
        EvalCase(
            name="Chill acoustic preference",
            profile={
                "genre": "lofi",
                "mood": "chill",
                "energy": 0.38,
                "likes_acoustic": True,
                "target_tempo": 75.0,
                "target_valence": 0.58,
            },
            mode="mood-first",
            check=lambda song, score: float(song.get("acousticness", 0.0)) >= 0.45 and score >= 8.0,
            expectation="Top song should favor acoustic fit with score >= 8.",
        ),
        EvalCase(
            name="Unknown category robustness",
            profile={
                "genre": "hyperpop",
                "mood": "melancholy",
                "energy": 0.60,
                "likes_acoustic": False,
            },
            mode="balanced",
            check=lambda song, score: bool(song.get("title")) and score >= 7.5,
            expectation="System should still return a plausible top song with score >= 7.5.",
        ),
    ]

    passed = 0
    confidences: List[float] = []

    print("\n=== BeatMatcher Evaluation Harness ===")
    for idx, case in enumerate(cases, start=1):
        results = recommend_songs(case.profile, songs, k=1, mode=case.mode)
        if not results:
            print(f"[{idx}] {case.name}: FAIL")
            print("    reason: no recommendation returned")
            confidences.append(0.0)
            continue

        top_song, top_score, explanation = results[0]
        confidence = _confidence_from_score(top_score)
        confidences.append(confidence)

        ok = case.check(top_song, top_score)
        if ok:
            passed += 1

        print(f"[{idx}] {case.name}: {'PASS' if ok else 'FAIL'}")
        print(f"    expected: {case.expectation}")
        print(
            "    got: "
            f"{top_song.get('title', 'Unknown')} "
            f"({top_song.get('genre', 'n/a')}, {top_song.get('mood', 'n/a')}) "
            f"score={top_score:.2f}, confidence={confidence:.2f}"
        )
        print(f"    explanation: {explanation}")

    total = len(cases)
    avg_confidence = sum(confidences) / total if total else 0.0
    print("\n=== Summary ===")
    print(f"Pass rate: {passed}/{total}")
    print(f"Average confidence: {avg_confidence:.2f}")

    return passed, total, avg_confidence


if __name__ == "__main__":
    run_harness()
