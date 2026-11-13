import os
import pandas as pd
import torch

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)


# ============================================================
# SMARTREVIEW AI
# CONFIDENCE RELIABILITY AUDIT
# ============================================================

print("=" * 70)
print("SMARTREVIEW AI - CONFIDENCE RELIABILITY AUDIT")
print("=" * 70)


# ============================================================
# PATHS
# ============================================================

AI_ENGINE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

DATASET_DIR = os.path.join(
    AI_ENGINE_DIR,
    "datasets"
)

MODELS_DIR = os.path.join(
    AI_ENGINE_DIR,
    "models"
)

PREDICTION_FILE = os.path.join(
    DATASET_DIR,
    "human_hybrid_test_predictions.csv"
)


# ============================================================
# DEVICE
# ============================================================

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print()
print("Device:", device)

if torch.cuda.is_available():

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )


# ============================================================
# FIND HYBRID MODEL AUTOMATICALLY
# ============================================================

print()
print("=" * 70)
print("SEARCHING FOR HYBRID MODEL")
print("=" * 70)

if not os.path.exists(MODELS_DIR):

    raise FileNotFoundError(
        f"\nModels directory not found:\n{MODELS_DIR}"
    )


print()
print("Models directory:")

print(MODELS_DIR)

print()
print("Available model folders:")


model_folders = []

for item in os.listdir(MODELS_DIR):

    full_path = os.path.join(
        MODELS_DIR,
        item
    )

    if os.path.isdir(full_path):

        print(
            " -",
            item
        )

        model_folders.append(item)


# ============================================================
# SELECT HYBRID MODEL
# ============================================================

hybrid_candidates = [

    folder
    for folder in model_folders
    if (
        "hybrid" in folder.lower()
        and
        folder.lower().startswith("roberta")
    )
]


if not hybrid_candidates:

    raise FileNotFoundError(
        "\nNo RoBERTa hybrid model folder was found.\n"
        "Check the model folders printed above."
    )


# Prefer exact expected name if available
if "roberta_absa_hybrid" in hybrid_candidates:

    selected_model_folder = (
        "roberta_absa_hybrid"
    )

else:

    selected_model_folder = (
        hybrid_candidates[0]
    )


MODEL_DIR = os.path.join(
    MODELS_DIR,
    selected_model_folder
)


print()
print("Selected hybrid model:")

print(MODEL_DIR)


# ============================================================
# CHECK PREDICTION FILE
# ============================================================

if not os.path.exists(PREDICTION_FILE):

    raise FileNotFoundError(
        f"\nHuman prediction file not found:\n"
        f"{PREDICTION_FILE}"
    )


# ============================================================
# LOAD HUMAN TEST PREDICTIONS
# ============================================================

print()
print("=" * 70)
print("LOADING HUMAN TEST PREDICTIONS")
print("=" * 70)

df = pd.read_csv(
    PREDICTION_FILE
)

print()
print(
    "Records:",
    len(df)
)

print()
print("Columns found:")

print(
    list(df.columns)
)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [
    "sentence",
    "aspect",
    "label",
    "predicted_label"
]

for column in required_columns:

    if column not in df.columns:

        raise ValueError(
            f"\nRequired column missing: {column}"
        )


# ============================================================
# LOAD TOKENIZER
# ============================================================

print()
print("=" * 70)
print("LOADING TOKENIZER")
print("=" * 70)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_DIR
)


# ============================================================
# LOAD MODEL
# ============================================================

print()
print("=" * 70)
print("LOADING HYBRID RoBERTa MODEL")
print("=" * 70)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_DIR
)

model.to(device)

model.eval()

print()
print("Model loaded successfully.")


# ============================================================
# LABEL MAPPING
# ============================================================

id2label = {
    0: "negative",
    1: "neutral",
    2: "positive"
}


# ============================================================
# PREDICTION FUNCTION
# ============================================================

def predict_with_confidence(
    sentence,
    aspect
):

    text = (
        f"Aspect: {aspect} "
        f"Sentence: {sentence}"
    )

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
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

    confidence, prediction = torch.max(
        probabilities,
        dim=-1
    )

    predicted_id = prediction.item()

    predicted_label = id2label.get(
        predicted_id,
        str(predicted_id)
    )

    confidence_value = (
        confidence.item()
    )

    return (
        predicted_label,
        confidence_value
    )


# ============================================================
# RUN CONFIDENCE AUDIT
# ============================================================

print()
print("=" * 70)
print("CALCULATING CONFIDENCE")
print("=" * 70)

predictions = []

confidences = []


for index, row in df.iterrows():

    sentence = str(
        row["sentence"]
    )

    aspect = str(
        row["aspect"]
    )

    predicted_label, confidence = (
        predict_with_confidence(
            sentence,
            aspect
        )
    )

    predictions.append(
        predicted_label
    )

    confidences.append(
        confidence
    )

    print(
        f"{index + 1:02d}/{len(df)} | "
        f"{aspect:<15} | "
        f"{predicted_label:<8} | "
        f"{confidence * 100:.2f}%"
    )


# ============================================================
# STORE RESULTS
# ============================================================

df["model_prediction"] = predictions

df["confidence"] = confidences

df["correct"] = (
    df["label"]
    .astype(str)
    .str.lower()
    .str.strip()
    ==
    df["model_prediction"]
    .astype(str)
    .str.lower()
    .str.strip()
)


# ============================================================
# ACCURACY
# ============================================================

accuracy = (
    df["correct"].mean()
)


# ============================================================
# CONFIDENCE STATISTICS
# ============================================================

average_confidence = (
    df["confidence"].mean()
)

correct_rows = df[
    df["correct"]
]

wrong_rows = df[
    ~df["correct"]
]


if len(correct_rows) > 0:

    correct_confidence = (
        correct_rows["confidence"].mean()
    )

else:

    correct_confidence = 0


if len(wrong_rows) > 0:

    wrong_confidence = (
        wrong_rows["confidence"].mean()
    )

else:

    wrong_confidence = 0


# ============================================================
# RESULTS
# ============================================================

print()
print("=" * 70)
print("CONFIDENCE ANALYSIS RESULTS")
print("=" * 70)

print()

print(
    f"Human test records       : {len(df)}"
)

print(
    f"Actual test accuracy     : "
    f"{accuracy * 100:.2f}%"
)

print(
    f"Average model confidence : "
    f"{average_confidence * 100:.2f}%"
)

print(
    f"Correct predictions avg  : "
    f"{correct_confidence * 100:.2f}%"
)

print(
    f"Wrong predictions avg    : "
    f"{wrong_confidence * 100:.2f}%"
)


# ============================================================
# CONFIDENCE BUCKETS
# ============================================================

print()
print("=" * 70)
print("CONFIDENCE VS ACTUAL CORRECTNESS")
print("=" * 70)


bins = [
    0.0,
    0.50,
    0.60,
    0.70,
    0.80,
    0.90,
    0.95,
    1.01
]

labels = [
    "0-50%",
    "50-60%",
    "60-70%",
    "70-80%",
    "80-90%",
    "90-95%",
    "95-100%"
]


df["confidence_range"] = pd.cut(
    df["confidence"],
    bins=bins,
    labels=labels,
    right=False
)


for bucket in labels:

    subset = df[
        df["confidence_range"] == bucket
    ]

    if len(subset) == 0:

        continue

    bucket_accuracy = (
        subset["correct"].mean()
    )

    bucket_confidence = (
        subset["confidence"].mean()
    )

    print()

    print(
        f"{bucket}"
    )

    print(
        f"  Records         : {len(subset)}"
    )

    print(
        f"  Avg confidence  : "
        f"{bucket_confidence * 100:.2f}%"
    )

    print(
        f"  Actual accuracy : "
        f"{bucket_accuracy * 100:.2f}%"
    )


# ============================================================
# HIGH-CONFIDENCE ERRORS
# ============================================================

high_confidence_wrong = df[
    (~df["correct"])
    &
    (df["confidence"] >= 0.90)
]


print()
print("=" * 70)
print("HIGH-CONFIDENCE WRONG PREDICTIONS")
print("=" * 70)

print()

print(
    "Wrong predictions >=90% confidence:",
    len(high_confidence_wrong)
)


for _, row in high_confidence_wrong.iterrows():

    print()

    print(
        "Aspect:",
        row["aspect"]
    )

    print(
        "Sentence:",
        row["sentence"]
    )

    print(
        "Actual:",
        row["label"]
    )

    print(
        "Predicted:",
        row["model_prediction"]
    )

    print(
        f"Confidence: "
        f"{row['confidence'] * 100:.2f}%"
    )

    print(
        "-" * 70
    )


# ============================================================
# SAVE AUDIT
# ============================================================

output_file = os.path.join(
    DATASET_DIR,
    "confidence_reliability_audit.csv"
)


df.to_csv(
    output_file,
    index=False
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("CONFIDENCE RELIABILITY AUDIT COMPLETE")
print("=" * 70)

print()

print(
    f"Actual model accuracy : "
    f"{accuracy * 100:.2f}%"
)

print(
    f"Average confidence    : "
    f"{average_confidence * 100:.2f}%"
)

print()

print(
    "Confidence is NOT model accuracy."
)

print(
    "Confidence represents how strongly "
    "the model selected its prediction."
)

print()

print(
    "Audit saved to:"
)

print(
    output_file
)

print()
print("=" * 70)