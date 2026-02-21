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

@router.post("/movierecommendation/congruence")
async def get_congruence_ai_recommendations(
    request: MovieRecommendationRequest, 
    db: AsyncSession = Depends(get_db)
):

    try:
        # Matching current state
        target_mood_strings = request.moods
        
        if not target_mood_strings:
            raise HTTPException(status_code=400, detail="Please provide at least one mood.")

        # Fetch movies from DB
        queryMMM = (
            select(Movie, MovieMood.score, Mood.mood_name)
            .join(MovieMood, Movie.id == MovieMood.movie_id)
            .join(Mood, MovieMood.mood_id == Mood.id)
            .where(Mood.mood_name.in_(target_mood_strings))
            .options(selectinload(Movie.moods))
        )
        
        result = await db.execute(queryMMM)
        rows = result.all()

        # Aggregate
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
            avg_match_score = round(sum(data["mood_scores_list"]) / len(data["mood_scores_list"]), 2)

            matched_movies.append({
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "image_url": movie.image_url,
                "synopsis": movie.synopsis,
                "keyword": movie.keyword,
                "moods": [m.mood_name for m in movie.moods],
                "match_score": avg_match_score,
                "ai_selected": False
            })

        # AI Selection (Groq Mirroring)
        ai_selected_movies = []
        non_selected_movies = []

        if request.personalNotes and matched_movies:
            # We send ALL matched movies and their keywords
            movie_data_for_ai = [
                {"title": m["title"], "keywords": m["keyword"]} 
                for m in matched_movies
            ]

            prompt = f"""
            CONTEXT:
            - User's Current State: {target_mood_strings}
            - User's Personal Note: "{request.personalNotes}"
            - Psychological Goal: "Congruence" (Mirror and validate their current state)

            TASK:
            Act as a cinematic therapist. Review the provided list of {len(matched_movies)} movies. 
            Identify ALL films that 'mirror' the user's current emotional world. 
            Do NOT try to change their mood or cheer them up. Find stories that say "I hear you."

            SELECTION CRITERIA:
            1. Emotional Mirroring: Keywords must align with the specific situation in their note.
            2. Validation: The movie should offer a sense of shared experience or understanding.

            AVAILABLE MOVIES:
            {movie_data_for_ai}

            JSON OUTPUT FORMAT:
            {{
              "recommendations": [
                {{
                  "title": "Exact Movie Title",
                  "reason": "One short empathetic sentence explaining how this movie's themes validate the user's current experience."
                }}
              ]
            }}
            """

            try:
                chat_completion = await client.chat.completions.create(
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are a specialized cinematic consultant focusing on emotional validation. Output strictly in JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.4,
                    response_format={"type": "json_object"}
                )
                
                raw_response = chat_completion.choices[0].message.content
                parsed_json = json.loads(raw_response)
                
                ai_recommendations = parsed_json.get("recommendations", parsed_json.get("movies", []))
                reason_map = {item["title"].lower().strip(): item["reason"] for item in ai_recommendations}

                for m in matched_movies:
                    m_title_cleaned = m["title"].lower().strip()
                    if m_title_cleaned in reason_map:
                        m["ai_selected"] = True
                        m["match_score"] = f"AI Recommended: {reason_map[m_title_cleaned]}"
                        ai_selected_movies.append(m)
                    else:
                        non_selected_movies.append(m)
            
            except Exception as ai_err:
                print(f"GROQ ERROR (Congruence): {ai_err}")
                non_selected_movies = matched_movies
        else:
            non_selected_movies = matched_movies

        # Final sequence
        return {
            "preference": "congruence",
            "target_moods": target_mood_strings,
            "movies": ai_selected_movies + sorted(
                non_selected_movies, 
                key=lambda x: x["match_score"] if isinstance(x["match_score"], (int, float)) else 0, 
                reverse=True
            )
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")