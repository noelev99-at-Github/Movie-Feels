import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './movieresults.css';

function MovieResults({ formData }) {
  const navigate = useNavigate();
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    setShowResults(false);
    if (formData) {
      const timer = setTimeout(() => setShowResults(true), 1000);
      return () => clearTimeout(timer);
    }
  }, [formData]);

  if (!formData || !showResults) return null;

  const { message, movies } = formData;
  
  // Logic to handle how movies are ranked based on the match_score
  const allAreOnes = movies.every(movie => movie.match_score === 1);
  const filteredMovies = allAreOnes ? movies : movies.filter(movie => movie.match_score !== 1);

  return (
    <div className="standalone-movie-results">
      {/* Home Button */}
      <div className="standalone-home-bar">
        <button className="standalone-home-btn" onClick={() => navigate('/')}>
          ← Home
        </button>
      </div>

      <div className="standalone-results-container">
        {/* Intro Section */}
        <div className="standalone-intro">
          <h2>Movie Recommendation Result</h2>
          <p>{message}. Here are some movies we think you'll enjoy based on your mood.</p>
        </div>

        {/* Movie Cards Grid */}
        {filteredMovies.length > 0 ? (
          <div className="standalone-grid">
            {filteredMovies.map(movie => (
              <div key={movie.id} className="standalone-card">
                <div className="standalone-poster-wrap">
                  {/* UPDATED: Directly using the OMDb image URL */}
                  <img
                    src={movie.image_url}
                    alt={movie.title}
                    onError={(e) => { e.target.src = '/fallback-poster.jpg'; }} // Fallback if link breaks
                  />
                </div>

                <div className="standalone-details">
                  <h3>{movie.title} ({movie.year})</h3>
                  
                  <p className="standalone-score">
                    🎯 Match Score: <strong>{movie.match_score}</strong>
                  </p>

                  {/* NEW: Synopsis vs Storyline split */}
                  <div className="standalone-story-section">
                    {movie.synopsis && (
                      <div className="standalone-synopsis">
                        <strong>The Plot:</strong>
                        <p>{movie.synopsis}</p>
                      </div>
                    )}
                    
                  </div>

                  {/* Moods with Scores Section */}
                  <div className="standalone-moods">
                    {/* If mood_scores exists and has data, sort and show moods with scores */}
                    {movie.mood_scores && movie.mood_scores.length > 0 ? (
                      [...movie.mood_scores]
                        .sort((a, b) => b.score - a.score) // Sorts descending (highest score first)
                        .map((moodScore, idx) => (
                          <span key={idx} className="standalone-mood">
                            {moodScore.mood} 
                            <span className="mood-score-badge">
                              <strong>{" ( "}{moodScore.score}{" ) "}</strong>
                            </span>
                          </span>
                        ))
                    ) : (
                      /* Fallback: If no mood_scores, show regular moods */
                      movie.moods && movie.moods.map((mood, idx) => (
                        <span key={idx} className="standalone-mood">{mood}</span>
                      ))
                    )}
                  </div>

                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="standalone-no-results">No matching movies found for your selection.</p>
        )}
      </div>
    </div>
  );
}

export default MovieResults;