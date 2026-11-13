const express = require("express");

const router = express.Router();

const productController = require("../controllers/productController");

router.get("/", productController.getAllProducts);

router.get("/external/search", productController.searchExternalProducts);

router.post("/external/import", productController.importExternalProduct);

router.post("/external/sync", productController.syncExternalCatalog);

router.get("/:id/reviews", productController.getProductReviews);

router.get("/:id", productController.getProductById);

router.post("/", productController.createProduct);

router.put("/:id", productController.updateProduct);

router.delete("/:id", productController.deleteProduct);

module.exports = router;