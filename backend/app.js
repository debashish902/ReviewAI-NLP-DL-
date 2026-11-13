const express = require("express");
const cors = require("cors");
const path = require("path");
require("dotenv").config();

const reviewRoutes = require("./routes/reviewRoutes");
const authRoutes = require("./routes/authRoutes");
const productRoutes = require("./routes/productRoutes");
const aiRoutes = require("./routes/aiRoutes");

const app = express();

app.use(cors());
app.use(express.json());

app.get("/api/health", (req, res) => {
    res.json({
        success: true,
        message: "🚀 SmartReview AI Backend is Running Successfully!"
    });
});

app.use("/api/ai", aiRoutes);
app.use("/api/reviews", reviewRoutes);
app.use("/api/auth", authRoutes);
app.use("/api/products", productRoutes);

// In production, serve the frontend dist folder if available
const frontendDistPath = path.resolve(__dirname, "../frontend/dist");
app.use(express.static(frontendDistPath));

app.get("*", (req, res) => {
    const indexPath = path.join(frontendDistPath, "index.html");
    res.sendFile(indexPath, (err) => {
        if (err) {
            res.json({
                success: true,
                message: "🚀 SmartReview AI Backend is Running Successfully!",
                status: "online"
            });
        }
    });
});

module.exports = app;
