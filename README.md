# SmartReview AI — Aspect-Based Sentiment Analysis Platform

SmartReview AI is an end-to-end intelligent e-commerce product review and aspect-based sentiment analysis (ABSA) system. Traditional star ratings obscure key product details — SmartReview AI automatically dissects unstructured consumer reviews into fine-grained features (such as **battery life**, **camera**, **sound quality**, **display**, and **build quality**) and delivers calibrated sentiment polarity using fine-tuned RoBERTa Transformer models.

---

## 🌟 Key Features

- **Aspect-Based Sentiment Analysis (ABSA)**: Isolates individual clauses and sentiments using spaCy NLP + fine-tuned RoBERTa.
- **Calibrated Prediction Confidence**: Post-hoc Temperature Scaling ($T = 1.33$) eliminates overconfidence and reduces Expected Calibration Error (ECE) by 57%.
- **Interactive Modern Frontend**:
  - React 19 + Vite with a modern Rose/Pink color palette.
  - Dark mode (Obsidian Rose) and Light mode (Blush Porcelain) with instant theme toggle.
  - Aspect rating distribution visualizer and sentiment breakdown cards.
  - Live external product search & catalog sync via DummyJSON API.
- **Robust REST API Backend**: Node.js, Express, PostgreSQL, JWT Authentication, and review CRUD with image support.
- **Model Training & Evaluation Pipeline**: Scripts for dataset preprocessing, error analysis, class weighting, and confidence calibration.

---

## 🏗️ Architecture

```
SmartReview AI/
├── ai-engine/             # NLP & Deep Learning Pipeline
│   ├── config/            # Model & inference configurations
│   ├── datasets/          # Curated ABSA train/test datasets & benchmarks
│   ├── inference/         # Prediction engine & aspect extractor
│   ├── models/            # RoBERTa training, weighting & calibration scripts
│   ├── preprocessing/     # Text cleaning & spaCy clause segmentation
│   └── utils/             # Evaluation metrics & audit utilities
├── backend/               # Node.js + Express REST API
│   ├── config/            # Database connection configuration
│   ├── controllers/       # Auth, Product & Review controllers
│   ├── middleware/        # JWT auth verification
│   ├── routes/            # API endpoints
│   ├── services/          # External API & AI integration
│   └── seed_modern_catalog.js # Tech flagship catalog seeder
├── frontend/              # React 19 + Vite Application
│   ├── src/
│   │   ├── pages/         # Index, Products, ProductReviews, Login, Register
│   │   ├── App.jsx        # App router & theme provider
│   │   ├── App.css        # Component styles & animations
│   │   └── index.css      # Theme design tokens & global styles
│   └── package.json
└── docs/                  # Documentation & architecture notes
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- PostgreSQL (v14+)

### 1. Backend Setup
```bash
cd backend
npm install

# Copy environment configuration
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Start backend server
node server.js
```
The backend will run on `http://localhost:5000`.

### 2. Frontend Setup
```bash
cd frontend
npm install

# Start Vite dev server
npm run dev
```
The frontend will run on `http://localhost:5173`.

### 3. AI Engine Setup (Optional / Inference)
```bash
cd ai-engine
pip install -r requirements.txt
python inference/predict.py
```

---

## 🔬 Model & Methodology

1. **Clause Segmentation**: spaCy parses complex review sentences (e.g., *"Great display, but poor battery life"* into independent aspect targets).
2. **Transformer Classification**: Fine-tuned RoBERTa evaluates polarity into *Positive*, *Neutral*, or *Negative*.
3. **Temperature Scaling**: Logits are scaled by learned parameter $T = 1.33$ on the validation set, ensuring predicted probabilities accurately reflect empirical confidence.

---

## 📄 License

This project is licensed under the MIT License.

