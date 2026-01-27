import { useNavigate } from 'react-router-dom';
import './App.css';

function App() {
  const navigate = useNavigate();

  return (
    <div className="app">
      <div className="hero-container">
        <div className="glass-bubble">
          <div className="bubble-content">
            <h1 className="title">Movie Feels</h1>
            <p className="subtitle">
              Harnessing AI and movie storylines to give you movie recommendations that will meet you where you are.
            </p>
            <p className="subtitle2">
              "Movies let us explore emotions we can’t always express, confront ideas we might avoid, and experience worlds beyond our own. They remind us of our shared humanity, offer comfort in solitude, and sometimes, in the quiet of a story, help us make sense of our own lives."
            </p>

            <div className="btn-group">
              {/* Navigate to movie search page */}
              <button
                className="btn-outline"
                onClick={() => navigate('/moviereview')}
              >
                Movie Search & Review
              </button>

              {/* Navigate to full movie recommendation page */}
              <button
                className="btn-primary1"
                onClick={() => navigate('/movierecommendation')}
              >
                Movie Recommendations
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Footer, untouched */}
      <footer className="footer"></footer>
    </div>
  );
}

export default App;
