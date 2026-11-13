const authService = require("../services/authService");

exports.registerUser = async (req, res) => {

    try {

        const result = await authService.registerUser(req.body);

        res.status(201).json(result);

    } catch (error) {

        res.status(500).json({
            success: false,
            message: error.message
        });

    }

};

exports.loginUser = async (req, res) => {
    try {

        const result = await authService.loginUser(req.body);

        res.status(200).json(result);

    } catch (error) {

        res.status(500).json({
            success: false,
            message: error.message
        });

    }
};