import React, { useEffect, useState, useRef, useMemo } from "react";
import { API_URL } from "../config/api";

function ProductReviews({ product, onBack, onNavigateHome, theme, toggleTheme }) {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Review form states
  const [reviewText, setReviewText] = useState("");
  const [rating, setRating] = useState(0);
  const [editingReview, setEditingReview] = useState(null);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");

  // AI analysis states
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState(null);

  const formRef = useRef(null);

  const currentUser = JSON.parse(
    localStorage.getItem("user") || "null"
  );

  const token = localStorage.getItem("token");

  // =========================================================
  // FETCH PRODUCT REVIEWS
  // =========================================================

  const fetchReviews = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/api/products/${product.product_id}/reviews`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch product reviews.");
      }

      const data = await response.json();

      setReviews(
        Array.isArray(data.reviews) ? data.reviews : []
      );
    } catch (err) {
      setError(err.message || "Unable to load reviews.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product.product_id]);

  // =========================================================
  // SUBMIT / UPDATE REVIEW
  // =========================================================

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!rating || !reviewText.trim()) {
      setFormError("Please provide a rating and review text.");
      return;
    }

    if (!token) {
      setFormError("Please log in again to submit a review.");
      return;
    }

    setFormLoading(true);
    setFormError("");

    try {
      const url = editingReview
        ? `${API_URL}/api/reviews/${editingReview.review_id}`
        : `${API_URL}/api/reviews`;

      const method = editingReview ? "PUT" : "POST";

      const body = editingReview
        ? {
            review_text: reviewText.trim(),
            rating,
          }
        : {
            product_id: product.product_id,
            review_text: reviewText.trim(),
            rating,
          };

      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));

        throw new Error(
          errData.error ||
            errData.message ||
            "Failed to save review."
        );
      }

      setReviewText("");
      setRating(0);
      setEditingReview(null);

      // A changed review means the old AI result is stale.
      setAiAnalysis(null);
      setAiError("");

      await fetchReviews();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setFormLoading(false);
    }
  };

  // =========================================================
  // EDIT REVIEW
  // =========================================================

  const handleEditClick = (review) => {
    setEditingReview(review);
    setReviewText(review.review_text);
    setRating(Number(review.rating));
    setFormError("");

    if (formRef.current) {
      formRef.current.scrollIntoView({
        behavior: "smooth",
      });
    }
  };

  // =========================================================
  // CANCEL EDIT
  // =========================================================

  const handleCancelEdit = () => {
    setEditingReview(null);
    setReviewText("");
    setRating(0);
    setFormError("");
  };

  // =========================================================
  // DELETE REVIEW
  // =========================================================

  const handleDeleteClick = async (reviewId) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this review?"
      )
    ) {
      return;
    }

    if (!token) {
      alert("Please log in again to delete a review.");
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/reviews/${reviewId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));

        throw new Error(
          errData.error ||
            errData.message ||
            "Failed to delete review."
        );
      }

      setAiAnalysis(null);
      setAiError("");

      await fetchReviews();
    } catch (err) {
      alert("Error deleting review: " + err.message);
    }
  };

  // =========================================================
  // REAL AI REVIEW ANALYSIS
  // =========================================================

  const handleAnalyzeReviews = async () => {
    setAiError("");
    setAiAnalysis(null);

    if (reviews.length === 0) {
      setAiError(
        "There are no customer reviews to analyze yet."
      );
      return;
    }

    // Combine the reviews for this product up to the worker's 10,000-character limit.
    let combinedReviews = "";
    let analyzedCount = 0;

    for (const review of reviews) {
      const text =
        typeof review.review_text === "string"
          ? review.review_text.trim()
          : "";

      if (!text) continue;

      if (combinedReviews.length + text.length + 1 > 9800) {
        break;
      }

      combinedReviews += (combinedReviews ? "\n" : "") + text;
      analyzedCount++;
    }

    if (!combinedReviews.trim()) {
      setAiError(
        "No valid review text was found for this product."
      );
      return;
    }

    setAiLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/ai/analyze`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            review: combinedReviews,
          }),
        }
      );

      const responseData = await response
        .json()
        .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          responseData.message ||
            responseData.error ||
            "The AI analysis request failed."
        );
      }

      if (responseData.success === false) {
        throw new Error(
          responseData.message ||
            responseData.error ||
            "The AI model could not analyze these reviews."
        );
      }

      // The tested Express API returns:
      // { success: true, message: "...", data: modelResult }
      const result = responseData.data;

      if (
        !result ||
        !Array.isArray(result.aspects)
      ) {
        throw new Error(
          "The AI server returned an unexpected response format."
        );
      }

      setAiAnalysis({
        ...result,
        analyzedReviewCount: analyzedCount,
      });
    } catch (err) {
      setAiError(
        err.message ||
          "Unable to analyze reviews. Please try again."
      );
    } finally {
      setAiLoading(false);
    }
  };

  // =========================================================
  // AVERAGE RATING
  // =========================================================

  const averageRating =
    reviews.length > 0
      ? (
          reviews.reduce(
            (sum, review) =>
              sum + Number(review.rating || 0),
            0
          ) / reviews.length
        ).toFixed(1)
      : "0.0";

  const ratingDistribution = useMemo(() => {
    const counts = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
    reviews.forEach((r) => {
      const star = Math.round(Number(r.rating || 0));
      if (counts[star] !== undefined) {
        counts[star] += 1;
      }
    });
    return counts;
  }, [reviews]);

  // =========================================================
  // FORMAT SENTIMENT
  // =========================================================

  const formatSentiment = (sentiment) => {
    if (!sentiment) return "Unknown";

    return sentiment.charAt(0).toUpperCase() +
      sentiment.slice(1).toLowerCase();
  };

  const getSentimentClass = (sentiment) => {
    const normalized = String(sentiment || "").toLowerCase();

    if (normalized === "positive") return "ai-sentiment-positive";
    if (normalized === "negative") return "ai-sentiment-negative";
    if (normalized === "neutral") return "ai-sentiment-neutral";

    return "ai-sentiment-mixed";
  };

  const formatConfidence = (confidence) => {
    const value = Number(confidence);

    if (!Number.isFinite(value)) {
      return "Unavailable";
    }

    // The API returns confidence as a probability between 0 and 1.
    return `${(Math.max(0, Math.min(1, value)) * 100).toFixed(1)}%`;
  };

  // =========================================================
  // RENDER
  // =========================================================

  return (
    <div className="app">
      {/* HEADER */}
      <header className="header">
        <div>
          <h1>SmartReview AI</h1>
          <p>AI-Powered E-Commerce Review Analysis</p>
        </div>

        <div
          style={{
            display: "flex",
            gap: "12px",
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          {onNavigateHome && (
            <button
              className="header-nav-btn"
              onClick={onNavigateHome}
              title="Go to Home / Overview"
            >
              🏠 Home
            </button>
          )}

          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={
              theme === "dark"
                ? "Switch to Light Mode"
                : "Switch to Dark Mode"
            }
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>

          <button className="refresh-btn" onClick={onBack}>
            ← Back to Products
          </button>
        </div>
      </header>

      <main className="container">
        {/* PRODUCT HEADER */}
        <section className="review-header">
          <div className="review-product-hero">
            {product.image_url && (
              <div className="review-product-image-box">
                <img
                  src={product.image_url}
                  alt={product.product_name}
                  className="review-product-image"
                />
              </div>
            )}

            <div className="review-product-details">
              <h2>{product.product_name}</h2>

              <p className="review-product-meta">
                {product.brand} • {product.category}
                {product.price && (
                  <span className="review-product-price">
                    {" "}
                    • ${Number(product.price).toFixed(2)}
                  </span>
                )}
              </p>

              {product.description && (
                <p className="review-product-desc">{product.description}</p>
              )}
            </div>
          </div>

          <div className="review-stats">
            <div className="stat-card">
              <span>Total Reviews</span>
              <strong>{reviews.length}</strong>
            </div>

            <div className="stat-card">
              <span>Average Rating</span>
              <strong>⭐ {averageRating} / 5</strong>
            </div>

            <div className="rating-breakdown-card">
              {[5, 4, 3, 2, 1].map((star) => {
                const count = ratingDistribution[star] || 0;
                const percentage =
                  reviews.length > 0 ? (count / reviews.length) * 100 : 0;

                return (
                  <div className="rating-bar-row" key={star}>
                    <span className="rating-bar-label">{star} ⭐</span>
                    <div className="rating-bar-track">
                      <div
                        className="rating-bar-fill"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="rating-bar-count">({count})</span>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* REVIEW FORM */}
        <section className="review-form" ref={formRef}>
          <h3>
            {editingReview ? "Edit Review" : "Write a Review"}
          </h3>

          <div className="star-rating">
            {[1, 2, 3, 4, 5].map((star) => (
              <span
                key={star}
                className={star <= rating ? "active" : ""}
                onClick={() => setRating(star)}
                style={{
                  cursor: "pointer",
                  fontSize: "1.5rem",
                }}
              >
                {star <= rating ? "⭐" : "☆"}
              </span>
            ))}
          </div>

          <textarea
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
            placeholder="What did you think about this product?"
            rows="4"
          />

          {formError && (
            <div className="auth-error">{formError}</div>
          )}

          <div className="review-form-actions">
            <button
              className="review-submit-btn"
              onClick={handleSubmit}
              disabled={formLoading}
            >
              {formLoading
                ? "Saving..."
                : editingReview
                  ? "Update Review"
                  : "Submit Review"}
            </button>

            {editingReview && (
              <button
                className="review-cancel-btn"
                onClick={handleCancelEdit}
                disabled={formLoading}
              >
                Cancel
              </button>
            )}
          </div>
        </section>

        {/* AI ANALYSIS */}
        <section className="analysis-box">
          <h3>🤖 AI Review Analysis</h3>

          <p>
            Analyze customer feedback with your trained RoBERTa
            model. Discover product aspects and their predicted
            sentiment.
          </p>

          <button
            className="ai-btn"
            onClick={handleAnalyzeReviews}
            disabled={aiLoading || loading || reviews.length === 0}
          >
            {aiLoading
              ? "⏳ Analyzing Reviews..."
              : "✨ Analyze with AI"}
          </button>

          {aiLoading && (
            <div className="ai-loading-message" role="status">
              The AI model is analyzing customer feedback.
              <br />
              This may take several seconds.
            </div>
          )}

          {aiError && (
            <div className="ai-error-message" role="alert">
              {aiError}
            </div>
          )}

          {/* AI RESULTS */}
          {aiAnalysis && (
            <div className="ai-results">
              <div className="ai-results-heading">
                <h3>Analysis Results</h3>

                <span className="ai-model-badge">
                  {aiAnalysis.metadata?.model || "RoBERTa"}
                </span>
              </div>

              <div className="ai-summary-card">
                <span>Overall Sentiment</span>

                <strong
                  className={getSentimentClass(
                    aiAnalysis.overall_sentiment
                  )}
                >
                  {formatSentiment(
                    aiAnalysis.overall_sentiment
                  )}
                </strong>

                <small>
                  Analyzed {aiAnalysis.analyzedReviewCount}{" "}
                  customer review
                  {aiAnalysis.analyzedReviewCount === 1 ? "" : "s"}
                </small>
              </div>

              <div className="ai-aspects-heading">
                <h4>Aspect-Based Sentiment</h4>

                <span>
                  {aiAnalysis.aspects.length} aspects detected
                </span>
              </div>

              {aiAnalysis.aspects.length > 0 ? (
                <div className="ai-aspects-list">
                  {aiAnalysis.aspects.map((item, index) => (
                    <article
                      className="ai-aspect-card"
                      key={`${item.aspect}-${index}`}
                    >
                      <div className="ai-aspect-top">
                        <h4>{item.aspect}</h4>

                        <span
                          className={`ai-sentiment-badge ${getSentimentClass(
                            item.sentiment
                          )}`}
                        >
                          {formatSentiment(item.sentiment)}
                        </span>
                      </div>

                      {item.context && (
                        <p className="ai-aspect-context">
                          "{item.context}"
                        </p>
                      )}

                      <div className="ai-confidence-row">
                        <span>Prediction confidence</span>

                        <strong>
                          {formatConfidence(item.confidence)}
                        </strong>
                      </div>

                      {item.probabilities && (
                        <div className="ai-probabilities">
                          {["positive", "neutral", "negative"].map(
                            (label) => {
                              const probability = Number(
                                item.probabilities[label]
                              );

                              if (!Number.isFinite(probability)) {
                                return null;
                              }

                              const percentage = Math.max(
                                0,
                                Math.min(100, probability * 100)
                              );

                              return (
                                <div
                                  className="ai-probability-item"
                                  key={label}
                                >
                                  <div className="ai-probability-label">
                                    <span>{formatSentiment(label)}</span>
                                    <span>
                                      {percentage.toFixed(1)}%
                                    </span>
                                  </div>

                                  <div className="ai-probability-track">
                                    <div
                                      className={`ai-probability-fill ${getSentimentClass(
                                        label
                                      )}`}
                                      style={{
                                        width: `${percentage}%`,
                                      }}
                                    />
                                  </div>
                                </div>
                              );
                            }
                          )}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              ) : (
                <div className="message">
                  No aspects were detected in these reviews.
                </div>
              )}

              <div className="ai-disclaimer">
                <strong>Research note:</strong> Confidence represents
                the model's estimated probability for a prediction,
                calibrated with Temperature Scaling (T = {aiAnalysis.metadata?.temperature ? Number(aiAnalysis.metadata.temperature).toFixed(2) : "1.33"}).
                The improved RoBERTa model achieved 64.44% test accuracy
                and 0.77 positive F1 on the held-out benchmark.
              </div>
            </div>
          )}
        </section>

        {/* CUSTOMER REVIEWS */}
        <section className="reviews-section">
          <h2>Customer Reviews</h2>

          {loading && (
            <div className="message">Loading reviews...</div>
          )}

          {error && (
            <div className="message error">
              Error: {error}
            </div>
          )}

          {!loading && !error && reviews.length === 0 && (
            <div className="message">
              No reviews found for this product.
            </div>
          )}

          {!loading && !error && reviews.length > 0 && (
            <div className="reviews-list">
              {reviews.map((review, index) => (
                <div
                  className="review-card"
                  key={review.review_id || index}
                >
                  <div className="review-top">
                    <strong>
                      {review.username || "Anonymous User"}
                    </strong>

                    <span className="rating">
                      ⭐ {review.rating}/5
                    </span>
                  </div>

                  <p className="review-text">
                    {review.review_text}
                  </p>

                  <div className="review-card-bottom">
                    {review.created_at ? (
                      <span className="review-date">
                        {new Date(
                          review.created_at
                        ).toLocaleString()}
                      </span>
                    ) : (
                      <span />
                    )}

                    {currentUser &&
                      String(review.user_id) ===
                        String(currentUser.user_id) && (
                        <div className="card-actions">
                          <button
                            className="edit-btn"
                            onClick={() => handleEditClick(review)}
                            aria-label="Edit review"
                          >
                            ✏️
                          </button>

                          <button
                            className="delete-btn"
                            onClick={() =>
                              handleDeleteClick(review.review_id)
                            }
                            aria-label="Delete review"
                          >
                            🗑️
                          </button>
                        </div>
                      )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default ProductReviews;