const aiWorker = require("../services/aiWorker");

const analyzeReview = async (req, res) => {
    try {
        const { review } = req.body;

        if (
            typeof review !== "string" ||
            !review.trim()
        ) {
            return res.status(400).json({
                success: false,
                message: "Please provide a valid review."
            });
        }

        if (review.length > 10000) {
            return res.status(400).json({
                success: false,
                message: "Review cannot exceed 10000 characters."
            });
        }

        const result = await aiWorker.analyzeReview(
            review.trim()
        );

        return res.status(200).json({
            success: true,
            message: "Review analyzed successfully.",
            data: result
        });

    } catch (error) {
        console.error(
            "[AI Controller] Analysis failed:",
            error.message
        );

        return res.status(500).json({
            success: false,
            message: "Unable to analyze the review right now."
        });
    }
};

module.exports = {
    analyzeReview
};