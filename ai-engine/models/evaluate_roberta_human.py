import os
import numpy as np
import pandas as pd
import torch

from transformers import AutoTokenizer, AutoModelForSequenceClassification

from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)


# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATASET_DIR = os.path.join(
    BASE_DIR,
    "datasets"
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models",
    "roberta_absa"
)

VALIDATION_FILE = os.path.join(
    DATASET_DIR,
    "validation_dataset.csv"
)

OUTPUT_FILE = os.path.join(
    DATASET_DIR,
    "roberta_human_predictions.csv"
)


# ============================================================
# 2. CONFIGURATION
# ============================================================

MAX_LENGTH = 128

BATCH_SIZE = 8

label2id = {
    "negative": 0,
    "neutral": 1,
    "positive": 2
}

id2label = {
    0: "negative",
    1: "neutral",
    2: "positive"
}


# ============================================================
# 3. DEVICE
# ============================================================

print("\n" + "=" * 65)
print("SMARTREVIEW AI - HUMAN VALIDATION EVALUATION")
print("=" * 65)

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(f"PyTorch version : {torch.__version__}")
print(f"CUDA available  : {torch.cuda.is_available()}")
print(f"Device          : {device}")

if torch.cuda.is_available():

    print(
        f"GPU             : "
        f"{torch.cuda.get_device_name(0)}"
    )


# ============================================================
# 4. CHECK FILES
# ============================================================

if not os.path.exists(VALIDATION_FILE):

    raise FileNotFoundError(
        f"Validation dataset not found:\n{VALIDATION_FILE}"
    )

if not os.path.exists(MODEL_DIR):

    raise FileNotFoundError(
        f"Trained model not found:\n{MODEL_DIR}"
    )


# ============================================================
# 5. LOAD VALIDATION DATA
# ============================================================

print("\nLoading validation dataset...")

df = pd.read_csv(
    VALIDATION_FILE
)

print(
    f"Total validation rows: {len(df)}"
)


# ============================================================
# 6. CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "sentence",
    "aspect",
    "validated_sentiment"
]

for column in required_columns:

    if column not in df.columns:

        raise ValueError(
            f"Missing required column: {column}"
        )


# ============================================================
# 7. KEEP ONLY HUMAN-VALIDATED ROWS
# ============================================================

df["validated_sentiment"] = (
    df["validated_sentiment"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)

df = df[
    df["validated_sentiment"].isin(
        [
            "negative",
            "neutral",
            "positive"
        ]
    )
].copy()

print(
    f"Human-validated rows: {len(df)}"
)

if len(df) == 0:

    raise ValueError(
        "No manually validated rows were found."
    )


# ============================================================
# 8. SHOW HUMAN LABEL DISTRIBUTION
# ============================================================

print("\nHuman-validated label distribution:")

print(
    df["validated_sentiment"]
    .value_counts()
)


# ============================================================
# 9. LOAD TOKENIZER
# ============================================================

print("\nLoading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR
)


# ============================================================
# 10. LOAD TRAINED MODEL
# ============================================================

print("Loading trained RoBERTa model...")

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_DIR
)

model.to(device)

model.eval()

print("Model loaded successfully.")


# ============================================================
# 11. CREATE ASPECT-CONDITIONED TEXT
# ============================================================

texts = []

for _, row in df.iterrows():

    sentence = str(
        row["sentence"]
    )

    aspect = str(
        row["aspect"]
    )

    text = (
        "Sentence: "
        + sentence
        + " Aspect: "
        + aspect
    )

    texts.append(text)


# ============================================================
# 12. MODEL PREDICTION
# ============================================================

predicted_labels = []
confidence_scores = []

print("\nRunning predictions...")

for start in range(
    0,
    len(texts),
    BATCH_SIZE
):

    batch_texts = texts[
        start:start + BATCH_SIZE
    ]

    inputs = tokenizer(
        batch_texts,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.no_grad():

        outputs = model(
            **inputs
        )

    probabilities = torch.softmax(
        outputs.logits,
        dim=-1
    )

    predictions = torch.argmax(
        probabilities,
        dim=-1
    )

    confidences = torch.max(
        probabilities,
        dim=-1
    ).values

    for prediction in predictions.cpu().numpy():

        predicted_labels.append(
            id2label[int(prediction)]
        )

    for confidence in confidences.cpu().numpy():

        confidence_scores.append(
            float(confidence)
        )

    print(
        f"Processed "
        f"{min(start + BATCH_SIZE, len(texts))}"
        f"/{len(texts)}"
    )


# ============================================================
# 13. STORE PREDICTIONS
# ============================================================

df["predicted_sentiment"] = predicted_labels

df["confidence"] = confidence_scores


# ============================================================
# 14. CALCULATE METRICS
# ============================================================

y_true = df[
    "validated_sentiment"
].tolist()

y_pred = df[
    "predicted_sentiment"
].tolist()


accuracy = accuracy_score(
    y_true,
    y_pred
)

precision, recall, f1, _ = (
    precision_recall_fscore_support(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0
    )
)


# ============================================================
# 15. DISPLAY RESULTS
# ============================================================

print("\n")
print("=" * 65)
print("HUMAN-VALIDATED RESULTS")
print("=" * 65)

print(
    f"Validated records : {len(df)}"
)

print(
    f"Accuracy          : {accuracy:.4f}"
)

print(
    f"Precision         : {precision:.4f}"
)

print(
    f"Recall            : {recall:.4f}"
)

print(
    f"F1 Score          : {f1:.4f}"
)


# ============================================================
# 16. CLASSIFICATION REPORT
# ============================================================

print("\n")
print("CLASSIFICATION REPORT")
print("=" * 65)

print(
    classification_report(
        y_true,
        y_pred,
        labels=[
            "negative",
            "neutral",
            "positive"
        ],
        zero_division=0
    )
)


# ============================================================
# 17. CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=[
        "positive",
        "neutral",
        "negative"
    ]
)

print("CONFUSION MATRIX")
print("=" * 65)

print(
    "                  Predicted"
)

print(
    "              Positive  Neutral  Negative"
)

print(
    f"Actual Positive "
    f"{cm[0][0]:>8} "
    f"{cm[0][1]:>8} "
    f"{cm[0][2]:>9}"
)

print(
    f"Actual Neutral  "
    f"{cm[1][0]:>8} "
    f"{cm[1][1]:>8} "
    f"{cm[1][2]:>9}"
)

print(
    f"Actual Negative "
    f"{cm[2][0]:>8} "
    f"{cm[2][1]:>8} "
    f"{cm[2][2]:>9}"
)


# ============================================================
# 18. SAVE PREDICTIONS
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n")
print("=" * 65)
print("PREDICTIONS SAVED")
print("=" * 65)

print(
    f"File: {OUTPUT_FILE}"
)


# ============================================================
# 19. FINAL MESSAGE
# ============================================================

print("\n")
print("=" * 65)
print("HUMAN VALIDATION EVALUATION COMPLETED")
print("=" * 65)

print(
    "\nThese results can be compared directly "
    "with the pretrained baseline because both "
    "use the same manually validated labels."
)