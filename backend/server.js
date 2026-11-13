const app = require("./app");
const initDatabase = require("./config/initDb");

const PORT = process.env.PORT || 5000;

async function startServer() {
    await initDatabase();

    app.listen(PORT, () => {
        console.log(`🚀 SmartReview AI Backend running on Port ${PORT}`);
    });
}

startServer();
