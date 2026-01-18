import React, { useState } from 'react';
import axios from 'axios';
import './addmovie.css';
import { GoogleGenerativeAI } from '@google/generative-ai';

function AddMovieReview({ showModal, onClose }) {
  // 2. Initialize Gemini AI
  const genAI = new GoogleGenerativeAI('AIzaSyDOkrHMXKmLmo8qgsBb-CnCnDfG6BU5QEQ'); 
  const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

  // ---------------- State ----------------
  const [formData, setFormData] = useState({
    image: null,
    displayPoster: '',
    title: '',
    year: '',
    synopsis: '',  // Plot from OMDb
    storyline: '', // NOW AUTO-FILLED by Gemini
    mood: {},
    review: '',
  });

  const [searchStatus, setSearchStatus] = useState('idle');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const moods = [
    'Love · Romance · Family · Community · Belonging · Home',
    'Happy · Playful · Bright · Feel-good · Carefree',
    'Hopeful · Healing · Optimistic · Reassuring',
    'Excited · Adventurous · Fun · Escapist',
    'Reflective· Introspective · Contemplative About Life',
    'Calm · Peaceful · Relaxed · Soft · Gentle',
    'Curious · Engaged · Intrigued · Mentally Active',
    'Intense · Emotional · Cathartic · Bittersweet',
    'Lonely · Isolated · Unseen · Longing',
    'Angry · Frustrated · Irritated · Stressed',
    'Hopeless · Sad · Heartbroken · Melancholy',
    'Scared · Anxious · Uneasy · Tense · Nervous'
  ];

  // ---------------- Handlers ----------------
  const handleSearchMovie = async () => {
    if (!formData.title) return setError("Please enter a movie title first");
    setSearchStatus('loading');
    setError('');

    try {
      // Step A: Fetch data from OMDb
      const res = await axios.get("https://www.omdbapi.com/", {
        params: { apikey: "2c6bd367", t: formData.title, y: formData.year, plot: "full" }
      });
      if (res.data.Response === "False") throw new Error(res.data.Error || "Movie not found");

      const fetchedTitle = res.data.Title;
      const fetchedYear = res.data.Year;
      const fetchedPlot = res.data.Plot;

      // Step B: Call Gemini AI to generate a custom storyline summary
      let aiStoryline = '';
      try {
        // Sending title and year data along with the specific prompt requested
        const prompt = `Generate 1 paragraph summarize storyline for this movie: ${fetchedTitle} (${fetchedYear})`;
        const result = await model.generateContent(prompt);
        const response = await result.response;
        aiStoryline = response.text(); 
      } catch (aiErr) {
        console.error("Gemini failed:", aiErr);
        aiStoryline = "AI summary unavailable. Please fill manually.";
      }

      // Step C: Update state - Storyline is now autofilled with Gemini data
      setFormData(prev => ({
        ...prev,
        title: fetchedTitle,
        year: fetchedYear,
        synopsis: fetchedPlot, 
        storyline: aiStoryline, // Autofilled from Gemini response
        displayPoster: res.data.Poster !== "N/A" ? res.data.Poster : ''
      }));
      setSearchStatus('found');
    } catch (err) {
      setError(err.message);
      setSearchStatus('idle');
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleMoodChange = (mood, value) => {
    const numericValue = value === '' ? '' : Math.min(1, Math.max(0, parseFloat(value) || 0));
    setFormData(prev => ({
      ...prev,
      mood: { ...prev.mood, [mood]: numericValue }
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const filteredMoods = Object.fromEntries(
        Object.entries(formData.mood).filter(([_, val]) => val > 0)
      );

      if (Object.keys(filteredMoods).length === 0) {
        throw new Error('Please rate at least one emotion');
      }

      const uploadData = new FormData();
      uploadData.append('image_url', formData.displayPoster); 
      uploadData.append('title', formData.title);
      uploadData.append('year', formData.year);
      uploadData.append('synopsis', formData.synopsis);
      uploadData.append('storyline', formData.storyline); 
      uploadData.append('review', formData.review);
      uploadData.append('moods', JSON.stringify(filteredMoods));

      const response = await fetch('http://localhost:8000/api/movies', {
        method: 'POST',
        body: uploadData,
      });

      if (!response.ok) throw new Error('Failed to submit movie');

      alert('Movie review submitted successfully!');
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!showModal) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-content" style={{ width: '600px', maxWidth: '95%', maxHeight: '90vh', overflowY: 'auto' }}>
        <button className="close-button" onClick={onClose}>×</button>
        <h2>Add Movie Review</h2>

        {searchStatus === 'loading' && (
          <p style={{color: '#1d4ed8', fontWeight: 'bold'}}>
            ✨ Gemini AI is analyzing the movie and writing your summary...
          </p>
        )}

        {error && <div className="error-message" style={{ color: 'red', marginBottom: '10px' }}>{error}</div>}

        <div className="movie-form">
          <div className="search-section" style={{ borderBottom: '1px solid #eee', paddingBottom: '15px' }}>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input style={{ flex: 2 }} type="text" name="title" value={formData.title} onChange={handleChange} placeholder="Movie Title..." />
              <input style={{ flex: 1 }} type="text" name="year" value={formData.year} onChange={handleChange} placeholder="Year" />
            </div>
            <button type="button" onClick={handleSearchMovie} className="submit-button" style={{ background: '#1d4ed8', marginTop: '10px' }}>
              {searchStatus === 'loading' ? 'Processing...' : 'Search & Auto-fill'}
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {formData.displayPoster && (
              <div style={{ textAlign: 'center', margin: '15px 0' }}>
                <img src={formData.displayPoster} alt="Poster" style={{ maxHeight: '150px', borderRadius: '8px' }} />
              </div>
            )}

            <div className="mood-section">
              <h3>Rate the Intensity (0 to 1.0)</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {moods.map(m => (
                  <div key={m} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '5px', background: 'black', color: 'white', borderRadius: '4px' }}>
                    <span style={{ fontSize: '0.85rem', flex: 1 }}>{m}</span>
                    <input
                      type="number" step="0.1" min="0" max="1" placeholder="0.0"
                      value={formData.mood[m] || ''}
                      onChange={(e) => handleMoodChange(m, e.target.value)}
                      style={{ width: '60px', marginLeft: '10px', textAlign: 'center' }}
                    />
                  </div>
                ))}
              </div>
            </div>

            <label style={{ marginTop: '15px', display: 'block' }}>
              Synopsis (Objective Plot from OMDb):
              <textarea 
                name="synopsis" 
                rows="3" 
                value={formData.synopsis} 
                onChange={handleChange} 
                placeholder="The OMDb plot summary will appear here..."
              />
            </label>

            {/* STORYLINE SECTION - AUTO-FILLED BY GEMINI */}
            <label style={{ marginTop: '15px', display: 'block', border: '1px solid #c0d8f0', padding: '10px', borderRadius: '8px', backgroundColor: '#f0f7ff' }}>
              <span style={{color: '#1d4ed8', fontWeight: 'bold'}}>✨ Storyline (AI Summary):</span>
              <textarea 
                name="storyline" 
                rows="4" 
                value={formData.storyline} 
                onChange={handleChange} 
                placeholder="Gemini will summarize the storyline here..."
                required 
                style={{ backgroundColor: 'white' }}
              />
            </label>

            <label style={{ marginTop: '15px', display: 'block' }}>
              Your Personal Review:
              <textarea 
                name="review" 
                rows="4" 
                value={formData.review} 
                onChange={handleChange} 
                placeholder="What did you think about it?"
                required 
              />
            </label>

            <button type="submit" className="submit-button" style={{ marginTop: '20px' }} disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : 'Submit Review'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default AddMovieReview;