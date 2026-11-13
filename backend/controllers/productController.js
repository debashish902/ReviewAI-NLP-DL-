const productService = require("../services/productService");
const externalApiService = require("../services/externalApiService");

exports.getAllProducts = async (req, res) => {
    try {
        const result = await productService.getAllProducts();

        res.status(200).json({
            success: true,
            products: result
        });

    } catch (error) {
        res.status(500).json({
            success: false,
            message: error.message
        });
    }
};

exports.getProductById = async (req, res) => {
    try {
        const productId = req.params.id;

        const result = await productService.getProductById(productId);

        res.status(200).json({
            success: true,
            product: result
        });

    } catch (error) {
        res.status(404).json({
            success: false,
            message: error.message
        });
    }
};

exports.createProduct = async (req, res) => {
    try {

        const { product_name, category, brand } = req.body;

            if (!product_name || !product_name.trim()) {
                return res.status(400).json({
                    success: false,
                    message: "Product name is required"
                });
            }

            if (!category || !category.trim()) {
                return res.status(400).json({
                    success: false,
                    message: "Category is required"
                });
            }

            if (!brand || !brand.trim()) {
                return res.status(400).json({
                    success: false,
                    message: "Brand is required"
                });
            }
        const result = await productService.createProduct(req.body);

        res.status(201).json({
            success: true,
            message: "Product created successfully",
            product: result
        });

    } catch (error) {
        res.status(500).json({
            success: false,
            message: error.message
        });
    }
};

exports.updateProduct = async (req, res) => {
    try {
        const productId = req.params.id;

        const result = await productService.updateProduct(
            productId,
            req.body
        );

        res.status(200).json({
            success: true,
            message: "Product updated successfully",
            product: result
        });

    } catch (error) {
        res.status(404).json({
            success: false,
            message: error.message
        });
    }
};

exports.deleteProduct = async (req, res) => {
    try {
        const productId = req.params.id;

        const result = await productService.deleteProduct(productId);

        res.status(200).json({
            success: true,
            message: "Product deleted successfully",
            product: result
        });

    } catch (error) {
        res.status(404).json({
            success: false,
            message: error.message
        });
    }
};

exports.getProductReviews = async (req, res) => {
    try {
        const productId = req.params.id;

        const result = await productService.getProductReviews(productId);

        res.status(200).json({
            success: true,
            product_id: productId,
            reviews: result
        });

    } catch (error) {
        res.status(500).json({
            success: false,
            message: error.message
        });
    }
};

exports.searchExternalProducts = async (req, res) => {
    try {
        const query = req.query.q || "";
        const results = await externalApiService.searchExternalProducts(query);

        res.status(200).json({
            success: true,
            products: results
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: error.message
        });
    }
};

exports.importExternalProduct = async (req, res) => {
    try {
        const { externalId } = req.body;
        if (!externalId) {
            return res.status(400).json({
                success: false,
                message: "externalId is required"
            });
        }

        const result = await externalApiService.importExternalProductById(externalId);

        res.status(200).json({
            success: true,
            message: `Imported ${result.product.product_name} with ${result.importedReviewsCount} reviews`,
            ...result
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: error.message
        });
    }
};

exports.syncExternalCatalog = async (req, res) => {
    try {
        const { categories, maxProducts } = req.body || {};
        const result = await externalApiService.syncExternalCatalog(categories, maxProducts);

        res.status(200).json({
            success: true,
            message: `Synced ${result.totalProcessed} products and ${result.reviewsAdded} reviews from live external API.`,
            ...result
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            message: error.message
        });
    }
};