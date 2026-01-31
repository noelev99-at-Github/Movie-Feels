import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# Create the base class for all SQLAlchemy models
# Any model defined will inherit from this Base
Base = declarative_base()

# Create an asynchronous engine that connects to the database
# echo=True prints all SQL statements to the console, useful for debugging
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session factory for async database sessions
# expire_on_commit=False means objects won't be expired after a commit
# class_=AsyncSession tells SQLAlchemy to use asynchronous sessions
AsyncSessionLocal = sessionmaker(
    engine,                # the database engine to bind sessions to
    expire_on_commit=False, # keep objects alive after commit
    class_=AsyncSession     # use async sessions
)

# Dependency function to get a database session in async FastAPI endpoints
# 'async with' ensures the session is properly closed after use
# 'yield' allows this function to be used as a dependency in FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
