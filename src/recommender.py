import csv
import logging
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Clamp a numeric value to the provided inclusive range."""
    return max(minimum, min(maximum, value))


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert a value to float or return a default when conversion fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int = 0) -> int:
    """Convert a value to int or return a default when conversion fails."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _profile_value(profile: object, key: str, default: object) -> object:
    """Read a preference from a dict or object profile with fallback."""
    if isinstance(profile, dict):
        return profile.get(key, default)
    return getattr(profile, key, default)


def _coerce_bool(value: object, default: bool = False) -> bool:
    """Parse bool-like values safely, including common string forms."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default

    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off", ""}:
        return False
    return default


def _mood_tempo_target(mood: str) -> float:
    """Return a default tempo target for a given mood label."""
    targets = {
        "happy": 122.0,
        "intense": 140.0,
        "chill": 78.0,
        "relaxed": 88.0,
        "focused": 82.0,
        "moody": 102.0,
    }
    return targets.get(mood.lower(), 100.0)


def _mood_valence_target(mood: str) -> float:
    """Return a default valence target for a given mood label."""
    targets = {
        "happy": 0.82,
        "intense": 0.48,
        "chill": 0.60,
        "relaxed": 0.68,
        "focused": 0.56,
        "moody": 0.42,
    }
    return targets.get(mood.lower(), 0.58)


def _mood_decade_target(mood: str) -> str:
    """Return a default release decade target for a given mood label."""
    targets = {
        "nostalgic": "1990s",
        "retro": "1980s",
        "throwback": "2000s",
        "classic": "1970s",
        "futuristic": "2020s",
    }
    return targets.get(mood.lower(), "")


def _split_tokens(value: object) -> List[str]:
    """Normalize comma-separated or list-like tokens into unique lowercase tags."""
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        raw_text = ",".join(str(item) for item in value)
    else:
        raw_text = str(value)

    tokens: List[str] = []
    seen = set()
    for chunk in raw_text.replace("|", ",").replace(";", ",").replace("/", ",").split(","):
        token = chunk.strip().lower()
        if token and token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _parse_decade(value: object) -> Optional[int]:
    """Convert decade-like text into its numeric decade start."""
    if value is None:
        return None

    text = str(value).strip().lower()
    if not text:
        return None

    digits = "".join(character for character in text if character.isdigit())
    if len(digits) >= 4:
        return (int(digits[:4]) // 10) * 10
    if len(digits) == 2:
        year = int(digits)
        if year >= 50:
            year += 1900
        else:
            year += 2000
        return (year // 10) * 10
    return None


def _decade_label(decade_start: Optional[int]) -> str:
    """Format a numeric decade start like 1990 into a readable label."""
    if decade_start is None:
        return ""
    return f"{decade_start}s"


def _decade_alignment_score(song_decade: str, song_year: int, preferred_decade: str) -> float:
    """Reward songs that sit close to the listener's target era."""
    preferred_start = _parse_decade(preferred_decade)
    if preferred_start is None:
        return 0.0

    song_start = _parse_decade(song_decade)
    if song_start is None and song_year:
        song_start = (song_year // 10) * 10

    if song_start is None:
        return 0.0

    distance = abs(song_start - preferred_start) // 10
    if distance == 0:
        return 1.4
    if distance == 1:
        return 0.8
    if distance == 2:
        return 0.35
    return 0.0


def _era_descriptor_target(preferred_decade: str, preferred_tags: List[str]) -> str:
    """Infer an era descriptor from the listener's requested era cues."""
    tag_set = set(preferred_tags)
    if tag_set.intersection({"nostalgic", "retro", "throwback", "vintage"}):
        return "retro"

    preferred_start = _parse_decade(preferred_decade)
    if preferred_start is None:
        return ""

    if preferred_start <= 1989:
        return "retro"
    if preferred_start <= 1999:
        return "throwback"
    if preferred_start <= 2009:
        return "millennial"
    if preferred_start <= 2019:
        return "modern"
    return "current"


def _mode_weights(mode: str) -> Dict[str, float]:
    """Return the weighting preset for a scoring mode."""
    normalized_mode = str(mode).strip().lower()
    presets: Dict[str, Dict[str, float]] = {
        "balanced": {
            "genre": 1.0,
            "mood": 1.0,
            "energy": 1.0,
            "tempo": 1.0,
            "valence": 1.0,
            "danceability": 1.0,
            "popularity": 1.0,
            "decade": 1.0,
            "tags": 1.0,
            "era": 1.0,
            "acoustic": 1.0,
        },
        "genre-first": {
            "genre": 2.6,
            "mood": 0.8,
            "energy": 0.9,
            "tempo": 0.9,
            "valence": 0.8,
            "danceability": 0.9,
            "popularity": 0.8,
            "decade": 0.8,
            "tags": 0.9,
            "era": 0.8,
            "acoustic": 0.9,
        },
        "mood-first": {
            "genre": 0.8,
            "mood": 2.6,
            "energy": 0.9,
            "tempo": 1.0,
            "valence": 1.2,
            "danceability": 0.95,
            "popularity": 0.85,
            "decade": 1.1,
            "tags": 1.5,
            "era": 1.1,
            "acoustic": 0.95,
        },
        "energy-focused": {
            "genre": 0.7,
            "mood": 0.85,
            "energy": 2.8,
            "tempo": 1.2,
            "valence": 0.95,
            "danceability": 1.1,
            "popularity": 0.85,
            "decade": 0.8,
            "tags": 0.9,
            "era": 0.8,
            "acoustic": 0.8,
        },
    }
    return presets.get(normalized_mode, presets["balanced"])


def _acoustic_bonus(acousticness: float, likes_acoustic: bool) -> float:
    """Compute the acoustic preference bonus for a song."""
    if likes_acoustic:
        if acousticness >= 0.75:
            return 2.0
        if acousticness >= 0.45:
            return 1.0
        return 0.0

    if acousticness <= 0.25:
        return 2.0
    if acousticness <= 0.50:
        return 1.0
    return 0.0


def _score_song_dict(user_prefs: Dict, song: Dict, mode: str = "balanced") -> Tuple[float, List[str]]:
    """Score a song dict against user preferences and return reasons."""
    score = 0.0
    reasons: List[str] = []
    weights = _mode_weights(mode)

    user_genre = str(_profile_value(user_prefs, "genre", "")).strip().lower()
    user_mood = str(_profile_value(user_prefs, "mood", "")).strip().lower()
    target_energy = _safe_float(_profile_value(user_prefs, "energy", 0.5), 0.5)
    likes_acoustic = _coerce_bool(_profile_value(user_prefs, "likes_acoustic", False), False)
    target_tempo = _safe_float(_profile_value(user_prefs, "target_tempo", _mood_tempo_target(user_mood)), _mood_tempo_target(user_mood))
    target_valence = _safe_float(_profile_value(user_prefs, "target_valence", _mood_valence_target(user_mood)), _mood_valence_target(user_mood))
    target_danceability = _safe_float(_profile_value(user_prefs, "target_danceability", 0.60), 0.60)
    target_popularity = _safe_float(_profile_value(user_prefs, "target_popularity", 60.0), 60.0)
    preferred_decade = str(_profile_value(user_prefs, "preferred_decade", "")).strip().lower()
    preferred_mood_tags = _split_tokens(_profile_value(user_prefs, "preferred_mood_tags", ""))

    song_genre = str(song.get("genre", "")).strip().lower()
    song_mood = str(song.get("mood", "")).strip().lower()
    song_energy = _safe_float(song.get("energy", 0.0), 0.0)
    song_tempo = _safe_float(song.get("tempo_bpm", 0.0), 0.0)
    song_valence = _safe_float(song.get("valence", 0.0), 0.0)
    song_acousticness = _safe_float(song.get("acousticness", 0.0), 0.0)
    song_danceability = _safe_float(song.get("danceability", 0.0), 0.0)
    song_popularity = _safe_float(song.get("popularity", 0.0), 0.0)
    song_release_year = _safe_int(song.get("release_year", 0), 0)
    song_release_decade = str(song.get("release_decade", "")).strip().lower()
    song_mood_tags = _split_tokens(song.get("mood_tags", ""))
    song_era_descriptor = str(song.get("era_descriptor", "")).strip().lower()

    if not preferred_decade:
        preferred_decade = _mood_decade_target(user_mood)

    if not preferred_mood_tags and user_mood:
        preferred_mood_tags = [user_mood]

    if user_genre and song_genre == user_genre:
        score += 1.0 * weights["genre"]
        reasons.append(f"matches your favorite genre ({song.get('genre')})")

    if user_mood and song_mood == user_mood:
        score += 1.0 * weights["mood"]
        reasons.append(f"matches your favorite mood ({song.get('mood')})")

    energy_gap = abs(song_energy - target_energy)
    energy_score = max(0.0, 6.0 - (energy_gap * 12.0)) * weights["energy"]
    score += energy_score
    reasons.append(f"energy is close to your target ({song_energy:.2f})")

    tempo_gap = abs(song_tempo - target_tempo)
    tempo_score = max(0.0, 1.5 - (tempo_gap / 40.0)) * weights["tempo"]
    score += tempo_score

    valence_gap = abs(song_valence - target_valence)
    valence_score = max(0.0, 1.25 - (valence_gap * 2.5)) * weights["valence"]
    score += valence_score

    danceability_gap = abs(song_danceability - target_danceability)
    danceability_score = max(0.0, 1.0 - (danceability_gap * 2.0)) * weights["danceability"]
    score += danceability_score

    popularity_gap = abs(song_popularity - target_popularity)
    popularity_score = max(0.0, 1.3 - (popularity_gap / 30.0)) * weights["popularity"]
    score += popularity_score
    if popularity_score > 0.0:
        reasons.append(f"has popularity near your target ({song_popularity:.0f}/100)")

    decade_score = _decade_alignment_score(song_release_decade, song_release_year, preferred_decade) * weights["decade"]
    score += decade_score
    if decade_score > 0.0:
        inferred_decade = song_release_decade or _decade_label((song_release_year // 10) * 10 if song_release_year else None)
        reasons.append(f"fits your preferred era ({inferred_decade})")

    matched_tags = [tag for tag in song_mood_tags if tag in preferred_mood_tags]
    tag_score = min(1.8, len(matched_tags) * 0.6) * weights["tags"]
    score += tag_score
    if matched_tags:
        reasons.append(f"shares mood tags like {', '.join(matched_tags[:3])}")

    target_era = _era_descriptor_target(preferred_decade, preferred_mood_tags)
    if song_era_descriptor and target_era and song_era_descriptor == target_era:
        score += 0.9 * weights["era"]
        reasons.append(f"matches the {target_era} era vibe")

    acoustic_bonus = _acoustic_bonus(song_acousticness, likes_acoustic) * weights["acoustic"]
    score += acoustic_bonus
    if likes_acoustic and song_acousticness >= 0.45:
        reasons.append("leans acoustic, which you prefer")
    elif not likes_acoustic and song_acousticness <= 0.50:
        reasons.append("stays on the less acoustic side")

    if not reasons:
        reasons.append("fits the overall vibe profile")

    return score, reasons


def _normalize_user_prefs(user_prefs: Dict) -> Dict:
    """Normalize and guardrail raw preference dictionaries for stable scoring."""
    mood = str(_profile_value(user_prefs, "mood", "")).strip().lower()

    normalized: Dict = {
        "genre": str(_profile_value(user_prefs, "genre", "")).strip().lower(),
        "mood": mood,
        "energy": _clamp(_safe_float(_profile_value(user_prefs, "energy", 0.5), 0.5), 0.0, 1.0),
        "likes_acoustic": _coerce_bool(_profile_value(user_prefs, "likes_acoustic", False), False),
        "target_tempo": _clamp(
            _safe_float(_profile_value(user_prefs, "target_tempo", _mood_tempo_target(mood)), _mood_tempo_target(mood)),
            40.0,
            220.0,
        ),
        "target_valence": _clamp(_safe_float(_profile_value(user_prefs, "target_valence", _mood_valence_target(mood)), _mood_valence_target(mood))),
        "target_danceability": _clamp(_safe_float(_profile_value(user_prefs, "target_danceability", 0.60), 0.60)),
        "target_popularity": _clamp(_safe_float(_profile_value(user_prefs, "target_popularity", 60.0), 60.0), 0.0, 100.0),
        "preferred_decade": str(_profile_value(user_prefs, "preferred_decade", "")).strip().lower(),
        "preferred_mood_tags": ", ".join(_split_tokens(_profile_value(user_prefs, "preferred_mood_tags", ""))),
    }

    return normalized


def _dict_to_song(song: Dict) -> "Song":
    """Convert song dicts into Song dataclass values with safe defaults."""
    return Song(
        id=_safe_int(song.get("id", 0), 0),
        title=str(song.get("title", "")).strip(),
        artist=str(song.get("artist", "")).strip(),
        genre=str(song.get("genre", "")).strip(),
        mood=str(song.get("mood", "")).strip(),
        energy=_clamp(_safe_float(song.get("energy", 0.0), 0.0), 0.0, 1.0),
        tempo_bpm=_clamp(_safe_float(song.get("tempo_bpm", 100.0), 100.0), 40.0, 220.0),
        valence=_clamp(_safe_float(song.get("valence", 0.5), 0.5), 0.0, 1.0),
        danceability=_clamp(_safe_float(song.get("danceability", 0.5), 0.5), 0.0, 1.0),
        acousticness=_clamp(_safe_float(song.get("acousticness", 0.5), 0.5), 0.0, 1.0),
        popularity=_safe_int(song.get("popularity", 50), 50),
        release_year=_safe_int(song.get("release_year", 2000), 2000),
        release_decade=str(song.get("release_decade", "")).strip(),
        mood_tags=str(song.get("mood_tags", "")).strip(),
        era_descriptor=str(song.get("era_descriptor", "")).strip(),
    )


def _song_to_dict(song: "Song") -> Dict:
    """Convert Song dataclass values into dicts for functional compatibility."""
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "genre": song.genre,
        "mood": song.mood,
        "energy": song.energy,
        "tempo_bpm": song.tempo_bpm,
        "valence": song.valence,
        "danceability": song.danceability,
        "acousticness": song.acousticness,
        "popularity": song.popularity,
        "release_year": song.release_year,
        "release_decade": song.release_decade,
        "mood_tags": song.mood_tags,
        "era_descriptor": song.era_descriptor,
    }

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    popularity: int = 50
    release_year: int = 2000
    release_decade: str = ""
    mood_tags: str = ""
    era_descriptor: str = ""

@dataclass
class TasteProfile:
    """
    Represents the profile used for song-to-user comparisons.
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_tempo: float = 100.0
    target_valence: float = 0.58
    target_danceability: float = 0.60
    target_popularity: float = 60.0
    preferred_decade: str = ""
    preferred_mood_tags: str = ""


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_tempo: float = 100.0
    target_valence: float = 0.58
    target_danceability: float = 0.60
    target_popularity: float = 60.0
    preferred_decade: str = ""
    preferred_mood_tags: str = ""


@dataclass
class RecommendationPlan:
    """Represents a plan for the agentic recommendation workflow."""
    user_prefs: Dict
    mode: str
    k: int
    candidate_limit: int
    profile_warnings: List[str]

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    VALID_MODES = {"balanced", "genre-first", "mood-first", "energy-focused"}

    def __init__(self, songs: List[Song], enable_guardrails: bool = True):
        """Initialize the recommender with a list of songs."""
        self.songs = songs
        self.enable_guardrails = enable_guardrails
        self.logger = logging.getLogger("music_recommender")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        level_name = os.getenv("RECOMMENDER_LOG_LEVEL", "WARNING").upper()
        level = getattr(logging, level_name, logging.WARNING)
        self.logger.setLevel(level)

    def recommend(self, user: UserProfile, k: int = 5, mode: str = "balanced") -> List[Song]:
        """Return top-k songs via a planner-retriever-ranker-verifier workflow."""
        user_prefs = {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
            "target_tempo": user.target_tempo,
            "target_valence": user.target_valence,
            "target_danceability": user.target_danceability,
            "target_popularity": user.target_popularity,
            "preferred_decade": user.preferred_decade,
            "preferred_mood_tags": user.preferred_mood_tags,
        }

        plan = self._plan_recommendation(user_prefs, k, mode)
        candidates = self._retrieve_candidates(plan)
        ranked = self._rank_candidates(plan, candidates)
        finalized = self._verify_and_finalize(plan, ranked)
        return [song for _, song, _ in finalized[: plan.k]]

    def explain_recommendation(self, user: UserProfile, song: Song, mode: str = "balanced") -> str:
        """Return retrieval-augmented rationale for one recommendation."""
        _, reasons = self._score_song(user, song, mode=mode)
        evidence = self._retrieve_explanation_evidence(song, user)
        if evidence:
            reasons.append(f"supported by similar catalog examples: {', '.join(evidence)}")
        return "; ".join(reasons)

    def _score_song(self, user: UserProfile, song: Song, mode: str = "balanced") -> Tuple[float, List[str]]:
        """Adapt dataclass inputs into dicts and reuse shared scoring."""
        user_prefs = {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
            "target_tempo": user.target_tempo,
            "target_valence": user.target_valence,
            "target_danceability": user.target_danceability,
            "target_popularity": user.target_popularity,
            "preferred_decade": user.preferred_decade,
            "preferred_mood_tags": user.preferred_mood_tags,
        }
        song_dict = {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "genre": song.genre,
            "mood": song.mood,
            "energy": song.energy,
            "tempo_bpm": song.tempo_bpm,
            "valence": song.valence,
            "danceability": song.danceability,
            "acousticness": song.acousticness,
            "popularity": song.popularity,
            "release_year": song.release_year,
            "release_decade": song.release_decade,
            "mood_tags": song.mood_tags,
            "era_descriptor": song.era_descriptor,
        }
        return _score_song_dict(user_prefs, song_dict, mode=mode)

    def _plan_recommendation(self, user_prefs: Dict, k: int, mode: str) -> RecommendationPlan:
        """Build a constrained plan that drives the recommendation workflow."""
        normalized_prefs = _normalize_user_prefs(user_prefs)
        safe_mode = mode if mode in self.VALID_MODES else "balanced"
        safe_k = max(1, _safe_int(k, 5))

        warnings: List[str] = []
        if safe_mode != mode:
            warnings.append(f"unknown mode '{mode}' replaced with '{safe_mode}'")
        if safe_k != k:
            warnings.append(f"invalid k '{k}' replaced with {safe_k}")

        candidate_limit = min(max(safe_k * 4, 10), len(self.songs)) if self.songs else 0
        plan = RecommendationPlan(
            user_prefs=normalized_prefs,
            mode=safe_mode,
            k=safe_k,
            candidate_limit=candidate_limit,
            profile_warnings=warnings,
        )
        if warnings:
            self.logger.warning("Guardrails applied: %s", "; ".join(warnings))
        self.logger.info("Planner created recommendation plan: mode=%s k=%s candidates=%s", plan.mode, plan.k, plan.candidate_limit)
        return plan

    def _retrieve_candidates(self, plan: RecommendationPlan) -> List[Song]:
        """Retrieve likely candidates before detailed ranking."""
        if not self.songs:
            return []

        genre_target = plan.user_prefs.get("genre", "")
        mood_target = plan.user_prefs.get("mood", "")
        tag_targets = set(_split_tokens(plan.user_prefs.get("preferred_mood_tags", "")))
        energy_target = _safe_float(plan.user_prefs.get("energy", 0.5), 0.5)

        retrieval_scores: List[Tuple[float, Song]] = []
        for song in self.songs:
            coarse = 0.0
            if genre_target and song.genre.strip().lower() == genre_target:
                coarse += 2.0
            if mood_target and song.mood.strip().lower() == mood_target:
                coarse += 2.0
            song_tags = set(_split_tokens(song.mood_tags))
            if tag_targets and song_tags:
                coarse += min(1.5, len(song_tags.intersection(tag_targets)) * 0.5)
            coarse += max(0.0, 1.5 - abs(song.energy - energy_target) * 2.0)
            coarse += max(0.0, 1.0 - abs(song.valence - _safe_float(plan.user_prefs.get("target_valence", 0.58), 0.58)) * 1.5)
            retrieval_scores.append((coarse, song))

        retrieval_scores.sort(key=lambda item: (-item[0], item[1].title))
        selected = [song for _, song in retrieval_scores[: plan.candidate_limit]]
        self.logger.info("Retriever selected %s/%s candidates", len(selected), len(self.songs))
        return selected

    def _rank_candidates(self, plan: RecommendationPlan, candidates: List[Song]) -> List[Tuple[float, Song, List[str]]]:
        """Score retrieved candidates with detailed feature matching."""
        ranked: List[Tuple[float, Song, List[str]]] = []
        for song in candidates:
            score, reasons = _score_song_dict(plan.user_prefs, _song_to_dict(song), mode=plan.mode)
            ranked.append((score, song, reasons))

        ranked.sort(key=lambda item: (-item[0], item[1].title))
        self.logger.info("Ranker produced %s scored candidates", len(ranked))
        return ranked

    def _verify_and_finalize(self, plan: RecommendationPlan, ranked: List[Tuple[float, Song, List[str]]]) -> List[Tuple[float, Song, List[str]]]:
        """Apply reliability guardrails and finalize deterministic outputs."""
        if not ranked:
            return []

        if not self.enable_guardrails:
            return ranked

        seen_titles = set()
        deduped: List[Tuple[float, Song, List[str]]] = []
        for score, song, reasons in ranked:
            title_key = song.title.strip().lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            deduped.append((score, song, reasons))

        top_window = deduped[: max(plan.k, 3)]
        if top_window and max(item[0] for item in top_window) < 1.5:
            fallback = sorted(
                deduped,
                key=lambda item: (-item[1].popularity, -item[0], item[1].title),
            )
            self.logger.warning("Low-confidence recommendation window detected; popularity fallback engaged")
            return fallback

        return deduped

    def _retrieve_explanation_evidence(self, song: Song, user: UserProfile, top_n: int = 2) -> List[str]:
        """Retrieve short catalog evidence snippets to ground explanations."""
        evidence_pool: List[Tuple[float, str]] = []
        song_tags = set(_split_tokens(song.mood_tags))
        user_tags = set(_split_tokens(user.preferred_mood_tags))

        for candidate in self.songs:
            if candidate.id == song.id:
                continue
            overlap = 0.0
            if candidate.genre.strip().lower() == song.genre.strip().lower():
                overlap += 1.0
            if candidate.mood.strip().lower() == song.mood.strip().lower():
                overlap += 1.0
            overlap += max(0.0, 0.8 - abs(candidate.energy - song.energy) * 1.5)
            overlap += min(0.8, len(song_tags.intersection(set(_split_tokens(candidate.mood_tags)))) * 0.3)
            overlap += min(0.8, len(user_tags.intersection(set(_split_tokens(candidate.mood_tags)))) * 0.3)
            evidence_pool.append((overlap, candidate.title))

        evidence_pool.sort(key=lambda item: (-item[0], item[1]))
        return [title for _, title in evidence_pool[:top_n] if title]

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    songs: List[Dict] = []
    logger = logging.getLogger("music_recommender")
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            song = {
                "id": _safe_int(row.get("id")),
                "title": row.get("title", "").strip(),
                "artist": row.get("artist", "").strip(),
                "genre": row.get("genre", "").strip(),
                "mood": row.get("mood", "").strip(),
                "energy": _clamp(_safe_float(row.get("energy"))),
                "tempo_bpm": _clamp(_safe_float(row.get("tempo_bpm"), 100.0), 40.0, 220.0),
                "valence": _clamp(_safe_float(row.get("valence"), 0.5)),
                "danceability": _clamp(_safe_float(row.get("danceability"), 0.5)),
                "acousticness": _clamp(_safe_float(row.get("acousticness"), 0.5)),
                "popularity": _safe_int(row.get("popularity"), 50),
                "release_year": _safe_int(row.get("release_year"), 2000),
                "release_decade": row.get("release_decade", "").strip(),
                "mood_tags": row.get("mood_tags", "").strip(),
                "era_descriptor": row.get("era_descriptor", "").strip(),
            }
            if not song["title"]:
                logger.warning("Skipping CSV row without title: id=%s", song["id"])
                continue
            songs.append(song)
    return songs

def score_song(user_prefs: Dict, song: Dict, mode: str = "balanced") -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py
    """
    return _score_song_dict(user_prefs, song, mode=mode)

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5, mode: str = "balanced") -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    recommender = Recommender([_dict_to_song(song) for song in songs])
    normalized_prefs = _normalize_user_prefs(user_prefs)
    plan = recommender._plan_recommendation(normalized_prefs, k, mode)
    candidates = recommender._retrieve_candidates(plan)
    ranked = recommender._rank_candidates(plan, candidates)
    finalized = recommender._verify_and_finalize(plan, ranked)

    outputs: List[Tuple[Dict, float, str]] = []
    for score, song, reasons in finalized[: plan.k]:
        outputs.append((_song_to_dict(song), score, "; ".join(reasons)))
    return outputs
