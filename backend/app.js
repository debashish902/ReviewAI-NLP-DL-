const express = require("express");
const cors = require("cors");
require("dotenv").config();

const reviewRoutes = require("./routes/reviewRoutes");
const authRoutes = require("./routes/authRoutes");
const productRoutes = require("./routes/productRoutes");
const aiRoutes = require("./routes/aiRoutes");

const app = express();

app.use(cors());
app.use(express.json());
app.use("/api/ai", aiRoutes);

app.get("/", (req, res) => {
    res.json({
        success: true,
        message: "🚀 SmartReview AI Backend is Running Successfully!"
    });
});

app.use("/api/reviews", reviewRoutes);
app.use("/api/auth", authRoutes);
app.use("/api/products", productRoutes);

module.exports = app;