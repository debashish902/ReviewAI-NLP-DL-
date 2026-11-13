const pool = require("../config/database");

exports.getAllProducts = async () => {
    const result = await pool.query(`
        SELECT
            p.product_id,
            p.product_name,
            p.category,
            p.brand,
            p.image_url,
            p.description,
            p.price,
            p.external_id,
            p.created_at,
            COALESCE(COUNT(r.review_id), 0)::int AS review_count,
            COALESCE(ROUND(AVG(r.rating)::numeric, 1), 0.0) AS avg_rating
        FROM products p
        LEFT JOIN reviews r ON p.product_id = r.product_id
        GROUP BY p.product_id, p.product_name, p.category, p.brand, p.image_url, p.description, p.price, p.external_id, p.created_at
        ORDER BY p.product_id DESC
    `);

    return result.rows;
};

exports.getProductById = async (productId) => {
    const result = await pool.query(
        `
        SELECT
            product_id,
            product_name,
            category,
            brand,
            image_url,
            description,
            price,
            external_id,
            created_at
        FROM products
        WHERE product_id = $1
        `,
        [productId]
    );

    if (result.rows.length === 0) {
        throw new Error("Product not found");
    }

    return result.rows[0];
};

exports.createProduct = async (productData) => {
    const { product_name, category, brand, image_url = null, description = null, price = null } = productData;

    const result = await pool.query(
        `
        INSERT INTO products (product_name, category, brand, image_url, description, price)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING product_id, product_name, category, brand, image_url, description, price, created_at
        `,
        [product_name, category, brand, image_url, description, price]
    );

    return result.rows[0];
};

exports.updateProduct = async (productId, productData) => {
    const { product_name, category, brand, image_url = null, description = null, price = null } = productData;

    const result = await pool.query(
        `
        UPDATE products
        SET
            product_name = $1,
            category = $2,
            brand = $3,
            image_url = COALESCE($4, image_url),
            description = COALESCE($5, description),
            price = COALESCE($6, price)
        WHERE product_id = $7
        RETURNING product_id, product_name, category, brand, image_url, description, price, created_at
        `,
        [product_name, category, brand, image_url, description, price, productId]
    );

    if (result.rows.length === 0) {
        throw new Error("Product not found");
    }

    return result.rows[0];
};

exports.deleteProduct = async (productId) => {
    const result = await pool.query(
        `
        DELETE FROM products
        WHERE product_id = $1
        RETURNING product_id
        `,
        [productId]
    );

    if (result.rows.length === 0) {
        throw new Error("Product not found");
    }

    return result.rows[0];
};

exports.getProductReviews = async (productId) => {
    const result = await pool.query(
        `
        SELECT
            reviews.review_id,
            reviews.user_id,
            users.username,
            reviews.rating,
            reviews.review_text,
            reviews.created_at
        FROM reviews
        JOIN users
            ON reviews.user_id = users.user_id
        WHERE reviews.product_id = $1
        ORDER BY reviews.created_at DESC
        `,
        [productId]
    );

    return result.rows;
};