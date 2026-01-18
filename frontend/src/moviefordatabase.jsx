import axios from "axios";
import React, { useState } from "react";

function MovieSearchModal() {
    const [movieData, setMovieData] = useState({ title: '', year: '' });
    const [apiRes, setApiRes] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isOpen, setIsOpen] = useState(false); // popup toggle

    const handleChange = (e) => {
        const { name, value } = e.target;
        setMovieData(prev => ({ ...prev, [name]: value }));
        setError('');
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!movieData.title) return setError("Please enter a movie title");

        setLoading(true);
        axios.get("https://www.omdbapi.com/", {
            params: {
                apikey: "2c6bd367",
                plot: "full",
                t: movieData.title,
                y: movieData.year
            }
        })
        .then(res => setApiRes(res.data))
        .catch(err => setError("Failed to fetch movie data"))
        .finally(() => setLoading(false));
    };

    return (
        <div>
            {/* Button to open popup */}
            <button 
                onClick={() => setIsOpen(true)} 
                style={{
                    padding: "10px 20px",
                    borderRadius: "5px",
                    border: "none",
                    background: "#1d4ed8",
                    color: "#fff",
                    cursor: "pointer"
                }}
            >
                Search Movie
            </button>

            {/* Modal */}
            {isOpen && (
                <div style={{
                    position: "fixed",
                    top: 0,
                    left: 0,
                    width: "100vw",
                    height: "100vh",
                    backgroundColor: "rgba(0,0,0,0.5)",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    zIndex: 1000
                }}>
                    <div style={{
                        background: "#fff",
                        padding: "20px",
                        borderRadius: "8px",
                        width: "300px",
                        maxWidth: "90%",
                        boxShadow: "0 5px 15px rgba(0,0,0,0.3)",
                        position: "relative"
                    }}>
                        {/* Close button */}
                        <button 
                            onClick={() => setIsOpen(false)} 
                            style={{
                                position: "absolute",
                                top: "10px",
                                right: "10px",
                                border: "none",
                                background: "transparent",
                                fontSize: "18px",
                                cursor: "pointer"
                            }}
                        >
                            ×
                        </button>

                        <form onSubmit={handleSubmit}>
                            <label style={{ display: "block", marginBottom: "8px" }}>
                                Movie Title:
                                <input
                                    type="text"
                                    name="title"
                                    value={movieData.title}
                                    onChange={handleChange}
                                    style={{
                                        width: "100%",
                                        padding: "5px",
                                        marginTop: "4px",
                                        marginBottom: "10px",
                                        boxSizing: "border-box"
                                    }}
                                />
                            </label>

                            <label style={{ display: "block", marginBottom: "10px" }}>
                                Year Released:
                                <input
                                    type="text"
                                    name="year"
                                    value={movieData.year}
                                    onChange={handleChange}
                                    style={{
                                        width: "100%",
                                        padding: "5px",
                                        marginTop: "4px",
                                        boxSizing: "border-box"
                                    }}
                                />
                            </label>

                            <button 
                                type="submit"
                                style={{
                                    padding: "8px 16px",
                                    borderRadius: "5px",
                                    border: "none",
                                    background: "#1d4ed8",
                                    color: "#fff",
                                    cursor: "pointer",
                                    width: "100%"
                                }}
                            >
                                Search
                            </button>
                        </form>

                        {loading && <p style={{ marginTop: "10px" }}>Loading...</p>}
                        {error && <p style={{ marginTop: "10px", color: "red" }}>{error}</p>}
                        {apiRes && apiRes.Plot && (
                            <div style={{ marginTop: "10px", color: "black" }}>
                                <h4>Plot:</h4>
                                <p>{apiRes.Plot}</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default MovieSearchModal;
