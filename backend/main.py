from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import AsyncSessionLocal
from models import init_db  # Table creation helper, called from main.py on startup
from routes.initialize_moods import initialize_moods
from routes.add_movie_to_database import router as add_movie_router
from routes.search_movie_in_database import router as search_movies_router
from routes.generate_movie_recommendation import router as recommend_movies_router

# Runs before the app starts accepting requests 
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as session:
        await initialize_moods(session)
    print("-----> Database initialized!")
    yield  


# Initialize FastAPI app
app = FastAPI(title="Movie Feels API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes 
app.include_router(add_movie_router)
app.include_router(search_movies_router)
app.include_router(recommend_movies_router)




# To run the app, use `uvicorn main:app --reload`