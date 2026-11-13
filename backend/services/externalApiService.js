const pool = require("../config/database");
const bcrypt = require("bcrypt");

const DUMMYJSON_BASE = "https://dummyjson.com/products";

// Map DummyJSON category slugs to clean display names
function formatCategoryName(rawCategory) {
  if (!rawCategory) return "Electronics";
  return rawCategory
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Search external products in real time via DummyJSON API
 */
exports.searchExternalProducts = async (query) => {
  const cleanQuery = (query || "").trim();
  const url = cleanQuery
    ? `${DUMMYJSON_BASE}/search?q=${encodeURIComponent(cleanQuery)}&limit=12`
    : `${DUMMYJSON_BASE}?limit=12`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`External API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  const products = Array.isArray(data.products) ? data.products : [];

  return products.map((p) => ({
    external_id: `dummyjson_${p.id}`,
    raw_id: p.id,
    product_name: p.title,
    brand: p.brand || "Generic",
    category: formatCategoryName(p.category),
    price: p.price || 0,
    description: p.description || "",
    image_url: p.thumbnail || (Array.isArray(p.images) && p.images[0]) || "",
    rating: p.rating || 0,
    review_count: Array.isArray(p.reviews) ? p.reviews.length : 0,
    reviews: Array.isArray(p.reviews) ? p.reviews : []
  }));
};

/**
 * Filter out legacy/outdated DummyJSON models during bulk catalog sync
 */
const LEGACY_PRODUCT_REGEX = /\b(iphone\s*(5s?|6s?|x\b)|galaxy\s*s[78]\b|galaxy\s*s10|galaxy\s*tab\s*white|oppo\s*(a57|f19|k1)|vivo\s*(s1|v9|x21)|realme\s*(c35|x\b|xt\b)|yoga\s*920|airpower|monopod|selfie\s*(lamp|stick)|camera\s*pedestal|iphone\s*12\s*silicone)\b/i;

/**
 * Fetch products from specific external categories
 */
exports.fetchExternalByCategories = async (categories = ["laptops", "tablets", "mobile-accessories"]) => {
  const allProducts = [];

  for (const cat of categories) {
    try {
      const response = await fetch(`${DUMMYJSON_BASE}/category/${encodeURIComponent(cat)}`);
      if (!response.ok) continue;
      const data = await response.json();
      if (Array.isArray(data.products)) {
        allProducts.push(...data.products);
      }
    } catch (err) {
      console.error(`Failed to fetch category ${cat}:`, err.message);
    }
  }

  return allProducts;
};

/**
 * Helper to get or create a reviewer user in PostgreSQL
 */
async function ensureReviewerUser(client, reviewerName, reviewerEmail, defaultPasswordHash) {
  const safeName = (reviewerName || "Verified Buyer").trim();
  const safeEmail = (
    reviewerEmail ||
    `${safeName.toLowerCase().replace(/[^a-z0-9]/g, ".")}@external.smartreview.ai`
  ).toLowerCase();

  // Check if email already exists
  const existing = await client.query(
    "SELECT user_id FROM users WHERE email = $1",
    [safeEmail]
  );

  if (existing.rows.length > 0) {
    return existing.rows[0].user_id;
  }

  const created = await client.query(
    `INSERT INTO users (username, email, password)
     VALUES ($1, $2, $3)
     RETURNING user_id`,
    [safeName, safeEmail, defaultPasswordHash]
  );

  return created.rows[0].user_id;
}

/**
 * Import a single product by DummyJSON ID along with its photo and external reviews
 */
exports.importExternalProductById = async (rawExternalId) => {
  const response = await fetch(`${DUMMYJSON_BASE}/${encodeURIComponent(rawExternalId)}`);
  if (!response.ok) {
    throw new Error(`Could not fetch external product ID ${rawExternalId}`);
  }

  const p = await response.json();
  return await saveExternalProductToDb(p);
};

/**
 * Persist an external API product object + its reviews into PostgreSQL
 */
async function saveExternalProductToDb(p) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    const externalId = `dummyjson_${p.id}`;
    const imageUrl = p.thumbnail || (Array.isArray(p.images) && p.images[0]) || "";
    const brand = p.brand || "Generic";
    const category = formatCategoryName(p.category);
    const description = p.description || "";
    const price = p.price ? Number(p.price) : null;

    // Upsert product based on external_id or matching product_name
    const existingProd = await client.query(
      "SELECT product_id FROM products WHERE external_id = $1 OR LOWER(product_name) = LOWER($2) LIMIT 1",
      [externalId, p.title]
    );

    let productId;
    let isNewProduct = false;

    if (existingProd.rows.length > 0) {
      productId = existingProd.rows[0].product_id;
      await client.query(
        `UPDATE products
         SET product_name = $1, category = $2, brand = $3, image_url = $4, description = $5, price = $6
         WHERE product_id = $7`,
        [p.title, category, brand, imageUrl, description, price, productId]
      );
    } else {
      const insertProd = await client.query(
        `INSERT INTO products (product_name, category, brand, image_url, description, price, external_id)
         VALUES ($1, $2, $3, $4, $5, $6, $7)
         RETURNING product_id`,
        [p.title, category, brand, imageUrl, description, price, externalId]
      );
      productId = insertProd.rows[0].product_id;
      isNewProduct = true;
    }

    const defaultPasswordHash = await bcrypt.hash("ExternalUser@123", 10);
    const externalReviews = Array.isArray(p.reviews) ? p.reviews : [];
    let importedReviewsCount = 0;

    for (const rev of externalReviews) {
      const userId = await ensureReviewerUser(
        client,
        rev.reviewerName,
        rev.reviewerEmail,
        defaultPasswordHash
      );

      const comment = (rev.comment || "").trim();
      const rating = Math.min(5, Math.max(1, Math.round(Number(rev.rating) || 4)));
      const reviewDate = rev.date ? new Date(rev.date) : new Date();

      if (!comment) continue;

      // Avoid duplicating identical review text for the same user & product
      const existingRev = await client.query(
        `SELECT review_id FROM reviews
         WHERE product_id = $1 AND user_id = $2 AND review_text = $3`,
        [productId, userId, comment]
      );

      if (existingRev.rows.length === 0) {
        await client.query(
          `INSERT INTO reviews (user_id, product_id, review_text, rating, created_at)
           VALUES ($1, $2, $3, $4, $5)`,
          [userId, productId, comment, rating, reviewDate]
        );
        importedReviewsCount++;
      }
    }

    await client.query("COMMIT");

    const finalProd = await pool.query(
      `SELECT p.*, COALESCE(COUNT(r.review_id), 0)::int AS review_count,
              COALESCE(ROUND(AVG(r.rating)::numeric, 1), 0.0) AS avg_rating
       FROM products p
       LEFT JOIN reviews r ON p.product_id = r.product_id
       WHERE p.product_id = $1
       GROUP BY p.product_id`,
      [productId]
    );

    return {
      product: finalProd.rows[0],
      isNewProduct,
      importedReviewsCount
    };
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

exports.saveExternalProductToDb = saveExternalProductToDb;

/**
 * Sync real-time electronics catalog from DummyJSON into database
 * Excludes older legacy models (e.g., iPhone 5s, S7, Vivo S1) so catalog stays modern.
 */
exports.syncExternalCatalog = async (categories = ["laptops", "tablets", "mobile-accessories"], maxProducts = 20) => {
  const externalProducts = await exports.fetchExternalByCategories(categories);
  const modernOnly = externalProducts.filter(
    (p) => p && p.title && !LEGACY_PRODUCT_REGEX.test(p.title)
  );
  const selected = modernOnly.slice(0, maxProducts);

  let createdCount = 0;
  let updatedCount = 0;
  let reviewsAdded = 0;

  for (const p of selected) {
    const result = await saveExternalProductToDb(p);
    if (result.isNewProduct) createdCount++;
    else updatedCount++;
    reviewsAdded += result.importedReviewsCount;
  }

  return {
    totalProcessed: selected.length,
    createdCount,
    updatedCount,
    reviewsAdded
  };
};
