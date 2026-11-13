const reviewService = require("../services/reviewService");

exports.getAllReviews = async (req, res) => {

    try {

        const result = await reviewService.getAllReviews();

        res.status(200).json(result);

    } catch (error) {

        res.status(500).json({
            success: false,
            message: error.message
        });

    }

};

exports.getReviewById = async (req, res) => {
    try {
        const reviewId = req.params.id;

        const result = await reviewService.getReviewById(reviewId);

        res.status(200).json({
            success: true,
            review: result
        });
    } catch (error) {
        res.status(404).json({
            success: false,
            message: error.message
        });
    }
};

exports.createReview = async (req, res) => {

    try {

        const { product_id, review_text, rating } = req.body;

            if (!product_id) {
                return res.status(400).json({
                    success: false,
                    message: "Product ID is required"
                });
            }

            if (!review_text || !review_text.trim()) {
                return res.status(400).json({
                    success: false,
                    message: "Review text is required"
                });
            }

            if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
                return res.status(400).json({
                    success: false,
                    message: "Rating must be an integer between 1 and 5"
                });
            }
        const userId = req.user.user_id;

        const result = await reviewService.createReview(
            userId,
            req.body
        );

        res.status(201).json({
            success: true,
            message: "Review created successfully",
            review: result
        });

    } catch (error) {

        res.status(500).json({
            success: false,
            message: error.message
        });

    }
};

exports.updateReview = async (req, res) => {

    try {
        const userId = req.user.user_id;
        const reviewId = req.params.id;

        const result = await reviewService.updateReview(
            reviewId,
            userId,
            req.body
        );

        res.status(200).json({
            success: true,
            message: "Review updated successfully",
            review: result
        });

    } catch (error) {

        res.status(500).json({
            success: false,
            message: error.message
        });

    }
};

exports.deleteReview = async (req, res) => {

    try {
        const userId = req.user.user_id;
        const reviewId = req.params.id;

        const result = await reviewService.deleteReview(
            reviewId,
            userId
        );

        res.status(200).json({
            success: true,
            message: "Review deleted successfully",
            review: result
        });

    } catch (error) {

        res.status(500).json({
            success: false,
            message: error.message
        });

    }
};

exports.getMyReviews = async (req, res) => {
    try {
        const userId = req.user.user_id;

        const result = await reviewService.getMyReviews(userId);

        res.status(200).json({
            success: true,
            reviews: result
        });

    } catch (error) {
        res.status(500).json({
            success: false,
            message: error.message
        });
    }
};