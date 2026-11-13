import React, { useEffect, useState } from "react";
import { API_URL } from "../config/api";

function Index({ user, onNavigateToProducts, onSelectProduct, onLogout, theme, toggleTheme }) {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [totalProductsCount, setTotalProductsCount] = useState(0);
  const [totalReviewsCount, setTotalReviewsCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/api/products`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch products");
        return res.json();
      })
      .then((data) => {
        const prods = data.products || [];
        setTotalProductsCount(prods.length);
        const revSum = prods.reduce((acc, p) => acc + (Number(p.review_count) || 0), 0);
        setTotalReviewsCount(revSum);
        // Prioritize products with images and highest rating
        const sorted = [...prods].sort((a, b) => {
          const hasImgA = a.image_url ? 1 : 0;
          const hasImgB = b.image_url ? 1 : 0;
          if (hasImgA !== hasImgB) return hasImgB - hasImgA;
          return (Number(b.avg_rating) || 0) - (Number(a.avg_rating) || 0);
        });
        setFeaturedProducts(sorted.slice(0, 6));
      })
      .catch((err) => {
        console.error("Failed to load featured products:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const getCategoryIcon = (category) => {
    const cat = String(category || "").toLowerCase();
    if (cat.includes("vr") || cat.includes("headset")) return "🥽";
    if (cat.includes("drone")) return "🚁";
    if (cat.includes("phone") || cat.includes("mobile")) return "📱";
    if (cat.includes("laptop") || cat.includes("computer") || cat.includes("pc")) return "💻";
    if (cat.includes("audio") || cat.includes("headphone") || cat.includes("speaker") || cat.includes("earbud")) return "🎧";
    if (cat.includes("watch") || cat.includes("wearable")) return "⌚";
    if (cat.includes("camera") || cat.includes("photo")) return "📷";
    if (cat.includes("gaming") || cat.includes("console")) return "🎮";
    if (cat.includes("accessori") || cat.includes("mouse") || cat.includes("keyboard")) return "🖱️";
    if (cat.includes("reader") || cat.includes("book")) return "📖";
    if (cat.includes("tablet") || cat.includes("ipad")) return "📟";
    return "📦";
  };

  return (
    <div className="app">
      {/* NAVIGATION HEADER */}
      <header className="header">
        <div>
          <h1>SmartReview AI</h1>
          <p>AI-Powered E-Commerce Review Analysis</p>
          {user && (
            <p className="welcome">
              Welcome back, {user.username}!
            </p>
          )}
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
          <button
            className="header-nav-btn active"
            title="Current Page"
          >
            🏠 Home
          </button>

          <button
            className="header-nav-btn"
            onClick={onNavigateToProducts}
            title="Browse all products and manage catalog"
          >
            📦 Product Catalog
          </button>

          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>

          <button className="refresh-btn" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="container">
        {/* HERO SECTION */}
        <section className="index-hero">
          <div className="hero-badge">
            🚀 Powered by Calibrated RoBERTa & spaCy NLP
          </div>

          <h2 className="hero-title">
            Transform Customer Feedback into <span className="gradient-text">Actionable Intelligence</span>
          </h2>

          <p className="hero-description">
            Traditional star ratings hide the details that matter most. SmartReview AI automatically dissects
            real consumer reviews into fine-grained aspects — such as <strong>battery life</strong>, <strong>camera</strong>, 
            <strong>sound quality</strong>, <strong>display</strong>, and <strong>build quality</strong> — delivering transparent, 
            calibrated sentiment analysis in real time.
          </p>

          <div className="hero-actions">
            <button className="hero-primary-btn" onClick={onNavigateToProducts}>
              Explore Product Catalog →
            </button>
            <a href="#featured-section" className="hero-secondary-btn">
              View Featured Products ↓
            </a>
          </div>

          {/* KEY STATS BAR */}
          <div className="hero-stats-grid">
            <div className="hero-stat-card">
              <span className="stat-icon">📱</span>
              <div className="stat-number">{totalProductsCount > 0 ? totalProductsCount : "25+"}</div>
              <div className="stat-label">Modern Tech Flagships</div>
            </div>

            <div className="hero-stat-card">
              <span className="stat-icon">💬</span>
              <div className="stat-number">{totalReviewsCount > 0 ? totalReviewsCount : "300+"}</div>
              <div className="stat-label">Authentic Customer Reviews</div>
            </div>

            <div className="hero-stat-card">
              <span className="stat-icon">🎯</span>
              <div className="stat-number">25+</div>
              <div className="stat-label">Monitored Aspects</div>
            </div>

            <div className="hero-stat-card">
              <span className="stat-icon">⚡</span>
              <div className="stat-number">64.4%</div>
              <div className="stat-label">Calibrated Model Accuracy</div>
            </div>
          </div>
        </section>

        {/* FEATURED PRODUCTS SHOWCASE */}
        <section id="featured-section" className="index-featured-section">
          <div className="section-header-row">
            <div>
              <h3>Featured Products</h3>
              <p>Live products with real photos & customer reviews ready for AI sentiment analysis</p>
            </div>

            <button className="view-all-link-btn" onClick={onNavigateToProducts}>
              View All Products ({totalProductsCount > 0 ? totalProductsCount : "..."}) →
            </button>
          </div>

          {loading ? (
            <div className="message">Loading featured products...</div>
          ) : (
            <div className="featured-products-grid">
              {featuredProducts.map((product) => (
                <div className="featured-card" key={product.product_id}>
                  <div className="featured-card-top">
                    <span className="featured-category-badge">
                      {getCategoryIcon(product.category)} {product.category}
                    </span>
                    <span className="featured-brand-badge">{product.brand}</span>
                  </div>

                  {product.image_url && (
                    <div className="featured-image-box">
                      <img
                        src={product.image_url}
                        alt={product.product_name}
                        className="featured-image"
                        loading="lazy"
                      />
                      {product.price && (
                        <span className="featured-price-pill">
                          ${Number(product.price).toFixed(2)}
                        </span>
                      )}
                    </div>
                  )}

                  <h4>{product.product_name}</h4>

                  <div className="featured-rating-row">
                    <span className="featured-stars">
                      ⭐ {product.avg_rating && Number(product.avg_rating) > 0 ? Number(product.avg_rating).toFixed(1) : "New"}
                    </span>
                    <span className="featured-count">
                      ({product.review_count || 0} reviews)
                    </span>
                  </div>

                  <p className="featured-aspects-hint">
                    {product.description
                      ? product.description.length > 90
                        ? product.description.slice(0, 90) + "..."
                        : product.description
                      : "Key aspects: Battery • Display • Camera • Build • Value"}
                  </p>

                  <div className="featured-actions">
                    <button
                      className="featured-analyze-btn"
                      onClick={() => onSelectProduct(product)}
                    >
                      ✨ Analyze Reviews
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* CALL TO ACTION BANNER */}
          <div className="index-cta-card">
            <div>
              <h3>Looking for a specific device?</h3>
              <p>
                Browse our complete catalog with live search, category filtering, and product management capabilities.
              </p>
            </div>
            <button className="cta-action-btn" onClick={onNavigateToProducts}>
              Open Full Catalog →
            </button>
          </div>
        </section>

        {/* HOW SMARTREVIEW AI WORKS */}
        <section className="index-features-section">
          <div className="section-title-center">
            <h3>How SmartReview AI Works</h3>
            <p>End-to-end Aspect-Based Sentiment Analysis (ABSA) pipeline</p>
          </div>

          <div className="features-grid">
            <div className="feature-box">
              <div className="feature-icon">🔍</div>
              <h4>1. Sentence & Clause Extraction</h4>
              <p>
                Reviews are broken into independent clauses using spaCy natural language processing,
                isolating contrasting phrases (e.g., <em>"Great display, but poor battery"</em>) so each feature is judged accurately.
              </p>
            </div>

            <div className="feature-box">
              <div className="feature-icon">🧠</div>
              <h4>2. Deep Learning Classification</h4>
              <p>
                Fine-tuned RoBERTa Transformer evaluates sentiment polarity for each specific aspect
                into Positive, Neutral, or Negative with calibrated probabilities.
              </p>
            </div>

            <div className="feature-box">
              <div className="feature-icon">📊</div>
              <h4>3. Temperature-Scaled Confidence</h4>
              <p>
                Post-hoc Temperature Scaling ($T = 1.33$) ensures prediction confidence is statistically grounded,
                reducing Expected Calibration Error by 57% and eliminating false overconfidence.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="index-footer">
        <p>SmartReview AI • Aspect-Based Sentiment Analysis Platform</p>
        <div style={{ display: "flex", gap: "16px", justifyContent: "center", marginTop: "8px" }}>
          <button className="link-button" onClick={onNavigateToProducts}>
            Product Catalog
          </button>
          <span>•</span>
          <button className="link-button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
            Back to Top ↑
          </button>
        </div>
      </footer>
    </div>
  );
}

export default Index;
