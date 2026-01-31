from typing import List, Dict, Optional
from pydantic import BaseModel

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