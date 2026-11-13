import React, { useEffect, useMemo, useState } from "react";
import { API_URL } from "../config/api";

function Products({ onSelectProduct, user, onLogout, onNavigateHome, theme, toggleTheme }) {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Modal and CRUD states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create"); // 'create' or 'edit'
  const [editingProductId, setEditingProductId] = useState(null);

  const [formData, setFormData] = useState({
    product_name: "",
    category: "",
    brand: "",
    price: "",
    image_url: "",
    description: ""
  });
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState("");

  // External API Live Search & Import Modal states
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [externalQuery, setExternalQuery] = useState("watch");
  const [externalResults, setExternalResults] = useState([]);
  const [externalLoading, setExternalLoading] = useState(false);
  const [externalError, setExternalError] = useState("");
  const [importingId, setImportingId] = useState(null);
  const [importSuccessMsg, setImportSuccessMsg] = useState("");
  const [syncingAll, setSyncingAll] = useState(false);

  const fetchProducts = () => {
    fetch(`${API_URL}/api/products`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to fetch products");
        }
        return response.json();
      })
      .then((data) => {
        setProducts(data.products || []);
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const getCategoryIcon = (catName) => {
    const cat = String(catName || "").toLowerCase();
    if (cat.includes("vr") || cat.includes("headset")) return "🥽";
    if (cat.includes("drone")) return "🚁";
    if (cat.includes("phone") || cat.includes("mobile")) return "📱";
    if (cat.includes("laptop") || cat.includes("computer") || cat.includes("pc")) return "💻";
    if (cat.includes("audio") || cat.includes("headphone") || cat.includes("speaker") || cat.includes("earbud") || cat.includes("accessor")) return "🎧";
    if (cat.includes("watch") || cat.includes("wearable")) return "⌚";
    if (cat.includes("camera") || cat.includes("photo")) return "📷";
    if (cat.includes("gaming") || cat.includes("console")) return "🎮";
    if (cat.includes("tablet") || cat.includes("ipad")) return "📟";
    return "📦";
  };

  const categories = useMemo(() => {
    return ["All", ...new Set(products.map((product) => product.category))];
  }, [products]);

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const matchesSearch = product.product_name
        .toLowerCase()
        .includes(search.toLowerCase()) ||
        (product.brand || "").toLowerCase().includes(search.toLowerCase());

      const matchesCategory =
        category === "All" || product.category === category;

      return matchesSearch && matchesCategory;
    });
  }, [products, search, category]);

  const openCreateModal = () => {
    setModalMode("create");
    setEditingProductId(null);
    setFormData({
      product_name: "",
      category: "",
      brand: "",
      price: "",
      image_url: "",
      description: ""
    });
    setModalError("");
    setIsModalOpen(true);
  };

  const openEditModal = (product) => {
    setModalMode("edit");
    setEditingProductId(product.product_id);
    setFormData({
      product_name: product.product_name || "",
      category: product.category || "",
      brand: product.brand || "",
      price: product.price || "",
      image_url: product.image_url || "",
      description: product.description || ""
    });
    setModalError("");
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setModalError("");
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setModalError("");

    if (!formData.product_name || !formData.category || !formData.brand) {
      setModalError("Product name, category, and brand are required.");
      return;
    }

    setModalLoading(true);

    const url =
      modalMode === "create"
        ? `${API_URL}/api/products`
        : `${API_URL}/api/products/${editingProductId}`;

    const method = modalMode === "create" ? "POST" : "PUT";

    const payload = {
      ...formData,
      price: formData.price ? Number(formData.price) : null,
      image_url: formData.image_url.trim() || null,
      description: formData.description.trim() || null
    };

    fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to ${modalMode} product`);
        }
        return response.json();
      })
      .then(() => {
        closeModal();
        fetchProducts();
      })
      .catch((err) => {
        setModalError(err.message);
      })
      .finally(() => {
        setModalLoading(false);
      });
  };

  const handleDelete = (product_id) => {
    if (window.confirm("Are you sure you want to delete this product?")) {
      fetch(`${API_URL}/api/products/${product_id}`, {
        method: "DELETE"
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Failed to delete product");
          }
          fetchProducts();
        })
        .catch((err) => {
          alert(err.message);
        });
    }
  };

  // =========================================================
  // EXTERNAL LIVE API SEARCH & IMPORT
  // =========================================================

  const handleOpenImportModal = () => {
    setIsImportModalOpen(true);
    setImportSuccessMsg("");
    setExternalError("");
    searchExternalApi(externalQuery);
  };

  const searchExternalApi = async (queryText) => {
    setExternalLoading(true);
    setExternalError("");
    try {
      const res = await fetch(
        `${API_URL}/api/products/external/search?q=${encodeURIComponent(queryText || "")}`
      );
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.message || "Failed to search external API");
      }
      setExternalResults(data.products || []);
    } catch (err) {
      setExternalError(err.message);
    } finally {
      setExternalLoading(false);
    }
  };

  const handleSearchExternalSubmit = (e) => {
    e.preventDefault();
    searchExternalApi(externalQuery);
  };

  const handleImportExternalProduct = async (item) => {
    setImportingId(item.raw_id);
    setExternalError("");
    setImportSuccessMsg("");
    try {
      const res = await fetch(`${API_URL}/api/products/external/import`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ externalId: item.raw_id })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.message || "Import failed");
      }
      setImportSuccessMsg(
        `✅ Imported "${item.product_name}" with photo and ${data.importedReviewsCount} real-time reviews!`
      );
      fetchProducts();
    } catch (err) {
      setExternalError(err.message);
    } finally {
      setImportingId(null);
    }
  };

  const handleSyncCatalog = async () => {
    setSyncingAll(true);
    setImportSuccessMsg("");
    setExternalError("");
    try {
      const res = await fetch(`${API_URL}/api/products/external/sync`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          categories: ["laptops", "mobile-accessories", "tablets"],
          maxProducts: 20
        })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.message || "Sync failed");
      }
      setImportSuccessMsg(`✅ ${data.message}`);
      fetchProducts();
    } catch (err) {
      setExternalError(err.message);
    } finally {
      setSyncingAll(false);
    }
  };

  if (loading && products.length === 0) {
    return (
      <div className="app">
        <div className="message">Loading real-time products...</div>
      </div>
    );
  }

  if (error && products.length === 0) {
    return (
      <div className="app">
        <div className="message error">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div>
          <h1>SmartReview AI</h1>
          <p>AI-Powered E-Commerce Review Analysis</p>

          {user && <p className="welcome">Welcome, {user.username}</p>}
        </div>

        <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
          <button
            className="header-nav-btn"
            onClick={onNavigateHome}
            title="Go to Home / Overview"
          >
            🏠 Home
          </button>
          <button
            className="header-nav-btn active"
            title="Current Page: Products Catalog"
          >
            📦 Products
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

      {/* Main */}
      <main className="container">
        <section className="dashboard-header">
          <div>
            <h2>Real-Time Product Catalog</h2>
            <p>Latest 2024–2025 flagship products with real photos &amp; rich multi-aspect reviews</p>
          </div>

          <div className="stats">
            <div className="stat-card">
              <span>Total Products</span>
              <strong>{products.length}</strong>
            </div>

            <div className="stat-card">
              <span>Categories</span>
              <strong>{Math.max(0, categories.length - 1)}</strong>
            </div>

            <button className="import-api-btn" onClick={handleOpenImportModal}>
              🌐 Import Live API
            </button>

            <button className="add-product-btn" onClick={openCreateModal}>
              + Add Product
            </button>
          </div>
        </section>

        {/* Search + Filter */}
        <section className="filters">
          <input
            type="text"
            placeholder="Search by product name or brand..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </section>

        {/* Products Grid */}
        <section className="products-grid">
          {filteredProducts.length === 0 ? (
            <div className="message">No products found.</div>
          ) : (
            filteredProducts.map((product) => (
              <div className="product-card" key={product.product_id}>
                <div className="product-image-box">
                  {product.image_url ? (
                    <img
                      src={product.image_url}
                      alt={product.product_name}
                      className="product-image"
                      loading="lazy"
                    />
                  ) : (
                    <div className="product-icon">
                      {getCategoryIcon(product.category)}
                    </div>
                  )}

                  {product.price && (
                    <span className="product-price-tag">
                      ${Number(product.price).toFixed(2)}
                    </span>
                  )}
                </div>

                <h3>{product.product_name}</h3>

                <div className="product-rating-row">
                  <span className="product-stars">
                    ⭐{" "}
                    {product.avg_rating && Number(product.avg_rating) > 0
                      ? Number(product.avg_rating).toFixed(1)
                      : "New"}
                  </span>
                  <span className="product-review-count">
                    {product.review_count > 0
                      ? `(${product.review_count} ${
                          product.review_count === 1 ? "review" : "reviews"
                        })`
                      : "(No reviews yet)"}
                  </span>
                </div>

                <div className="product-info">
                  <p>
                    <strong>Brand:</strong> {product.brand}
                  </p>

                  <p>
                    <strong>Category:</strong> {product.category}
                  </p>
                </div>

                {product.description && (
                  <p className="product-desc-snippet">
                    {product.description.length > 85
                      ? product.description.slice(0, 85) + "..."
                      : product.description}
                  </p>
                )}

                <div className="card-actions">
                  <button
                    className="edit-btn"
                    onClick={() => openEditModal(product)}
                    title="Edit"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    className="delete-btn"
                    onClick={() => handleDelete(product.product_id)}
                    title="Delete"
                  >
                    🗑️ Delete
                  </button>
                </div>

                <button
                  className="analyze-btn"
                  onClick={() => onSelectProduct(product)}
                >
                  ✨ Analyze Reviews
                </button>
              </div>
            ))
          )}
        </section>
      </main>

      {/* Add/Edit Product Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>{modalMode === "create" ? "Add New Product" : "Edit Product"}</h2>

            <form onSubmit={handleSubmit}>
              <div>
                <label>Product Name</label>
                <input
                  type="text"
                  name="product_name"
                  value={formData.product_name}
                  onChange={handleFormChange}
                  placeholder="e.g. iPhone 15 Pro"
                />
              </div>

              <div>
                <label>Category</label>
                <input
                  type="text"
                  name="category"
                  value={formData.category}
                  onChange={handleFormChange}
                  placeholder="e.g. Smartphones"
                />
              </div>

              <div>
                <label>Brand</label>
                <input
                  type="text"
                  name="brand"
                  value={formData.brand}
                  onChange={handleFormChange}
                  placeholder="e.g. Apple"
                />
              </div>

              <div>
                <label>Price ($)</label>
                <input
                  type="number"
                  step="0.01"
                  name="price"
                  value={formData.price}
                  onChange={handleFormChange}
                  placeholder="e.g. 999.99"
                />
              </div>

              <div>
                <label>Photo URL</label>
                <input
                  type="text"
                  name="image_url"
                  value={formData.image_url}
                  onChange={handleFormChange}
                  placeholder="https://..."
                />
              </div>

              {modalError && <div className="auth-error">{modalError}</div>}

              <div className="modal-actions">
                <button
                  type="button"
                  className="modal-cancel"
                  onClick={closeModal}
                  disabled={modalLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="modal-submit"
                  disabled={modalLoading}
                >
                  {modalLoading
                    ? modalMode === "create"
                      ? "Creating..."
                      : "Updating..."
                    : modalMode === "create"
                    ? "Create Product"
                    : "Update Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* External API Live Import Modal */}
      {isImportModalOpen && (
        <div className="modal-overlay">
          <div className="modal import-modal">
            <div className="import-modal-header">
              <div>
                <h2>🌐 Live External Product API</h2>
                <p>
                  Search real-time products via DummyJSON API and import them with
                  their photos & live customer reviews.
                </p>
              </div>
              <button
                className="modal-close-x"
                onClick={() => setIsImportModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={handleSearchExternalSubmit}
              className="external-search-bar"
            >
              <input
                type="text"
                value={externalQuery}
                onChange={(e) => setExternalQuery(e.target.value)}
                placeholder="Search real-time products (e.g. watch, laptop, phone, shoes, camera)..."
              />
              <button type="submit" disabled={externalLoading}>
                {externalLoading ? "Searching..." : "🔍 Search Live API"}
              </button>
              <button
                type="button"
                className="sync-all-btn"
                onClick={handleSyncCatalog}
                disabled={syncingAll}
                title="Refresh full tech catalog from DummyJSON"
              >
                {syncingAll ? "Syncing..." : "🔄 Sync Tech Catalog"}
              </button>
            </form>

            {importSuccessMsg && (
              <div className="register-success" style={{ marginBottom: "15px" }}>
                {importSuccessMsg}
              </div>
            )}

            {externalError && (
              <div className="auth-error" style={{ marginBottom: "15px" }}>
                {externalError}
              </div>
            )}

            <div className="external-results-scroll">
              {externalLoading ? (
                <div className="message">Querying live external API...</div>
              ) : externalResults.length === 0 ? (
                <div className="message">No external products matched your search.</div>
              ) : (
                <div className="external-results-grid">
                  {externalResults.map((item) => {
                    const alreadyExists = products.some(
                      (p) => p.external_id === item.external_id
                    );

                    return (
                      <div className="external-item-card" key={item.external_id}>
                        <div className="external-item-img-wrap">
                          <img
                            src={item.image_url}
                            alt={item.product_name}
                            loading="lazy"
                          />
                        </div>

                        <div className="external-item-info">
                          <span className="external-item-cat">
                            {item.category} • {item.brand}
                          </span>
                          <h4>{item.product_name}</h4>
                          <div className="external-item-meta">
                            <strong>${Number(item.price).toFixed(2)}</strong>
                            <span>⭐ {item.rating}</span>
                            <span>💬 {item.review_count} reviews</span>
                          </div>
                        </div>

                        <button
                          className={`external-import-btn ${
                            alreadyExists ? "reimport" : ""
                          }`}
                          onClick={() => handleImportExternalProduct(item)}
                          disabled={importingId === item.raw_id}
                        >
                          {importingId === item.raw_id
                            ? "Importing..."
                            : alreadyExists
                            ? "🔄 Re-sync"
                            : "📥 Import"}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Products;