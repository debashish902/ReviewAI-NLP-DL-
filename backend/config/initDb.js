const pool = require("./database");

async function initDatabase() {
    try {
        console.log("[DB] Verifying database schema...");

        await pool.query(`
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS products (
                product_id SERIAL PRIMARY KEY,
                product_name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                brand VARCHAR(100),
                image_url TEXT,
                description TEXT,
                price NUMERIC(10, 2),
                external_id VARCHAR(100) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reviews (
                review_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
                rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                review_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        `);

        console.log("[DB] Schema verification completed successfully.");
    } catch (err) {
        console.error("[DB] Error initializing database tables:", err.message);
    }
}

module.exports = initDatabase;
