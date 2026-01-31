from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import Movie

router = APIRouter()


@router.get("/api/movies/search")
async def search_movies_by_title(title: str, db: AsyncSession = Depends(get_db)):
    try:
        # Execute query with eager loading for moods only
        result = await db.execute(
            select(Movie)
            .where(Movie.title.ilike(f"%{title}%"))
            .options(selectinload(Movie.moods))
            .order_by(Movie.created_at.desc())
        )
        movies = result.scalars().all()

        # Format the response
        return [
            {
                "id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "synopsis": movie.synopsis,
                "storyline": movie.storyline,
                "image_url": movie.image_url,
                "created_at": movie.created_at,
                "moods": [m.mood_name for m in movie.moods],
            }
            for movie in movies
        ]

    except Exception as e:
        print(f"Search Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search movies by title: {str(e)}",
        )