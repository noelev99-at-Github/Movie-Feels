# Movie Feels - Version 3

> "Movies let us explore emotions we can’t always express, confront ideas we might avoid, and experience worlds beyond our own. They remind us of our shared humanity, offer comfort in solitude, and sometimes, in the quiet of a story, help us make sense of our own lives."

Movie Feels is a web application born from this philosophy. Inspired by the love of movies that my younger sister and I share, I realized that traditional recommendations often miss the mark because they ignore how we feel.

To bridge this gap, I architected a platform that prioritizes emotional resonance over simple genre tags. By researching and designing a custom database and developing a recommendation system enhanced with Generative AI, I’ve created a system that analyzes user sentiment and focuses on movie stories to provide suggestions that **meet you where you are.**

---

## Features

![Movie Feels Screenshot](/frontend/src/assets/apppreview.png)

### The Movie Recommendation Form
A form I designed to collect relevant data from users:
- Selecting the set of moods they are currently feeling
- Mood congruence or incongruence
- Optional text box, *“How’s life?”*, where users can freely describe how they feel

### Own Design of the Recommendation Algorithm
The hardest part of the project. One of the guiding ideas of this project is to provide movie suggestions that meet you where you are. I’m continuously refining the algorithm and learning along the way to improve its recommendations.

### Adding Movie
From Version 1’s manual input to Version 3’s automated data input sourced from the OMDb external API, users only need to provide the title (and date if needed for more accuracy). 
The system automatically generates the movie keywords using Generative AI.  
I designed it this way because I don’t want random movies in the database—I want users to feel like they’re contributing by adding movies they think others will enjoy.

### Movie Search
Allows users to check if a movie exists in the local database.

---

## 🛠️ Tech Stack
- **Frontend:** React  
- **Backend:** FastAPI  
- **Database:** PostgreSQL  

---

## Next Steps
Currently, I’m exploring:
- Light machine learning  
- Revising the database again and using keywords  
- Experimenting with ways to better narrow down movies for recommendation and creating a high-quality list
