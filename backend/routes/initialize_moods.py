from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Mood

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