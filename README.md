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

### Movie Search
Allows users to check if a movie exists in the local database.

### Adding Movie
From Version 1’s manual input to Version 3’s automated data input sourced from the OMDb external API, users only need to provide the title (and date if needed for more accuracy). The system automatically generates a more detailed movie storyline using Generative AI.  
I designed it this way because I don’t want random movies in the database—I want users to feel like they’re contributing by adding movies they think others will enjoy.

### Personal Design of the Recommendation Algorithm
The hardest part of the project. One of the guiding ideas of this project is to provide movie suggestions that meet you where you are. I’m continuously refining the algorithm and learning along the way to improve its recommendations.

---

## 🛠️ Tech Stack
- **Frontend:** React  
- **Backend:** FastAPI  
- **Database:** PostgreSQL  

---

## Background

### Version 1
Movie Feels began when I noticed that although my younger sister and I both love watching movies, besides a small difference in genre taste, we watch movies for different reasons.  
- She watches movies to help her express how she feels—for example, when she’s sad, she watches a movie to help her cry.  
- When I’m sad, I watch a movie to regain motivation or feel happy, experiencing emotions opposite to my own.  

This version used simple emotions for recommendations, which worked okay when users felt basic emotions, but human emotions are complex. It didn’t fully satisfy me when recommending movies for complex emotions.

### Version 2
Improved UI because Version 1’s UI was very minimal. I’m happy with the expanding and contracting circle design on the homepage.  
- It adds a calming touch—it somewhat imitates our lungs gently inhaling and exhaling, reminding users to breathe.

### Version 3
- Redesigned the database to better store data for improving movie recommendations and narrowed down the set of emotions used  
- Loaded the database with 100 handpicked movies  
- System computes an average from the database search results for recommendations, applies a threshold of 0.7 (movies with higher averages are listed), and then sends them to Generative AI, which uses the user input to relate to the storylines of the movies  

#### Current Challenges
- Too reliant on Generative AI for the final verdict, and using a free API, which isn’t sustainable  
- As the database grows, the system may face increased challenges in processing larger amounts of data efficiently  
- Current algorithm sends too much data to Generative AI, quickly exhausting its allocated resources  

When I’m satisfied, I want to deploy this project, so it can’t rely too heavily on the free Gen AI API.

---

## Next Steps
Currently, I’m exploring:
- Light machine learning  
- Revising the database again and using keywords  
- Experimenting with ways to better narrow down movies for recommendation and creating a high-quality list
