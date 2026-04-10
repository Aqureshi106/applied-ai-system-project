from src.recommender import Song, UserProfile, Recommender

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
