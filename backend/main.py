import os
import shutil
import uuid
import json
import os
from google import genai
from google.genai import types
from datetime import datetime
from typing import List, Optional, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# SQLAlchemy Async Imports
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, selectinload
from sqlalchemy.future import select 

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Set up SQLAlchemy with async engine
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Initialize FastAPI app
app = FastAPI(title="Movie Feels API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Models
class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(Text, nullable=False)
    title = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)
    synopsis = Column(Text, nullable=False)
    storyline = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    moods = relationship("Mood", secondary="movie_moods", back_populates="movies")

class Mood(Base):
    __tablename__ = "moods"

    id = Column(Integer, primary_key=True)
    mood_name = Column(String(255), unique=True, nullable=False)

    movies = relationship("Movie", secondary="movie_moods", back_populates="moods")

class MovieMood(Base):
    __tablename__ = "movie_moods"

    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    mood_id = Column(Integer, ForeignKey("moods.id", ondelete="CASCADE"), primary_key=True)
    score = Column(Float)

# Pydantic models for request validation
class MovieRecommendationRequest(BaseModel):
    moods: List[str]
    preference: str
    personalNotes: Optional[str] = ""
    timestamp: Optional[str] = None

class MovieCreate(BaseModel):
    title: str
    image_url: str
    year: int
    synopsis: str
    storyline: str
    moods: Dict[str, float]

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
# Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Initialize predefined moods, responsible for seeding the moods table
async def initialize_moods(db: AsyncSession):
    predefined_moods = [
      'Love · Romance · Family · Community · Belonging · Home',
      'Happy · Playful · Bright · Feel-good · Carefree',
      'Hopeful · Healing · Optimistic · Reassuring',
      'Excited · Adventurous · Fun · Escapist',
      'Reflective · Introspective · Contemplative About Life',
      'Calm · Peaceful · Relaxed · Soft · Gentle',
      'Curious · Engaged · Intrigued · Mentally Active',
      'Intense · Emotional · Cathartic · Bittersweet',
      'Lonely · Isolated · Unseen · Longing',
      'Angry · Frustrated · Irritated · Stressed',
      'Hopeless · Sad · Heartbroken · Melancholy',
      'Scared · Anxious · Uneasy · Tense · Nervous'
    ]

    for mood_name in predefined_moods:
        result = await db.execute(select(Mood).where(Mood.mood_name == mood_name))
        mood = result.scalar_one_or_none()
        if not mood:
            db.add(Mood(mood_name=mood_name))
    await db.commit()

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await initialize_moods(session)
    print("✅ Database initialized!")

@app.get("/")
async def health_check():
    return {"status": "healthy", "message": "Movie Feels API is running"}

@app.get("/api/moods")
async def get_moods(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Mood).order_by(Mood.mood_name))
        moods = result.scalars().all()
        return [{"id": mood.id, "name": mood.mood_name} for mood in moods]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch moods: {str(e)}")

@app.post("/api/movies")
async def create_movie(movie: MovieCreate, db: AsyncSession = Depends(get_db)):
    try:
        # 1️⃣ Create the Movie instance
        new_movie = Movie(
            title=movie.title,
            year=movie.year,
            image_url=movie.image_url,
            synopsis=movie.synopsis,
            storyline=movie.storyline,
        )

        db.add(new_movie)
        await db.flush()  # generates new_movie.id

        # 2️⃣ Process moods
        for mood_name, score in movie.moods.items():
            # Check if mood exists
            result = await db.execute(select(Mood).where(Mood.mood_name == mood_name))
            mood_obj = result.scalar_one_or_none()

            # If not, create it
            if not mood_obj:
                mood_obj = Mood(mood_name=mood_name)
                db.add(mood_obj)
                await db.flush()

            # Create association
            association = MovieMood(
                movie_id=new_movie.id,
                mood_id=mood_obj.id,
                score=float(score)
            )
            db.add(association)

        # 3️⃣ Commit everything
        await db.commit()

        # 4️⃣ Return response
        return {
            "status": "success",
            "id": new_movie.id,
            "title": new_movie.title,
            "synopsis": new_movie.synopsis,
            "storyline": new_movie.storyline,
            "moods_recorded": len(movie.moods)
        }

    except Exception as e:
        await db.rollback()
        print(f"Backend Error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@app.get("/api/movies/search")
async def search_movies_by_title(title: str, db: AsyncSession = Depends(get_db)):
    try:
        # 1️⃣ Execute query with eager loading for moods only
        result = await db.execute(
            select(Movie)
            .where(Movie.title.ilike(f"%{title}%"))
            .options(selectinload(Movie.moods))  # no reviews
            .order_by(Movie.created_at.desc())
        )
        movies = result.scalars().all()

        # 2️⃣ Format the response
        return [
            {
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "synopsis": movie.synopsis,
                "storyline": movie.storyline,
                "image_url": movie.image_url,
                "created_at": movie.created_at,
                "moods": [m.mood_name for m in movie.moods]  # only moods
            }
            for movie in movies
        ]

    except Exception as e:
        print(f"Search Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search movies by title: {str(e)}"
        )

# Initialize the client (Reads API key from environment variable GEMINI_API_KEY)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.post("/movierecommendationuserinput")
async def receive_user_input(request: MovieRecommendationRequest, db: AsyncSession = Depends(get_db)):
    # EXACT string definitions from your frontend list
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
        # STEP 1: Determine target moods based on user preference
        target_mood_strings = []
        if request.preference == 'congruence':
            target_mood_strings = request.moods
        else:
            for user_mood in request.moods:
                repair_targets = mood_repair_map.get(user_mood, [user_mood])
                target_mood_strings.extend(repair_targets)
            target_mood_strings = list(set(target_mood_strings))  # remove duplicates

        # STEP 2: Fetch movies with relevant moods
        stmt = (
            select(Movie, MovieMood.score, Mood.mood_name)
            .join(MovieMood, Movie.id == MovieMood.movie_id)
            .join(Mood, MovieMood.mood_id == Mood.id)
            .where(Mood.mood_name.in_(target_mood_strings))
            .options(selectinload(Movie.moods))  # no reviews
        )
        result = await db.execute(stmt)
        rows = result.all()

        # STEP 3: Get all moods for each movie
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

        # STEP 4: Aggregate scores per movie (FIXED: now uses AVERAGE)
        movie_scores = {}
        for movie, mood_score, mood_name in rows:
            if movie.id not in movie_scores:
                movie_scores[movie.id] = {
                    "movie": movie,
                    "mood_scores_list": [],  # Collect all matching scores
                    "matching_moods": []
                }
            movie_scores[movie.id]["mood_scores_list"].append(float(mood_score or 0))
            movie_scores[movie.id]["matching_moods"].append(mood_name)

        # Calculate average score for each movie
        for movie_id in movie_scores:
            scores = movie_scores[movie_id]["mood_scores_list"]
            movie_scores[movie_id]["total_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0

        # STEP 5: Format matched movies
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

        
        # STEP 6: AI Selection & Tiering
        ai_selected_movies = []
        non_selected_movies = []

        if request.personalNotes and matched_movies:
            # Sort all matched movies by match_score descending first
            matched_movies.sort(key=lambda x: x["match_score"], reverse=True)
            
            # CHANGE: Instead of [:15], we filter for scores >= 0.7
            top_movies_for_ai = [m for m in matched_movies if m["match_score"] >= 0.7]

            # Fallback to top 5 if NO movies are >= 0.7 to ensure AI always has something
            if not top_movies_for_ai:
                top_movies_for_ai = matched_movies[:5]

            if top_movies_for_ai:
                # Prepare AI input - Only send essential data
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
                        model='gemini-2.0-flash', # Note: gemini-2.0-flash is currently standard
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
                # No movies met the 0.7 threshold
                non_selected_movies = matched_movies.copy()
        else:
            non_selected_movies = matched_movies.copy()

        # STEP 7: Sort non-selected tier by score
        non_selected_movies.sort(key=lambda x: x["match_score"], reverse=True)

        # STEP 8: Combine final sequence
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
    
# To run the app, use `uvicorn main:app --reload`


