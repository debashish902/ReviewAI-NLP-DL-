import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)


INPUT_FILE = "ai-engine/datasets/validation_dataset.csv"


print("Loading validation dataset...")

df = pd.read_csv(INPUT_FILE)


# Remove rows that have not been manually validated
df["validated_sentiment"] = (
    df["validated_sentiment"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)

df["aspect_sentiment"] = (
    df["aspect_sentiment"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)


df = df[
    df["validated_sentiment"].isin(
        ["positive", "neutral", "negative"]
    )
]


print("\n========== BASELINE EVALUATION ==========")

print("Validated records:", len(df))


if len(df) == 0:

    print("No validated records found.")
    exit()


# Actual ground truth
y_true = df["validated_sentiment"]


# RoBERTa predictions
y_pred = df["aspect_sentiment"]


# -----------------------------------------
# Metrics
# -----------------------------------------

accuracy = accuracy_score(
    y_true,
    y_pred
)

precision = precision_score(
    y_true,
    y_pred,
    average="weighted",
    zero_division=0
)

recall = recall_score(
    y_true,
    y_pred,
    average="weighted",
    zero_division=0
)

f1 = f1_score(
    y_true,
    y_pred,
    average="weighted",
    zero_division=0
)


print("\nPerformance Metrics:")

print(
    f"Accuracy  : {accuracy:.4f}"
)

print(
    f"Precision : {precision:.4f}"
)

print(
    f"Recall    : {recall:.4f}"
)

print(
    f"F1 Score  : {f1:.4f}"
)


# -----------------------------------------
# Detailed classification report
# -----------------------------------------

print("\nClassification Report:\n")

print(
    classification_report(
        y_true,
        y_pred,
        labels=[
            "positive",
            "neutral",
            "negative"
        ],
        zero_division=0
    )
)


# -----------------------------------------
# Confusion Matrix
# -----------------------------------------

labels = [
    "positive",
    "neutral",
    "negative"
]

cm = confusion_matrix(
    y_true,
    y_pred,
    labels=labels
)


print("\nConfusion Matrix:")

print(
    "                Predicted"
)

print(
    "              Pos  Neu  Neg"
)

for label, row in zip(labels, cm):

    print(
        f"Actual {label[:3]:3}   "
        f"{row[0]:3}  "
        f"{row[1]:3}  "
        f"{row[2]:3}"
    )


# -----------------------------------------
# Show disagreements
# -----------------------------------------

df["correct"] = (
    df["aspect_sentiment"]
    ==
    df["validated_sentiment"]
)


disagreements = df[
    df["correct"] == False
]


print(
    "\nTotal disagreements:",
    len(disagreements)
)


if len(disagreements) > 0:

    print("\nExamples of disagreements:\n")

    print(
        disagreements[
            [
                "sentence",
                "aspect",
                "aspect_sentiment",
                "validated_sentiment"
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


print(
    "\n=========================================="
)