const pool = require("../config/database");
const bcrypt = require("bcrypt");
const jwt = require("jsonwebtoken");

exports.registerUser = async (userData) => {

    const { username, email, password } = userData;

    const hashedPassword = await bcrypt.hash(password, 10);

    const result = await pool.query(
        `INSERT INTO users (username, email, password)
         VALUES ($1, $2, $3)
         RETURNING user_id, username, email`,
        [username, email, hashedPassword]
    );

    return {
        success: true,
        message: "User registered successfully",
        user: result.rows[0]
    };

};

exports.loginUser = async (userData) => {

    const { email, password } = userData;

    const result = await pool.query(
        "SELECT * FROM users WHERE email = $1",
        [email]
    );
    

    if (result.rows.length === 0) {
        throw new Error("User not found");
    }

    const user = result.rows[0];

    const isPasswordCorrect = await bcrypt.compare(
        password,
        user.password
    );

    if (!isPasswordCorrect) {
        throw new Error("Invalid password");
    }


    const token = jwt.sign(
    {
        user_id: user.user_id,
        email: user.email
    },
    process.env.JWT_SECRET,
    {
        expiresIn: "1d"
    }
    );
    return {
    success: true,
    message: "Login successful",
    token,
    user: {
        user_id: user.user_id,
        username: user.username,
        email: user.email
    }
    };
};