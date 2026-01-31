from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database import Base, engine # Source of base and engine


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


# Table creation helper, called from main.py on startup
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)