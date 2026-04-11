# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Real recommendation systems usually combine many signals, such as user behavior and item features, to predict what feels like a good next option. In this project, each `Song` uses genre, mood, energy, tempo, valence, danceability, and acousticness. The `UserProfile` stores a favorite genre, favorite mood, target energy level, and whether the user prefers acoustic songs. The `Recommender` gives each song a score using a simple recipe: genre matches are worth 2 points, mood matches are worth 1 point, and energy adds similarity points based on how close the song is to the user’s target. It then sorts the catalog from best match to weakest match and returns the top songs. This version prioritizes songs that match the user’s style and overall vibe, rather than just choosing the highest or lowest values.

### Algorithm Recipe

1. Load the songs from `data/songs.csv`.
2. Compare each song to the user's preferences one song at a time.
3. Add 2 points when the song matches the user's favorite genre.
4. Add 1 point when the song matches the user's favorite mood.
5. Add similarity points for energy based on how close the song is to the user's target energy.
6. Sort all songs by total score from highest to lowest.
7. Return the top K songs as the final recommendations.

### Potential Biases

This system might over-prioritize genre and energy, causing it to miss great songs that match the user's mood or overall vibe in a less direct way. Because the dataset is small and fixed, it can also reflect the limits of the catalog instead of the full range of real musical taste.

### Data Flow

```mermaid
flowchart TD
   A["<b>User Prefs</b><br/>(genre, mood, energy,<br/>acoustic, tempo, valence,<br/>danceability, popularity,<br/>decade, mood_tags)"] --> D
   B["Load songs from CSV"] --> C["For each song"]
   M["<b>Scoring Mode</b><br/>(balanced / genre-first /<br/>mood-first / energy-focused)"] --> D
   C --> D["<b>Score song</b><br/>genre match<br/>mood match<br/>energy similarity<br/>tempo, valence, danceability<br/>popularity, decade, tags, era<br/>acoustic preference"]
   D --> E["Store score & reasons"]
   E --> F["Sort by score desc<br/>(title as tiebreaker)"]
   F --> G["Return Top K"]

```

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Terminal Output Screenshots

The screenshots below show top-5 terminal recommendations for adversarial and edge-case profiles used to stress-test the scoring logic.

1. Conflicting mood vs energy

![Profile 1 - Conflicting mood vs energy](docs/edge-profile-screenshots/profile-1-conflicting-mood-vs-energy.png)

2. String-bool trap for acoustic preference

![Profile 2 - String-bool trap](docs/edge-profile-screenshots/profile-2-string-bool-trap.png)

3. Out-of-range high energy

![Profile 3 - Out-of-range high energy](docs/edge-profile-screenshots/profile-3-out-of-range-high-energy.png)

4. Out-of-range negative energy

![Profile 4 - Out-of-range negative energy](docs/edge-profile-screenshots/profile-4-out-of-range-negative-energy.png)

5. Unknown genre and unknown mood

![Profile 5 - Unknown genre and mood](docs/edge-profile-screenshots/profile-5-unknown-genre-mood.png)

6. Empty categorical fields with numeric targeting

![Profile 6 - Empty categorical fields](docs/edge-profile-screenshots/profile-6-empty-categorical.png)

7. Impossible preference bundle

![Profile 7 - Impossible preference bundle](docs/edge-profile-screenshots/profile-7-impossible-bundle.png)

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Experiments You Tried

## Pair 1: Normal Pop Profile vs Conflicting Mood+Energy Profile

**Normal Profile:** pop, happy, energy=0.85, no acoustic preference  
**Top 1:** Sunrise City (pop, happy, energy=0.82)

**Conflicting Profile:** lofi, sad, energy=0.90, acoustic preference=true  
**Top 1:** Final Frontier (cinematic, epic, energy=0.70, acousticness=0.81)

**What changed:** The normal pop profile gets a song that directly matches genre, mood, and energy. The conflicting profile gets a song that matches *none* of those categorical preferences but has high acousticness.

**Why it makes sense:** In the conflicting profile, mood and genre don't match, but energy is close (0.90 vs 0.70), and acousticness is very high (0.81). The scoring logic weights acoustic preference (+2.0) and energy closeness heavily, so Final Frontier wins despite missing the user's stated vibe. This reveals a **real weakness**: when a user asks for "lofi sad" but has energy=0.90, the system resolves this contradiction by favoring numeric fit over semantic intent. A human listener would probably say "that doesn't match lofi" even if the math works out.

---

## Pair 2: Standard Pop Profile vs Empty Categories Profile

**Standard Profile:** pop, happy, energy=0.85, danceability=0.82, etc.  
**Top 3:** Sunrise City (pop), Gym Hero (pop), Rooftop Lights (indie pop)

**Empty Categories Profile:** genre="", mood="", energy=0.82, numeric targets only  
**Top 1:** Sunrise City (pop, energy=0.82)  
**Top 3:** Neon Heatwave (electronic), Street Pulse (hip hop)

**What changed:** When genre and mood are removed as constraints, Street Pulse (hip hop) and Neon Heatwave (electronic) climb into the top 5. They don't match "pop" but they have high energy and danceability that match the numeric targets.

**Why it makes sense:** This shows the difference between *semantic* matching (genre labels) and *numeric* matching (energy, danceability, etc.). When the user doesn't specify a genre, the system has no reason to prefer pop songs—it just finds songs with the right "feel" numbers. A non-programmer would say: "If I don't tell you I like pop, why are you recommending pop? You should just find me energetic, danceable songs, and that could be hip-hop too."

---

## Pair 3: Acoustic Lover vs Acoustic Hater (Same Genre/Mood)

**Acoustic Lover:** pop, happy, likes_acoustic=True  
Expected top picks: songs with high acousticness + pop/happy

**Acoustic Hater:** pop, happy, likes_acoustic=False  
Expected top picks: songs with low acousticness + pop/happy

**What makes sense:** The acoustic bonus in the scorer is a binary cliff—songs jump from 0 to +2.0 points based on acousticness thresholds. This means a song like Rooftop Lights (indie pop, acousticness=0.35) gets +1.0 for an acoustic-hater but +0.0 for an acoustic-lover. Same song, totally different treatment. 

**Reality check:** In practice, this works well when preferences are clear, but it can create weird ranking flips. A song at acousticness=0.46 is slightly better for acoustic-lovers, but at acousticness=0.44 it's slightly better for haters. That's not how human taste works—we don't have exact thresholds.

---

## Pair 4: Original Weights vs Doubled-Energy Weights

**Original:** genre=+2.0, energy=max(0, 3.0 - gap*6.0)  
**Conflicting Profile Top 1:** Final Frontier (score=6.57)

**After Shift:** genre=+1.0, energy=max(0, 6.0 - gap*12.0)  
**Conflicting Profile Top 1:** Final Frontier (score=8.37)

**What changed:** The same song stayed at #1, but its score jumped 1.80 points. Scores got bigger because energy contribution doubled. For high-energy profiles, the shift pushes high-energy songs even higher—some songs that were #4 or #5 moved to #2 or #3.

**Why it makes sense:** Energy became twice as important in the math, so every unit of energy-closeness counted for more. If you double the weight on one factor, songs that match it well rise, and songs that don't match it well drop. This is a straightforward consequence of changing the formula.

**The problem:** Even though the math is logical, the results don't always feel better. Halving genre importance means a song that perfectly matches your favorite genre but has mediocre energy can now lose to a song from a totally different genre that has slightly better energy. That might not match what a human would choose.

---

## Pair 5: Mood-Disabled Profile vs Mood-Enabled Profile

**Mood Enabled (Original):**  
- Users asking for "happy" would get songs marked "happy" (+1.0 bonus)
- Top 1 for pop/happy profile: Sunrise City (pop, happy)

**Mood Disabled (Current Experimental):**  
- Mood labels are ignored; energy/acousticness/danceability dominate
- Top 1 for pop/happy profile: Still Sunrise City, but for different reasons
  - It's not +1 for matching mood; the score is higher because energy is closer

**What changed:** Removing mood didn't flip the top results much because energy was already very important. But the *reason* each song ranked high changed.

**Why it matters:** This reveals that energy was already dominating. Removing mood didn't break the system—it just confirmed that mood wasn't the main driver to begin with. A non-programmer would say: "If I'm happy and want happy songs, shouldn't the system care that the song is labeled happy? But it turns out the system mostly just cares if the song feels high-energy."

---

## Pair 6: "Impossible" Profile vs "Unknown" Profile

**Impossible Profile:** classical, intense, energy=0.95, high danceability  
(Classical music is rarely intense or high-energy or danceable)

**Top 1:** Gym Hero (pop, intense, energy=0.93, danceability=0.88)

**Unknown Profile:** hyperpop, melancholy, energy=0.60  
(These genre/mood are not in the catalog)

**Top 1:** Night Drive Loop (synthwave, moody, energy=0.75)

**What changed:** Both profiles are unrealistic, but they behaved differently. The impossible profile got a song that matches the *energy/danceability* but not the genre. The unknown profile got a song that's *similar in vibe* even though the exact genre/mood don't exist.

**Why it makes sense:** When preferences are impossible to satisfy exactly, the scorer falls back to numeric proximity. The impossible profile wanted high-energy danceability, so it lands on Gym Hero. The unknown profile wanted moderate energy with a moody feel, so it lands on synthwave. Neither result is perfect, but they're reasonable substitutes—the system defaulted to numeric safety.

---

## Overall Insight

**"Why does Gym Hero keep showing up?"**

Gym Hero (pop, intense, energy=0.93, danceability=0.88) appears frequently because it's *numerically central* to many profiles:
- High energy users see it (0.93 is close to many targets)
- Pop lovers see it (genre match +1.0)
- Danceability-focused users see it (0.88 is high)

Even though it's marked "intense" not "happy," it still ranks high for happy-pop profiles because its energy score overwhelms the mood mismatch (which no longer counts with mood disabled).

**The lesson:** The system is optimizing for numeric proximity more than semantic vibe. If the dataset had more truly diverse songs—slow danceables, high-energy introspective songs, etc.—Gym Hero wouldn't dominate. But with an 18-song catalog where high-energy pop is common, Gym Hero becomes a "default winner" that keeps appearing because it checks multiple boxes at once.

---

## Limitations and Risks

This recommender works for classroom simulation, but it has important limitations:

- Tiny catalog bias: With only 18 songs, results reflect what is available more than what users truly want. Underrepresented genres (like metal) often get weak matches.
- Feature-limited understanding: The model only uses structured metadata (genre, mood, energy, tempo, valence, danceability, acousticness). It does not understand lyrics, language, culture, or context.
- Numeric-over-semantic behavior: The scorer can prefer songs with close numeric values even when genre/mood labels feel wrong to a human listener.
- Weight sensitivity: Small changes to feature weights can noticeably change rankings, which makes behavior unstable and design choices subjective.
- Threshold effects: Acoustic preference uses hard cutoffs, so near-threshold songs can flip ranking abruptly in ways that may feel unnatural.
- No personalization memory: The system does not learn from listening history, skips, or feedback, so recommendations do not improve over time.
- Fairness risk: If used in a real product, over-weighting dominant genres or moods could repeatedly surface similar songs and reduce diversity for users with niche tastes.

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Building this recommender showed me how user preferences become a prediction when they are converted into numeric features and weights. The model does not "understand" music like a person; it computes similarity across fields like energy, tempo, valence, danceability, and acousticness, then ranks songs by total score. Through testing, I learned that even simple weight choices strongly shape outcomes. For example, when energy has a large weight, songs with close energy values can outrank songs that better match the user's stated genre or mood. That made it clear that recommendation quality is not just about data, but also about design decisions in the scoring formula.

I also learned how bias and unfairness can appear in subtle ways. Because the catalog is small and uneven across genres, users with underrepresented tastes can receive weaker or less relevant results. The system can also over-recommend songs that are numerically central, which reduces diversity and constantly favors certain styles. These patterns may seem unfair to users who expect recommendations to reflect identity, culture, or mood nuance rather than only numeric proximity. This project reinforced that human judgment still matters: we need to evaluate whether outputs feel appropriate, not just whether the math is internally consistent.


---

## 7. `model_card_template.md`

Combines reflection and model card framing from the Module 3 guidance. :contentReference[oaicite:2]{index=2}  

```markdown
# 🎧 Model Card - Music Recommender Simulation

## 1. Model Name

BeatMatcher Mini 1.0

---

## 2. Intended Use

This model recommends 3 to 5 songs from a small, fixed catalog based on a user's stated preferences. It is designed for classroom learning about recommendation systems, not for production use.

Target users are students and instructors exploring how feature-based scoring works and how design choices can create bias.

---

## 3. How It Works (Short Explanation)

The recommender compares each song to a user profile and computes a total match score. The profile includes preferred genre, mood, energy target, acoustic preference, and optional numeric targets (tempo, valence, danceability).

Songs gain points for matching categorical preferences and for being numerically close to target values. In practice, energy similarity and acoustic preference can strongly influence ranking. After scoring all songs, the system sorts by score and returns the top results.

---

## 4. Data

The dataset in data/songs.csv contains 18 songs.

Each song includes:
- title and artist
- genre and mood labels
- energy, tempo_bpm, valence, danceability, acousticness

I did not add or remove songs from the provided catalog. The data covers several genres (for example pop, lofi, rock, jazz, electronic, metal, classical, hip hop), but representation is uneven. Some styles have only one song, so the catalog mostly reflects a narrow, synthetic sample rather than broad real-world listening diversity.

---

## 5. Strengths

- Transparent behavior: The scoring logic is easy to explain and debug.
- Strong performance on in-catalog preferences: Users with common profiles (for example pop + high energy or lofi + chill) receive results that feel intuitive.
- Good for experimentation: Weight changes and feature toggles quickly show how ranking behavior shifts.
- Fast and simple: No training step is required; scoring runs directly on metadata.

---

## 6. Limitations and Bias

- Small catalog limitation: Results are constrained by only 18 songs, which can cause weak matches for niche preferences.
- Representation bias: Underrepresented genres are disadvantaged because there are fewer candidates to recommend.
- Numeric-over-semantic bias: Songs with close numeric values can outrank songs that better match the user's stated genre or mood intent.
- Weight sensitivity: Minor weight changes can produce large ranking changes, making output stability fragile.
- Threshold artifacts: Acoustic preference uses hard cutoffs, so near-threshold songs can flip rank abruptly.
- Diversity risk: The same "central" songs can appear repeatedly across profiles, reducing recommendation variety.

If this were deployed in a real app, these effects could feel unfair to users whose taste is less represented in the catalog.

---

## 7. Evaluation

I evaluated the model with both normal and edge-case profiles and reviewed top-5 recommendations for each case.

Evaluation scenarios included:
- normal profiles (for example pop/happy/high-energy)
- conflicting profiles (for example lofi/sad with very high energy)
- empty or unknown categorical preferences
- impossible preference bundles
- mood-enabled vs mood-disabled comparisons
- changed scoring weights (original vs energy-heavy)

I also ran automated tests in tests/test_recommender.py. I did not use a formal numeric metric like precision@k; evaluation was qualitative, focused on whether outputs matched user intent and whether ranking changes were explainable.

---

## 8. Future Work

- Expand the catalog to improve genre and mood coverage.
- Rebalance weights so one strong numeric feature does not dominate semantic intent.
- Replace hard acoustic thresholds with smoother scoring.
- Add diversity-aware reranking so top results are less repetitive.
- Reintroduce and calibrate mood influence to better capture emotional intent.
- Add lightweight feedback loops so the system can adapt to a user's skips/likes over time.

---

## 9. Personal Reflection

This project made it clear that recommenders are not just about data; they are about choices in representation and weighting. Turning taste into numbers is powerful, but it can also flatten meaning. I was surprised by how often energy proximity overruled genre or mood expectations, especially in edge cases.

It also changed how I think about fairness in recommendation systems. Bias does not only come from harmful labels; it can come from coverage gaps, objective functions, and design defaults that repeatedly favor some tastes over others. Human judgment still matters for deciding whether recommendations feel appropriate, diverse, and respectful of user intent.