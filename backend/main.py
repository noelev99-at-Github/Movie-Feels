import os
import shutil
import uuid
import json
import os
from google import genai
from google.genai import types
from datetime import datetime
from typing import List, Optional

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
app = FastAPI(title="Movie Review API")

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
    image_url = Column(Text)
    title = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)
    synopsis = Column(Text, nullable=False)
    storyline = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    moods = relationship("Mood", secondary="movie_moods", back_populates="movies")
    reviews = relationship("Review", back_populates="movie", cascade="all, delete")

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

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"))
    review = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    movie = relationship("Movie", back_populates="reviews")

# Pydantic models for request validation
class ReviewCreate(BaseModel):
    review: str

class MovieRecommendationRequest(BaseModel):
    moods: List[str]
    preference: str
    personalNotes: Optional[str] = ""
    timestamp: Optional[str] = None

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
      'Reflective· Introspective · Contemplative About Life',
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
    return {"status": "healthy", "message": "Movie Review API is running"}

@app.get("/api/moods")
async def get_moods(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Mood).order_by(Mood.mood_name))
        moods = result.scalars().all()
        return [{"id": mood.id, "name": mood.mood_name} for mood in moods]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch moods: {str(e)}")

@app.post("/api/movies")
async def create_movie(
    title: str = Form(...),
    year: str = Form(...),
    synopsis: str = Form(...),   # NEW: Auto-filled plot from OMDb
    storyline: str = Form(...),  # NEW: Your manual storyline input
    review: str = Form(...),     # Your personal review
    moods: str = Form(...),      # JSON string of weighted moods
    image_url: str = Form(...),  # OMDb Poster URL
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. Create the Movie instance using your specific DB columns
        new_movie = Movie(
            title=title,
            year=int(year) if year.isdigit() else 0,
            synopsis=synopsis,   # Maps to your DB 'synopsis' column
            storyline=storyline, # Maps to your DB 'storyline' column
            image_url=image_url
        )

        db.add(new_movie)
        await db.flush()  # This generates the new_movie.id for relationships

        # 2. Process Moods (Object with Intensity Scores)
        mood_data = json.loads(moods) 
        
        for mood_name, score in mood_data.items():
            # Find the mood in the master 'moods' table
            result = await db.execute(select(Mood).where(Mood.mood_name == mood_name))
            mood_obj = result.scalar_one_or_none()
            
            # If this mood doesn't exist in the master list yet, create it
            if not mood_obj:
                mood_obj = Mood(mood_name=mood_name)
                db.add(mood_obj)
                await db.flush()

            # 3. Save the score in the association table (MovieMood)
            association = MovieMood(
                movie_id=new_movie.id,
                mood_id=mood_obj.id,
                score=float(score)
            )
            db.add(association)

        # 4. Save the Review to the reviews table
        new_review = Review(
            movie_id=new_movie.id, 
            review=review
        )
        db.add(new_review)

        # Commit everything to the database
        await db.commit()

        # 5. Return a clean response to the frontend
        return {
            "status": "success",
            "id": new_movie.id,
            "title": new_movie.title,
            "synopsis": new_movie.synopsis,
            "storyline": new_movie.storyline,
            "moods_recorded": len(mood_data)
        }

    except Exception as e:
        await db.rollback()
        print(f"Backend Error: {e}") 
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@app.get("/api/movies/search")
async def search_movies_by_title(title: str, db: AsyncSession = Depends(get_db)):
    try:
        # 1. Execute query with eager loading for relationships
        # We use selectinload for moods and reviews to avoid "LazyLoad" errors
        result = await db.execute(
            select(Movie)
            .where(Movie.title.ilike(f"%{title}%"))
            .options(
                selectinload(Movie.moods), 
                selectinload(Movie.reviews)
            )
            .order_by(Movie.created_at.desc())
        )
        movies = result.scalars().all()

        # 2. Format the response to match your new database structure
        return [
            {
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "synopsis": movie.synopsis,   # Auto-filled data from API
                "storyline": movie.storyline, # Your manual input
                "image_url": movie.image_url,
                "created_at": movie.created_at,
                "reviews": [
                    {
                        "review": r.review, 
                        "created_at": r.created_at
                    } for r in movie.reviews
                ],
                # This logic fetches the mood name from the related Mood table
                "moods": [m.mood_name for m in movie.moods]
            }
            for movie in movies
        ]

    except Exception as e:
        print(f"Search Error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to search movies by title: {str(e)}"
        )

# New endpoint for posting a review to a movie
@app.post("/api/movies/{movie_id}/reviews")
async def post_review(
    movie_id: int, 
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if movie exists
        result = await db.execute(select(Movie).where(Movie.id == movie_id))
        movie = result.scalar_one_or_none()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Create new review
        new_review = Review(
            movie_id=movie_id,
            review=review_data.review
        )
        
        db.add(new_review)
        await db.commit()
        await db.refresh(new_review)
        
        # Return the created review
        return {
            "id": new_review.id,
            "movie_id": new_review.movie_id,
            "review": new_review.review,
            "created_at": new_review.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to post review: {str(e)}")
    
# Initialize the client (Reads API key from environment variable GEMINI_API_KEY)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Define the route to receive the POST request for movie recommendations
@app.post("/movierecommendationuserinput")
async def receive_user_input(request: MovieRecommendationRequest, db: AsyncSession = Depends(get_db)):
    # EXACT string definitions from your frontend list
    m1 = 'Love · Romance · Family · Community · Belonging · Home'
    m2 = 'Happy · Playful · Bright · Feel-good · Carefree'
    m3 = 'Hopeful · Healing · Optimistic · Reassuring'
    m4 = 'Excited · Adventurous · Fun · Escapist'
    m5 = 'Reflective· Introspective · Contemplative About Life'
    m6 = 'Calm · Peaceful · Relaxed · Soft · Gentle'
    m7 = 'Curious · Engaged · Intrigued · Mentally Active'
    m8 = 'Intense · Emotional · Cathartic · Bittersweet'
    m9 = 'Lonely · Isolated · Unseen · Longing'
    m10 = 'Angry · Frustrated · Irritated · Stressed'
    m11 = 'Hopeless · Sad · Heartbroken · Melancholy'
    m12 = 'Scared · Anxious · Uneasy · Tense · Nervous'

    # Mood Repair Map: Logic to shift from negative to positive states
    mood_repair_map = {
        m8:  [m2, m3, m6],  # Intense -> Happy/Hopeful/Calm
        m9:  [m1, m3, m4],  # Lonely -> Belonging/Hopeful/Adventure
        m10: [m6, m2, m5],  # Angry -> Calm/Happy/Reflective
        m11: [m3, m2, m1],  # Hopeless -> Hopeful/Happy/Love
        m12: [m6, m3, m2],  # Scared -> Calm/Hopeful/Bright
    }

    try:
        # STEP 1: Fetch movies with Relationships
        # .unique() is required when using selectinload in AsyncSession
        stmt = select(Movie).options(
            selectinload(Movie.moods), 
            selectinload(Movie.reviews)
        )
        result = await db.execute(stmt)
        movies = result.unique().scalars().all()

        # STEP 2: Logic for Congruence vs Incongruence
        target_mood_strings = []
        if request.preference == 'congruence':
            target_mood_strings = request.moods
        else:
            for user_mood in request.moods:
                # Get the repair list or fallback to the current mood if not in map
                repair_targets = mood_repair_map.get(user_mood, [user_mood])
                target_mood_strings.extend(repair_targets)
            target_mood_strings = list(set(target_mood_strings))

        # STEP 3: Initial Matching
        matched_movies = []
        for movie in movies:
            movie_mood_names = [m.mood_name for m in movie.moods]
            matches = set(movie_mood_names) & set(target_mood_strings)
            score = len(matches)

            if score > 0:
                # DATABASE FIX: Accessing .review instead of .review_content
                review_text = movie.reviews[0].review if movie.reviews else ""
                
                matched_movies.append({
                    "id": movie.id,
                    "title": movie.title,
                    "year": movie.year,
                    "image_url": movie.image_url,
                    "synopsis": movie.synopsis,
                    "storyline": movie.storyline,
                    "review": review_text,
                    "moods": movie_mood_names,
                    "match_score": float(score),
                    "ai_boosted": False
                })

        # STEP 4: AI Reranking with Gemini 2.5 Flash
        if request.personalNotes and len(matched_movies) > 0:
            # Send top 10 potential candidates to AI to save tokens/speed
            ai_candidates = matched_movies[:10]
            
            ai_input_data = [
                {
                    "title": m["title"], 
                    "storyline": m["storyline"], 
                    "review": m["review"]
                } for m in ai_candidates
            ]

            prompt = f"""
            User Note: "{request.personalNotes}"
            User Preference: {request.preference} (Congruence: Match mood, Incongruence: Shift mood).
            Target Mood Context: {", ".join(target_mood_strings)}

            Rank these movies from best to worst based on the user's note.
            Movies: {ai_input_data}
            
            Return ONLY a comma-separated list of titles.
            """

            try:
                response = await client.aio.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                
                if response and response.text:
                    ranked_titles = [t.strip().lower() for t in response.text.split(',')]
                    total = len(ranked_titles)
                    
                    for index, title in enumerate(ranked_titles):
                        boost = total - index
                        for m in matched_movies:
                            if m["title"].lower() == title:
                                m["match_score"] += boost
                                m["ai_boosted"] = True
            except Exception as ai_err:
                print(f"AI Error: {ai_err}")

        # STEP 5: Final Sorting
        matched_movies.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "preference": request.preference,
            "target_moods": target_mood_strings,
            "movies": matched_movies
        }

    except Exception as e:
        print("--- CRITICAL BACKEND ERROR ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
# To run the app, use `uvicorn main:app --reload`


