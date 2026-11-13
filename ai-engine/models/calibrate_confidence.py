import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from torch.nn import functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import accuracy_score, log_loss


# ============================================================
# SMARTREVIEW AI
# EXPERIMENT 5: CONFIDENCE CALIBRATION
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# PATH CONFIGURATION
# ============================================================

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

AI_DIR = ROOT_DIR / "ai-engine"
DATA_DIR = AI_DIR / "datasets"
HUMAN_DIR = DATA_DIR / "human"

# Previous model (Experiment 4):
# MODEL_DIR = AI_DIR / "models" / "roberta_absa_hybrid"

MODEL_DIR = AI_DIR / "models" / "roberta_absa_improved"

VALIDATION_FILE = HUMAN_DIR / "human_validation.csv"
TEST_FILE = HUMAN_DIR / "human_test.csv"

OUTPUT_FILE = DATA_DIR / "calibrated_predictions.csv"
CONFIG_FILE = DATA_DIR / "calibration_config.json"


# ============================================================
# MODEL CONFIGURATION
# ============================================================

MAX_LENGTH = 128

LABELS = [
    "negative",
    "neutral",
    "positive"
]

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# LOAD DATASET
# ============================================================

def load_dataset(file_path, dataset_name):

    print(f"\nLoading {dataset_name} dataset...")
    print(f"File: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(
            f"{dataset_name} dataset not found:\n{file_path}"
        )

    df = pd.read_csv(file_path)

    required_columns = [
        "sentence",
        "aspect",
        "label"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns in {dataset_name} dataset: "
            f"{missing_columns}\n"
            f"Available columns: {list(df.columns)}"
        )

    df = df.dropna(
        subset=required_columns
    ).copy()

    df["sentence"] = df["sentence"].astype(str).str.strip()
    df["aspect"] = df["aspect"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip().str.lower()

    df = df[
        df["sentence"].ne("")
        & df["aspect"].ne("")
        & df["label"].isin(LABELS)
    ].reset_index(drop=True)

    if df.empty:
        raise ValueError(
            f"No valid records found in {dataset_name} dataset."
        )

    df["label_id"] = df["label"].map(
        {
            "negative": 0,
            "neutral": 1,
            "positive": 2
        }
    )

    print(f"Valid records: {len(df)}")
    print("\nLabel distribution:")
    print(df["label"].value_counts())

    return df


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    print("\n" + "=" * 65)
    print("LOADING HYBRID RoBERTa MODEL")
    print("=" * 65)

    if not MODEL_DIR.exists():
        raise FileNotFoundError(
            f"Model directory not found:\n{MODEL_DIR}"
        )

    tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_DIR)
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_DIR)
    )

    model.to(DEVICE)
    model.eval()

    print(f"Device: {DEVICE}")

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    print(f"Model: {MODEL_DIR}")
    print("Model loaded successfully.")

    return tokenizer, model


# ============================================================
# GENERATE LOGITS
# IMPORTANT:
# Uses the sentence + aspect pair format used in training.
# ============================================================

def get_logits(df, tokenizer, model):

    all_logits = []

    print("\nGenerating predictions...")

    for index, row in df.iterrows():

        sentence = str(row["sentence"]).strip()
        aspect = str(row["aspect"]).strip()

        # Match the training input format.
        inputs = tokenizer(
            sentence,
            aspect,
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )

        inputs = {
            key: value.to(DEVICE)
            for key, value in inputs.items()
        }

        with torch.no_grad():

            outputs = model(
                **inputs
            )

        logits = (
            outputs.logits[0]
            .detach()
            .cpu()
        )

        all_logits.append(logits)

        if (index + 1) % 10 == 0 or index + 1 == len(df):
            print(
                f"Processed {index + 1}/{len(df)}",
                end="\r"
            )

    print()

    return torch.stack(all_logits)


# ============================================================
# TEMPERATURE SCALING
# ============================================================

def optimize_temperature(validation_logits, validation_labels):

    print("\n" + "=" * 65)
    print("OPTIMIZING TEMPERATURE")
    print("=" * 65)

    # Optimize log-temperature to ensure positive temperature.
    log_temperature = torch.nn.Parameter(
        torch.zeros(1)
    )

    optimizer = torch.optim.LBFGS(
        [log_temperature],
        lr=0.01,
        max_iter=100
    )

    def closure():

        optimizer.zero_grad()

        temperature = torch.exp(
            log_temperature
        ).clamp(min=0.05, max=20.0)

        loss = F.cross_entropy(
            validation_logits / temperature,
            validation_labels
        )

        loss.backward()

        return loss

    optimizer.step(closure)

    temperature = torch.exp(
        log_temperature.detach()
    ).clamp(min=0.05, max=20.0).item()

    print(f"Optimal temperature: {temperature:.4f}")

    return temperature


# ============================================================
# EXPECTED CALIBRATION ERROR
# ============================================================

def calculate_ece(probabilities, labels, bins=10):

    confidences, predictions = probabilities.max(dim=1)

    accuracies = predictions.eq(labels)

    ece = torch.tensor(0.0)

    bin_boundaries = torch.linspace(
        0.0,
        1.0,
        bins + 1
    )

    for index in range(bins):

        lower = bin_boundaries[index]
        upper = bin_boundaries[index + 1]

        if index == 0:

            mask = (
                (confidences >= lower)
                & (confidences <= upper)
            )

        else:

            mask = (
                (confidences > lower)
                & (confidences <= upper)
            )

        if mask.any():

            bin_accuracy = accuracies[mask].float().mean()
            bin_confidence = confidences[mask].mean()

            ece += (
                mask.float().mean()
                * torch.abs(
                    bin_accuracy - bin_confidence
                )
            )

    return ece.item()


# ============================================================
# EVALUATION
# ============================================================

def evaluate_predictions(logits, labels, temperature):

    raw_probabilities = torch.softmax(
        logits,
        dim=1
    )

    calibrated_probabilities = torch.softmax(
        logits / temperature,
        dim=1
    )

    predictions = raw_probabilities.argmax(
        dim=1
    )

    calibrated_predictions = calibrated_probabilities.argmax(
        dim=1
    )

    accuracy_before = accuracy_score(
        labels.numpy(),
        predictions.numpy()
    )

    accuracy_after = accuracy_score(
        labels.numpy(),
        calibrated_predictions.numpy()
    )

    loss_before = log_loss(
        labels.numpy(),
        raw_probabilities.numpy(),
        labels=[0, 1, 2]
    )

    loss_after = log_loss(
        labels.numpy(),
        calibrated_probabilities.numpy(),
        labels=[0, 1, 2]
    )

    ece_before = calculate_ece(
        raw_probabilities,
        labels
    )

    ece_after = calculate_ece(
        calibrated_probabilities,
        labels
    )

    return {
        "probabilities_before": raw_probabilities,
        "probabilities_after": calibrated_probabilities,
        "predictions": predictions,
        "calibrated_predictions": calibrated_predictions,
        "accuracy_before": accuracy_before,
        "accuracy_after": accuracy_after,
        "log_loss_before": loss_before,
        "log_loss_after": loss_after,
        "ece_before": ece_before,
        "ece_after": ece_after
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("SMARTREVIEW AI - CONFIDENCE CALIBRATION")
    print("=" * 65)

    print(f"\nDevice: {DEVICE}")

    # Load separate human-labelled datasets.
    validation_df = load_dataset(
        VALIDATION_FILE,
        "VALIDATION"
    )

    test_df = load_dataset(
        TEST_FILE,
        "TEST"
    )

    # Prevent accidental overlap between validation and test.
    validation_keys = set(
        zip(
            validation_df["sentence"],
            validation_df["aspect"]
        )
    )

    test_keys = set(
        zip(
            test_df["sentence"],
            test_df["aspect"]
        )
    )

    overlap = validation_keys.intersection(
        test_keys
    )

    if overlap:
        raise ValueError(
            f"Found {len(overlap)} overlapping sentence-aspect "
            "pairs between validation and test datasets. "
            "Resolve the overlap before reporting final results."
        )

    tokenizer, model = load_model()

    # Generate logits using the training input format.
    validation_logits = get_logits(
        validation_df,
        tokenizer,
        model
    )

    test_logits = get_logits(
        test_df,
        tokenizer,
        model
    )

    validation_labels = torch.tensor(
        validation_df["label_id"].tolist(),
        dtype=torch.long
    )

    test_labels = torch.tensor(
        test_df["label_id"].tolist(),
        dtype=torch.long
    )

    print("\nValidation logits:", validation_logits.shape)
    print("Test logits:", test_logits.shape)

    # Check model output dimension.
    if validation_logits.shape[1] != len(LABELS):
        raise ValueError(
            f"Expected {len(LABELS)} output classes, "
            f"but model returned {validation_logits.shape[1]}."
        )

    # Calibrate using validation data only.
    temperature = optimize_temperature(
        validation_logits,
        validation_labels
    )

    validation_results = evaluate_predictions(
        validation_logits,
        validation_labels,
        temperature
    )

    test_results = evaluate_predictions(
        test_logits,
        test_labels,
        temperature
    )

    # --------------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("VALIDATION RESULTS")
    print("=" * 65)

    print(
        f"Accuracy before calibration: "
        f"{validation_results['accuracy_before']:.4f}"
    )

    print(
        f"Accuracy after calibration : "
        f"{validation_results['accuracy_after']:.4f}"
    )

    print(
        f"Log loss before calibration: "
        f"{validation_results['log_loss_before']:.4f}"
    )

    print(
        f"Log loss after calibration : "
        f"{validation_results['log_loss_after']:.4f}"
    )

    print(
        f"ECE before calibration     : "
        f"{validation_results['ece_before']:.4f}"
    )

    print(
        f"ECE after calibration      : "
        f"{validation_results['ece_after']:.4f}"
    )

    print("\n" + "=" * 65)
    print("HELD-OUT TEST RESULTS")
    print("=" * 65)

    print(
        f"Test accuracy before calibration: "
        f"{test_results['accuracy_before']:.4f}"
    )

    print(
        f"Test accuracy after calibration : "
        f"{test_results['accuracy_after']:.4f}"
    )

    print(
        f"Test log loss before calibration: "
        f"{test_results['log_loss_before']:.4f}"
    )

    print(
        f"Test log loss after calibration : "
        f"{test_results['log_loss_after']:.4f}"
    )

    print(
        f"Test ECE before calibration     : "
        f"{test_results['ece_before']:.4f}"
    )

    print(
        f"Test ECE after calibration      : "
        f"{test_results['ece_after']:.4f}"
    )

    print("\nIMPORTANT:")
    print(
        "Temperature scaling adjusts confidence probabilities."
    )
    print(
        "It does not normally change the predicted class."
    )
    print(
        "Confidence is not the same as model accuracy."
    )

    # --------------------------------------------------------
    # SAVE TEST PREDICTIONS
    # --------------------------------------------------------

    calibrated_probabilities = (
        test_results["probabilities_after"].numpy()
    )

    raw_probabilities = (
        test_results["probabilities_before"].numpy()
    )

    predictions_df = test_df[
        ["sentence", "aspect", "label"]
    ].copy()

    predictions_df["predicted_label"] = [
        LABELS[index]
        for index in test_results["predictions"].tolist()
    ]

    predictions_df["calibrated_predicted_label"] = [
        LABELS[index]
        for index in test_results["calibrated_predictions"].tolist()
    ]

    predictions_df["confidence_before"] = (
        raw_probabilities.max(axis=1)
    )

    predictions_df["confidence_after"] = (
        calibrated_probabilities.max(axis=1)
    )

    for index, label in enumerate(LABELS):

        predictions_df[
            f"{label}_probability_before"
        ] = raw_probabilities[:, index]

        predictions_df[
            f"{label}_probability_after"
        ] = calibrated_probabilities[:, index]

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    predictions_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # SAVE CALIBRATION CONFIGURATION
    # --------------------------------------------------------

    config = {
        "experiment": "SmartReview AI Confidence Calibration",
        "model_directory": str(MODEL_DIR),
        "temperature": temperature,
        "labels": LABELS,
        "max_length": MAX_LENGTH,
        "input_format": "tokenizer(sentence, aspect)",
        "validation_records": len(validation_df),
        "test_records": len(test_df),
        "validation_accuracy_before": validation_results["accuracy_before"],
        "validation_accuracy_after": validation_results["accuracy_after"],
        "validation_log_loss_before": validation_results["log_loss_before"],
        "validation_log_loss_after": validation_results["log_loss_after"],
        "validation_ece_before": validation_results["ece_before"],
        "validation_ece_after": validation_results["ece_after"],
        "test_accuracy_before": test_results["accuracy_before"],
        "test_accuracy_after": test_results["accuracy_after"],
        "test_log_loss_before": test_results["log_loss_before"],
        "test_log_loss_after": test_results["log_loss_after"],
        "test_ece_before": test_results["ece_before"],
        "test_ece_after": test_results["ece_after"]
    }

    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            config,
            file,
            indent=4
        )

    print("\n" + "=" * 65)
    print("CONFIDENCE CALIBRATION COMPLETED")
    print("=" * 65)

    print(f"\nPredictions saved to:\n{OUTPUT_FILE}")
    print(f"\nCalibration configuration saved to:\n{CONFIG_FILE}")


if __name__ == "__main__":
    main()