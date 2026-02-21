import os
import json
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# Import Groq
from groq import AsyncGroq

from database import get_db
from models import Movie, Mood, MovieMood
from schemas import MovieRecommendationRequest

# Initialize Groq Client
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

router = APIRouter()

@router.post("/movierecommendation/incongruence")
async def get_incongruence_recommendations(
    request: MovieRecommendationRequest, 
    db: AsyncSession = Depends(get_db)
):
    # --- MOOD CATEGORY DEFINITIONS ---
    m1 = 'Love · Romance · Family · Community · Belonging · Home'
    m2 = 'Happy · Playful · Bright · Feel-good · Carefree'
    m3 = 'Hopeful · Healing · Optimistic · Reassuring'
    m4 = 'Excited · Adventurous · Fun · Escapist'
    m5 = 'Reflective · Introspective · Contemplative About Life'
    m6 = 'Calm · Peaceful · Relaxed · Soft · Gentle'
    
    # Negative states that require incongruence (Repair)
    m8 = 'Intense · Emotional · Cathartic · Bittersweet'
    m9 = 'Lonely · Isolated · Unseen · Longing'
    m10 = 'Angry · Frustrated · Irritated · Stressed'
    m11 = 'Hopeless · Sad · Heartbroken · Melancholy'
    m12 = 'Scared · Anxious · Uneasy · Tense · Nervous'

    # The Incongruence Map (Mood Repair)
    mood_repair_map = {
        m8:  [m2, m3, m6],
        m9:  [m1, m3, m4],
        m10: [m6, m2, m5],
        m11: [m3, m2, m1],
        m12: [m6, m3, m2],
    }

    try:
        # Determine target moods
        target_mood_strings = []
        for user_mood in request.moods:
            repair_targets = mood_repair_map.get(user_mood, [user_mood])
            target_mood_strings.extend(repair_targets)
        
        target_mood_strings = list(set(target_mood_strings))

        # Fetch movies matching the REPAIR moods from Database
        stmt = (
            select(Movie, MovieMood.score, Mood.mood_name)
            .join(MovieMood, Movie.id == MovieMood.movie_id)
            .join(Mood, MovieMood.mood_id == Mood.id)
            .where(Mood.mood_name.in_(target_mood_strings))
            .options(selectinload(Movie.moods))
        )
        result = await db.execute(stmt)
        rows = result.all()

        # Aggregate scores
        movie_scores = {}
        for movie, mood_score, mood_name in rows:
            if movie.id not in movie_scores:
                movie_scores[movie.id] = {
                    "movie": movie,
                    "mood_scores_list": [],
                }
            movie_scores[movie.id]["mood_scores_list"].append(float(mood_score or 0))

        matched_movies = []
        for movie_id, data in movie_scores.items():
            movie = data["movie"]
            avg_score = sum(data["mood_scores_list"]) / len(data["mood_scores_list"])
            
            matched_movies.append({
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "image_url": movie.image_url,
                "synopsis": movie.synopsis,
                "keyword": movie.keyword,
                "moods": [m.mood_name for m in movie.moods],
                "match_score": round(avg_score, 2),
                "ai_selected": False,
                "ai_reason": None  # Placeholder for the reason
            })

        # AI Selection (Groq Implementation)
        ai_selected_movies = []
        non_selected_movies = []

        if request.personalNotes and matched_movies:
            # We send all titles + keywords to the AI for analysis
            movie_data_for_ai = [
                {"title": m["title"], "keywords": m["keyword"]} 
                for m in matched_movies
            ]

            prompt = f"""
            CONTEXT:
            - User's Current State: {request.moods}
            - User's Personal Note: "{request.personalNotes}"
            - Psychological Goal: "Mood Incongruence Repair" (Shift user to {target_mood_strings})

            TASK:
            Act as an expert cinematic therapist. Review the provided list of {len(matched_movies)} movies. 
            Identify ALL films from this list that serve as an effective emotional 'antidote' or helpful 
            distraction for the user's specific situation. Do not limit yourself to a specific number or the keywords provided; 
            Also do a reseach on what the movie is about, and if a movie is a high-quality match, select it.

            SELECTION CRITERIA:
            1. Resonance: The movie's keywords must bridge the gap between their current note and the target mood.
            2. Therapeutic Value: The story must provide a genuine perspective shift or emotional relief.

            AVAILABLE MOVIES:
            {movie_data_for_ai}

            JSON OUTPUT FORMAT:
            {{
              "recommendations": [
                {{
                  "title": "Exact Movie Title",
                  "reason": "A personalized, one-sentence therapeutic explanation connecting the movie's themes to the user's situation. Structure this reply like you are talking to a friend"
                }}
              ]
            }}
            """

            try:
                # Call Groq API with JSON mode
                chat_completion = await client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that only outputs valid JSON lists."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.3, # Low temp for consistency
                    response_format={"type": "json_object"}
                )
                
                raw_response = chat_completion.choices[0].message.content
                print(f"DEBUG: Groq raw output: {raw_response}")

                # Groq sometimes wraps the list in a key like {"movies": [...]}
                parsed_json = json.loads(raw_response)
                if isinstance(parsed_json, dict) and "movies" in parsed_json:
                    ai_recommendations = parsed_json["movies"]
                elif isinstance(parsed_json, list):
                    ai_recommendations = parsed_json
                else:
                    # If it returned a dict but not the list, look for any list inside
                    ai_recommendations = next((v for v in parsed_json.values() if isinstance(v, list)), [])

                # Create a lookup for reasons
                reason_map = {item["title"].lower(): item["reason"] for item in ai_recommendations}

                for m in matched_movies:
                    m_title_lower = m["title"].lower()
                    if m_title_lower in reason_map:
                        m["ai_selected"] = True
                        # This displays the "Why" in your UI
                        m["match_score"] = f"AI Recommended: {reason_map[m_title_lower]}"
                        ai_selected_movies.append(m)
                    else:
                        non_selected_movies.append(m)
            
            except Exception as ai_err:
                print(f"AI ERROR (Groq): {ai_err}")
                non_selected_movies = matched_movies
        else:
            non_selected_movies = matched_movies

        # Final Return: AI picks first, then standard DB picks
        return {
            "mode": "incongruence_repair",
            "target_moods": target_mood_strings,
            "movies": ai_selected_movies + sorted(
                non_selected_movies, 
                key=lambda x: x["match_score"] if isinstance(x["match_score"], (int, float)) else 0, 
                reverse=True
            )
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))