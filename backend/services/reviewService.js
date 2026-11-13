const pool = require("../config/database");

exports.getAllReviews = async () => {

    const result = await pool.query(`
         SELECT
            users.username,
            products.product_name,
            reviews.rating,
            reviews.review_text

        FROM reviews

        JOIN users
        ON reviews.user_id = users.user_id

        JOIN products
        ON reviews.product_id = products.product_id;
    `);

    return result.rows;

};

exports.getReviewById = async (reviewId) => {
    const result = await pool.query(
        `
        SELECT
            review_id,
            user_id,
            product_id,
            review_text,
            rating,
            created_at
        FROM reviews
        WHERE review_id = $1
        `,
        [reviewId]
    );

    if (result.rows.length === 0) {
        throw new Error("Review not found");
    }

    return result.rows[0];
};

exports.createReview = async (userId, reviewData) => {

    const { product_id, review_text, rating } = reviewData;

    const result = await pool.query(
        `
        INSERT INTO reviews (user_id, product_id, review_text, rating)
        VALUES ($1, $2, $3, $4)
        RETURNING review_id, user_id, product_id, review_text, rating, created_at
        `,
        [userId, product_id, review_text, rating]
    );

    return result.rows[0];
};

exports.updateReview = async (reviewId, userId, reviewData) => {

    const { review_text, rating } = reviewData;

    const result = await pool.query(
        `
        UPDATE reviews
        SET review_text = $1,
            rating = $2
        WHERE review_id = $3
        AND user_id = $4
        RETURNING review_id, user_id, product_id, review_text, rating, created_at
        `,
        [review_text, rating, reviewId, userId]
    );

    if (result.rows.length === 0) {
        throw new Error("Review not found or you are not authorized to update it");
    }

    return result.rows[0];
};

exports.deleteReview = async (reviewId, userId) => {

    const result = await pool.query(
        `
        DELETE FROM reviews
        WHERE review_id = $1
        AND user_id = $2
        RETURNING review_id
        `,
        [reviewId, userId]
    );

    if (result.rows.length === 0) {
        throw new Error("Review not found or you are not authorized to delete it");
    }

    return result.rows[0];
};

exports.getMyReviews = async (userId) => {

    const result = await pool.query(
        `
        SELECT
            reviews.review_id,
            reviews.user_id,
            reviews.product_id,
            products.product_name,
            reviews.review_text,
            reviews.rating,
            reviews.created_at
        FROM reviews
        JOIN products
            ON reviews.product_id = products.product_id
        WHERE reviews.user_id = $1
        ORDER BY reviews.created_at DESC
        `,
        [userId]
    );

    return result.rows;
};
