from src.recommender import Song, UserProfile, Recommender, recommend_songs

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
            popularity=92,
            release_year=2024,
            release_decade="2020s",
            mood_tags="euphoric, glossy, uplifting",
            era_descriptor="current",
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
            popularity=48,
            release_year=1998,
            release_decade="1990s",
            mood_tags="nostalgic, warm, dusty",
            era_descriptor="retro",
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_advanced_metadata_changes_rankings():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
        target_popularity=90,
        preferred_decade="2020s",
        preferred_mood_tags="euphoric, glossy",
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert results[0].title == "Test Pop Track"
    explanation = rec.explain_recommendation(user, results[0])
    assert "popularity" in explanation.lower()
    assert "mood tag" in explanation.lower() or "era vibe" in explanation.lower()


def test_scoring_modes_change_the_top_song():
    songs = [
        Song(
            id=1,
            title="Genre First Pop",
            artist="Test Artist",
            genre="pop",
            mood="chill",
            energy=0.8,
            tempo_bpm=120,
            valence=0.7,
            danceability=0.8,
            acousticness=0.2,
            popularity=85,
            release_year=2024,
            release_decade="2020s",
            mood_tags="uplifting",
            era_descriptor="current",
        ),
        Song(
            id=2,
            title="Mood First Happy",
            artist="Test Artist",
            genre="lofi",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.7,
            danceability=0.8,
            acousticness=0.2,
            popularity=85,
            release_year=2024,
            release_decade="2020s",
            mood_tags="uplifting",
            era_descriptor="current",
        ),
    ]
    rec = Recommender(songs)
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )

    genre_first = rec.recommend(user, k=1, mode="genre-first")[0]
    mood_first = rec.recommend(user, k=1, mode="mood-first")[0]

    assert genre_first.title == "Genre First Pop"
    assert mood_first.title == "Mood First Happy"


def test_explanation_includes_retrieved_catalog_evidence():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    top_song = rec.recommend(user, k=1)[0]

    explanation = rec.explain_recommendation(user, top_song)
    assert "supported by similar catalog examples" in explanation


def test_guardrails_normalize_bad_inputs_and_invalid_mode():
    songs = [
        {
            "id": 1,
            "title": "Guardrail Song",
            "artist": "Test",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.95,
            "tempo_bpm": 128,
            "valence": 0.85,
            "danceability": 0.88,
            "acousticness": 0.1,
            "popularity": 90,
            "release_year": 2024,
            "release_decade": "2020s",
            "mood_tags": "euphoric, uplifting",
            "era_descriptor": "current",
        }
    ]
    prefs = {
        "genre": "pop",
        "mood": "happy",
        "energy": 4.5,
        "likes_acoustic": "False",
        "target_tempo": 400,
        "target_valence": 3.0,
    }

    results = recommend_songs(prefs, songs, k=-5, mode="totally-unknown-mode")

    assert len(results) == 1
    assert results[0][0]["title"] == "Guardrail Song"
