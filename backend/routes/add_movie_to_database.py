from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models import Movie, Mood, MovieMood
from schemas import MovieCreate

router = APIRouter()


@router.post("/api/movies")
async def create_movie(movie: MovieCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Create the Movie instance
        new_movie = Movie(
            title=movie.title,
            year=movie.year,
            image_url=movie.image_url,
            synopsis=movie.synopsis,
            keyword=movie.keyword,
        )

        db.add(new_movie)
        await db.flush()  # generates new_movie.id

        # Process moods
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
                score=float(score),
            )
            db.add(association)

        # Commit everything
        await db.commit()

        # Return response
        return {
            "status": "success",
            "id": new_movie.id,
            "title": new_movie.title,
            "synopsis": new_movie.synopsis,
            "keyword": new_movie.keyword,
            "moods_recorded": len(movie.moods),
        }

    except Exception as e:
        await db.rollback()
        print(f"Backend Error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")