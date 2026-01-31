import os
import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# Gemini AI 
from google import genai

from database import get_db
from models import Movie, Mood, MovieMood
from schemas import MovieRecommendationRequest

# Reads API key from environment variable GEMINI_API_KEY
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

router = APIRouter()


@router.post("/movierecommendationuserinput")
async def receive_user_input(request: MovieRecommendationRequest, db: AsyncSession = Depends(get_db)):
    m1 = 'Love · Romance · Family · Community · Belonging · Home'
    m2 = 'Happy · Playful · Bright · Feel-good · Carefree'
    m3 = 'Hopeful · Healing · Optimistic · Reassuring'
    m4 = 'Excited · Adventurous · Fun · Escapist'
    m5 = 'Reflective · Introspective · Contemplative About Life'
    m6 = 'Calm · Peaceful · Relaxed · Soft · Gentle'
    m7 = 'Curious · Engaged · Intrigued · Mentally Active'
    m8 = 'Intense · Emotional · Cathartic · Bittersweet'
    m9 = 'Lonely · Isolated · Unseen · Longing'
    m10 = 'Angry · Frustrated · Irritated · Stressed'
    m11 = 'Hopeless · Sad · Heartbroken · Melancholy'
    m12 = 'Scared · Anxious · Uneasy · Tense · Nervous'

    # Mood Repair Map: Logic to shift from negative to positive states
    mood_repair_map = {
        m8:  [m2, m3, m6],
        m9:  [m1, m3, m4],
        m10: [m6, m2, m5],
        m11: [m3, m2, m1],
        m12: [m6, m3, m2],
    }

    try:
        # STEP 1 Determine target moods based on user preference
        target_mood_strings = []
        if request.preference == 'congruence':
            target_mood_strings = request.moods
        else:
            for user_mood in request.moods:
                repair_targets = mood_repair_map.get(user_mood, [user_mood])
                target_mood_strings.extend(repair_targets)
            target_mood_strings = list(set(target_mood_strings))  # remove duplicates

        # STEP 2 Fetch movies with relevant moods
        stmt = (
            select(Movie, MovieMood.score, Mood.mood_name)
            .join(MovieMood, Movie.id == MovieMood.movie_id)
            .join(Mood, MovieMood.mood_id == Mood.id)
            .where(Mood.mood_name.in_(target_mood_strings))
            .options(selectinload(Movie.moods))
        )
        result = await db.execute(stmt)
        rows = result.all()

        # STEP 3 Get all moods for each movie
        all_moods_stmt = (
            select(Movie.id, Mood.mood_name, MovieMood.score)
            .join(MovieMood, Movie.id == MovieMood.movie_id)
            .join(Mood, MovieMood.mood_id == Mood.id)
        )
        all_moods_result = await db.execute(all_moods_stmt)
        all_moods_rows = all_moods_result.all()

        movie_all_moods = {}
        for movie_id, mood_name, mood_score in all_moods_rows:
            movie_all_moods.setdefault(movie_id, []).append({
                "mood": mood_name,
                "score": round(float(mood_score or 0), 2)
            })

        # STEP 4 Aggregate scores per movie, this uses AVERAGE
        movie_scores = {}
        for movie, mood_score, mood_name in rows:
            if movie.id not in movie_scores:
                movie_scores[movie.id] = {
                    "movie": movie,
                    "mood_scores_list": [],
                    "matching_moods": []
                }
            movie_scores[movie.id]["mood_scores_list"].append(float(mood_score or 0))
            movie_scores[movie.id]["matching_moods"].append(mood_name)

        for movie_id in movie_scores:
            scores = movie_scores[movie_id]["mood_scores_list"]
            movie_scores[movie_id]["total_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0

        # STEP 5 Format matched movies
        matched_movies = []
        for movie_data in movie_scores.values():
            movie = movie_data["movie"]
            total_score = movie_data["total_score"]
            movie_mood_names = [m.mood_name for m in movie.moods]

            matched_movies.append({
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "image_url": movie.image_url,
                "synopsis": movie.synopsis,
                "storyline": movie.storyline,
                "moods": movie_mood_names,
                "mood_scores": movie_all_moods.get(movie.id, []),
                "match_score": total_score,
                "ai_selected": False
            })

        # STEP 6 AI 
        ai_selected_movies = []
        non_selected_movies = []

        if request.personalNotes and matched_movies:
            matched_movies.sort(key=lambda x: x["match_score"], reverse=True)

            top_movies_for_ai = [m for m in matched_movies if m["match_score"] >= 0.7]

            # Fallback to top 5 if No movies are >= 0.7 to make sure AI gets something just in case
            if not top_movies_for_ai:
                top_movies_for_ai = matched_movies[:5]

            if top_movies_for_ai:
                ai_input_data = [
                    {
                        "id": m["id"],
                        "title": m["title"],
                        "year": m["year"],
                    }
                    for m in top_movies_for_ai
                ]

                prompt = f"""
                User Note: "{request.personalNotes}"
                User Preference: {request.preference}

                TASK:
                Find and analyze which movies' storylines BEST FIT the user's personal situation described in their note.
                If preference is 'congruence', prioritize movies that match their current emotional state.
                If preference is 'repair', prioritize movies that could help shift their mood positively.
                Select only the movies that are truly relevant and helpful.

                Movies to evaluate:
                {ai_input_data}

                Return ONLY a comma-separated list of the movie titles that best fit, first entry should be the best fit, second, etc.
                If none are relevant, return "NONE".
                """
                try:
                    response = await client.aio.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=prompt
                    )

                    selected_titles = []
                    if response and response.text and response.text.strip().upper() != "NONE":
                        selected_titles = [t.strip().lower() for t in response.text.strip().split(',')]

                    for movie in matched_movies:
                        if movie["title"].lower() in selected_titles:
                            movie["ai_selected"] = True
                            movie["original_score"] = movie["match_score"]
                            movie["match_score"] = "AI Suggested"
                            ai_selected_movies.append(movie)
                        else:
                            non_selected_movies.append(movie)

                except Exception as ai_err:
                    print(f"AI Error: {ai_err}")
                    non_selected_movies = matched_movies.copy()
            else:
                non_selected_movies = matched_movies.copy()
        else:
            non_selected_movies = matched_movies.copy()

        # STEP 7 Sort non-selected tier by score
        non_selected_movies.sort(key=lambda x: x["match_score"], reverse=True)

        # STEP 8 Combine final sequence
        final_movies = ai_selected_movies + non_selected_movies

        return {
            "preference": request.preference,
            "target_moods": target_mood_strings,
            "ai_selected_count": len(ai_selected_movies),
            "movies": final_movies
        }

    except Exception as e:
        print("--- CRITICAL BACKEND ERROR ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))