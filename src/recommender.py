import csv
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
    likes_acoustic = bool(_profile_value(user_prefs, "likes_acoustic", False))
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

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        """Initialize the recommender with a list of songs."""
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5, mode: str = "balanced") -> List[Song]:
        """Return the top-k songs for a user profile."""
        scored_songs = []
        for song in self.songs:
            score, _ = self._score_song(user, song, mode=mode)
            scored_songs.append((score, song))

        scored_songs.sort(key=lambda item: (-item[0], item[1].title))
        return [song for _, song in scored_songs[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song, mode: str = "balanced") -> str:
        """Return a semicolon-separated explanation for one recommendation."""
        _, reasons = self._score_song(user, song, mode=mode)
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

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            songs.append(
                {
                    "id": _safe_int(row.get("id")),
                    "title": row.get("title", "").strip(),
                    "artist": row.get("artist", "").strip(),
                    "genre": row.get("genre", "").strip(),
                    "mood": row.get("mood", "").strip(),
                    "energy": _safe_float(row.get("energy")),
                    "tempo_bpm": _safe_float(row.get("tempo_bpm")),
                    "valence": _safe_float(row.get("valence")),
                    "danceability": _safe_float(row.get("danceability")),
                    "acousticness": _safe_float(row.get("acousticness")),
                    "popularity": _safe_int(row.get("popularity"), 50),
                    "release_year": _safe_int(row.get("release_year"), 2000),
                    "release_decade": row.get("release_decade", "").strip(),
                    "mood_tags": row.get("mood_tags", "").strip(),
                    "era_descriptor": row.get("era_descriptor", "").strip(),
                }
            )
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
    scored_songs: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, mode=mode)
        scored_songs.append((song, score, "; ".join(reasons)))

    scored_songs.sort(key=lambda item: (-item[1], item[0].get("title", "")))
    return scored_songs[:k]
