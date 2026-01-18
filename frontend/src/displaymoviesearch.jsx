import React, { useState } from 'react';
import './displaymoviesearch.css';

function DisplayMovieSearch({ movie, onClose }) {
  const [reviewTexts, setReviewTexts] = useState({});
  const [postingStatus, setPostingStatus] = useState({});
  const [localReviews, setLocalReviews] = useState({});

  const handleReviewChange = (movieId, text) => {
    setReviewTexts(prev => ({ ...prev, [movieId]: text }));
  };

  const handleSubmitReview = async (movieId) => {
    const reviewText = reviewTexts[movieId]?.trim();
    if (!reviewText) return;

    setPostingStatus(prev => ({ ...prev, [movieId]: 'posting' }));

    try {
      const response = await fetch(`http://localhost:8000/api/movies/${movieId}/reviews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review: reviewText })
      });

      if (!response.ok) throw new Error('Failed to post review');

      const newReview = await response.json();

      setReviewTexts(prev => ({ ...prev, [movieId]: '' }));
      setPostingStatus(prev => ({ ...prev, [movieId]: 'success' }));
      setLocalReviews(prev => ({
        ...prev,
        [movieId]: [...(prev[movieId] || []), newReview]
      }));

      alert('Review posted successfully!');
    } catch (err) {
      console.error(err);
      setPostingStatus(prev => ({ ...prev, [movieId]: 'error' }));
      alert('Failed to post review.');
    }
  };

  if (movie.notFound) {
    return (
      <div className="dms-popup-overlay">
        <div className="dms-popup-content">
          <button className="dms-close-btn" onClick={onClose}>✖</button>
          <h2>Search Results</h2>
          <p>Movie not found in our database.</p>
        </div>
      </div>
    );
  }

  const renderMovieCard = (item) => {
    // UPDATED: image_url is now a direct OMDb link, so we use it as is
    const imageUrl = item.image_url || '/path/to/default/image.jpg';
    const allReviews = [...(item.reviews || []), ...(localReviews[item.id] || [])];

    return (
      <div key={item.id} className="dms-movie-item">
        <div className="dms-movie-card">
          <h3 className="dms-movie-title">{item.title} ({item.year})</h3>
          
          <div className="dms-movie-content">
            <div className="dms-image-container">
              <img src={imageUrl} alt={item.title} className="dms-movie-image" />
            </div>

            <div className="dms-movie-details">
              {/* NEW: Displaying Synopsis and Storyline separately */}
              <div className="dms-detail-box">
                <strong>Synopsis (Official):</strong>
                <p>{item.synopsis}</p>
              </div>

              <div className="dms-detail-box" style={{ marginTop: '10px' }}>
                <strong>Storyline (Contributor Input):</strong>
                <p>{item.storyline}</p>
              </div>

              {/* NEW: Displaying Mood Tags */}
              {item.moods && item.moods.length > 0 && (
                <div className="dms-moods-container" style={{ marginTop: '10px' }}>
                  <strong>Moods:</strong>
                  <div className="dms-mood-tags">
                    {item.moods.map((m, i) => (
                      <span key={i} className="dms-mood-tag" style={{
                        display: 'inline-block',
                        background: '#e0e7ff',
                        color: '#4338ca',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '0.75rem',
                        marginRight: '5px',
                        marginTop: '5px'
                      }}>
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="dms-review-section">
            <h4>Reviews:</h4>
            {allReviews.length > 0 ? (
              <div className="dms-reviews-box">
                {allReviews.map((review, index) => (
                  <div key={index} className="dms-review-item">
                    <p className="dms-review-text">{review.review}</p>
                    <p className="dms-review-date">
                      <em>Posted on: {new Date(review.created_at).toLocaleDateString()}</em>
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p>No reviews yet.</p>
            )}

            <div className="dms-add-review-form">
              <textarea
                placeholder="Write your review here..."
                value={reviewTexts[item.id] || ''}
                onChange={(e) => handleReviewChange(item.id, e.target.value)}
                className="dms-review-textarea"
              />
              <button
                onClick={() => handleSubmitReview(item.id)}
                className="dms-post-review-btn"
              >
                {postingStatus[item.id] === 'posting' ? 'Posting...' : 'Post Review'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="dms-popup-overlay">
      <div className="dms-popup-content">
        <button className="dms-close-btn" onClick={onClose}>✖</button>
        {Array.isArray(movie) ? (
          <>
            <h2>Search Results</h2>
            {movie.length === 0 ? (
              <p>No movies found matching your search.</p>
            ) : (
              <div className="dms-movie-results">
                {movie.map(renderMovieCard)}
              </div>
            )}
          </>
        ) : renderMovieCard(movie)}
      </div>
    </div>
  );
}

export default DisplayMovieSearch;