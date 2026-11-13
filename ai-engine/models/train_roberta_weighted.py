# ============================================================
# SMARTREVIEW AI
# CLASS-WEIGHTED RoBERTa - HUMAN SUPERVISED ABSA
# ============================================================

import os
import json
import random

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from datasets import Dataset

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)

from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42

MODEL_NAME = "roberta-base"

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "datasets",
    "human"
)

TRAIN_FILE = os.path.join(
    DATA_DIR,
    "human_train.csv"
)

VAL_FILE = os.path.join(
    DATA_DIR,
    "human_validation.csv"
)

TEST_FILE = os.path.join(
    DATA_DIR,
    "human_test.csv"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "models",
    "roberta_absa_weighted"
)

RESULTS_DIR = os.path.join(
    BASE_DIR,
    "datasets"
)

PREDICTION_FILE = os.path.join(
    RESULTS_DIR,
    "human_weighted_test_predictions.csv"
)

SUMMARY_FILE = os.path.join(
    RESULTS_DIR,
    "weighted_training_summary.json"
)


# ============================================================
# LABEL MAPPING
# ============================================================

LABEL2ID = {
    "negative": 0,
    "neutral": 1,
    "positive": 2
}

ID2LABEL = {
    0: "negative",
    1: "neutral",
    2: "positive"
}


# ============================================================
# RANDOM SEED
# ============================================================

random.seed(SEED)

np.random.seed(SEED)

torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


print()
print("=" * 70)
print("SMARTREVIEW AI - CLASS-WEIGHTED RoBERTa")
print("=" * 70)

print()

print(f"Device: {DEVICE}")

if torch.cuda.is_available():

    print(
        f"GPU: {torch.cuda.get_device_name(0)}"
    )

    print(
        f"GPU Memory: "
        f"{torch.cuda.get_device_properties(0).total_memory / (1024 ** 3):.2f} GB"
    )

else:

    print(
        "WARNING: CUDA is not available."
    )


# ============================================================
# CHECK DATASETS
# ============================================================

print()
print("=" * 70)
print("CHECKING DATASETS")
print("=" * 70)

for file_path in [
    TRAIN_FILE,
    VAL_FILE,
    TEST_FILE
]:

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            f"Dataset not found:\n{file_path}"
        )

    print(
        f"FOUND: {file_path}"
    )


# ============================================================
# LOAD DATASETS
# ============================================================

print()
print("Loading human datasets...")

train_df = pd.read_csv(
    TRAIN_FILE
)

val_df = pd.read_csv(
    VAL_FILE
)

test_df = pd.read_csv(
    TEST_FILE
)


print()
print("Dataset sizes:")

print(
    f"Training   : {len(train_df)}"
)

print(
    f"Validation : {len(val_df)}"
)

print(
    f"Test       : {len(test_df)}"
)


# ============================================================
# SHOW COLUMNS
# ============================================================

print()
print("Training columns:")

print(
    list(train_df.columns)
)

print()
print("Validation columns:")

print(
    list(val_df.columns)
)

print()
print("Test columns:")

print(
    list(test_df.columns)
)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_columns = [
    "sentence",
    "aspect",
    "label"
]


for column in required_columns:

    for df_name, df in [
        ("training", train_df),
        ("validation", val_df),
        ("test", test_df)
    ]:

        if column not in df.columns:

            raise ValueError(
                f"Column '{column}' missing "
                f"from {df_name} dataset.\n"
                f"Available columns: {list(df.columns)}"
            )


# ============================================================
# CLEAN DATA
# ============================================================

def clean_dataframe(df):

    df = df.copy()

    # Sentence
    df["sentence"] = (
        df["sentence"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Aspect
    df["aspect"] = (
        df["aspect"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # Label
    df["label"] = (
        df["label"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # Keep only valid labels
    valid_labels = {
        "negative",
        "neutral",
        "positive"
    }

    df = df[
        df["label"].isin(valid_labels)
    ]

    # Remove empty text
    df = df[
        (df["sentence"] != "") &
        (df["aspect"] != "")
    ]

    return df.reset_index(
        drop=True
    )


train_df = clean_dataframe(
    train_df
)

val_df = clean_dataframe(
    val_df
)

test_df = clean_dataframe(
    test_df
)


# ============================================================
# CONVERT LABELS TO IDs
# ============================================================

train_df["label_id"] = (
    train_df["label"]
    .map(LABEL2ID)
)

val_df["label_id"] = (
    val_df["label"]
    .map(LABEL2ID)
)

test_df["label_id"] = (
    test_df["label"]
    .map(LABEL2ID)
)


# ============================================================
# DISPLAY CLASS DISTRIBUTION
# ============================================================

print()
print("=" * 70)
print("CLASS DISTRIBUTION")
print("=" * 70)

print()

print("Training:")

print(
    train_df["label"].value_counts()
)

print()

print("Validation:")

print(
    val_df["label"].value_counts()
)

print()

print("Test:")

print(
    test_df["label"].value_counts()
)


# ============================================================
# CALCULATE CLASS WEIGHTS
# ============================================================

print()
print("=" * 70)
print("CALCULATING CLASS WEIGHTS")
print("=" * 70)


class_counts = (
    train_df["label_id"]
    .value_counts()
    .sort_index()
)

total_samples = len(
    train_df
)

num_classes = 3

class_weights = []


for class_id in range(
    num_classes
):

    count = class_counts.get(
        class_id,
        0
    )

    if count == 0:

        weight = 1.0

    else:

        weight = (
            total_samples
            /
            (num_classes * count)
        )

    class_weights.append(
        weight
    )


class_weights = torch.tensor(
    class_weights,
    dtype=torch.float
)


print()

for class_id in range(
    num_classes
):

    print(
        f"{ID2LABEL[class_id]:8s} "
        f"count={class_counts.get(class_id, 0):3d} "
        f"weight={class_weights[class_id].item():.4f}"
    )


# ============================================================
# CONVERT TO HUGGINGFACE DATASETS
# ============================================================

print()
print("Converting datasets...")


train_dataset = Dataset.from_pandas(
    train_df[
        [
            "sentence",
            "aspect",
            "label_id"
        ]
    ],
    preserve_index=False
)


val_dataset = Dataset.from_pandas(
    val_df[
        [
            "sentence",
            "aspect",
            "label_id"
        ]
    ],
    preserve_index=False
)


test_dataset = Dataset.from_pandas(
    test_df[
        [
            "sentence",
            "aspect",
            "label_id"
        ]
    ],
    preserve_index=False
)


# ============================================================
# RENAME LABEL COLUMN
# ============================================================

train_dataset = train_dataset.rename_column(
    "label_id",
    "labels"
)

val_dataset = val_dataset.rename_column(
    "label_id",
    "labels"
)

test_dataset = test_dataset.rename_column(
    "label_id",
    "labels"
)


# ============================================================
# LOAD TOKENIZER
# ============================================================

print()
print("Loading RoBERTa tokenizer...")


tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)


# ============================================================
# TOKENIZATION
# ============================================================

def tokenize_function(
    examples
):

    return tokenizer(
        examples["sentence"],
        examples["aspect"],
        truncation=True,
        padding="max_length",
        max_length=128
    )


print()
print("Tokenizing datasets...")


train_dataset = train_dataset.map(
    tokenize_function,
    batched=True,
    desc="Training tokenization"
)


val_dataset = val_dataset.map(
    tokenize_function,
    batched=True,
    desc="Validation tokenization"
)


test_dataset = test_dataset.map(
    tokenize_function,
    batched=True,
    desc="Test tokenization"
)


# ============================================================
# DATASET FORMAT
# ============================================================

columns = [
    "input_ids",
    "attention_mask",
    "labels"
]


if "token_type_ids" in train_dataset.column_names:

    columns.append(
        "token_type_ids"
    )


train_dataset.set_format(
    type="torch",
    columns=columns
)

val_dataset.set_format(
    type="torch",
    columns=columns
)

test_dataset.set_format(
    type="torch",
    columns=columns
)


# ============================================================
# LOAD RoBERTa
# ============================================================

print()
print("=" * 70)
print("LOADING RoBERTa MODEL")
print("=" * 70)


model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3,
    id2label=ID2LABEL,
    label2id=LABEL2ID
)


model.to(
    DEVICE
)


# ============================================================
# CUSTOM WEIGHTED TRAINER
# ============================================================

class WeightedTrainer(
    Trainer
):

    def compute_loss(
        self,
        model,
        inputs,
        return_outputs=False,
        num_items_in_batch=None
    ):

        labels = inputs.pop(
            "labels"
        )

        outputs = model(
            **inputs
        )

        logits = outputs.logits

        weights = class_weights.to(
            logits.device
        )

        loss_function = nn.CrossEntropyLoss(
            weight=weights
        )

        loss = loss_function(
            logits,
            labels
        )

        if return_outputs:

            return (
                loss,
                outputs
            )

        return loss


# ============================================================
# METRICS
# ============================================================

def compute_metrics(
    eval_prediction
):

    predictions = (
        eval_prediction.predictions
    )

    labels = (
        eval_prediction.label_ids
    )

    predicted_labels = np.argmax(
        predictions,
        axis=1
    )

    accuracy = accuracy_score(
        labels,
        predicted_labels
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            labels,
            predicted_labels,
            average="macro",
            zero_division=0
        )
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "macro_f1": f1
    }


# ============================================================
# TRAINING ARGUMENTS
# ============================================================

print()
print("=" * 70)
print("SETTING TRAINING PARAMETERS")
print("=" * 70)


training_args = TrainingArguments(

    output_dir=OUTPUT_DIR,

    num_train_epochs=5,

    per_device_train_batch_size=8,

    per_device_eval_batch_size=8,

    learning_rate=2e-5,

    weight_decay=0.01,

    # IMPORTANT:
    # warmup_ratio intentionally removed.

    eval_strategy="epoch",

    save_strategy="epoch",

    save_total_limit=2,

    load_best_model_at_end=True,

    metric_for_best_model="macro_f1",

    greater_is_better=True,

    logging_strategy="steps",

    logging_steps=5,

    fp16=torch.cuda.is_available(),

    report_to="none",

    seed=SEED
)


# ============================================================
# TRAINER
# ============================================================

trainer = WeightedTrainer(

    model=model,

    args=training_args,

    train_dataset=train_dataset,

    eval_dataset=val_dataset,

    processing_class=tokenizer,

    compute_metrics=compute_metrics,

    callbacks=[
        EarlyStoppingCallback(
            early_stopping_patience=2
        )
    ]
)


# ============================================================
# TRAIN
# ============================================================

print()
print("=" * 70)
print("STARTING CLASS-WEIGHTED RoBERTa TRAINING")
print("=" * 70)

print()

print(
    "Class weighting:"
)

print(
    f"Negative = {class_weights[0].item():.4f}"
)

print(
    f"Neutral  = {class_weights[1].item():.4f}"
)

print(
    f"Positive = {class_weights[2].item():.4f}"
)

print()


trainer.train()


# ============================================================
# VALIDATION
# ============================================================

print()
print("=" * 70)
print("FINAL VALIDATION RESULTS")
print("=" * 70)


validation_results = trainer.evaluate(
    eval_dataset=val_dataset
)


for key, value in validation_results.items():

    if isinstance(
        value,
        (float, np.floating)
    ):

        print(
            f"{key:25s}: {value:.4f}"
        )

    else:

        print(
            f"{key:25s}: {value}"
        )


# ============================================================
# TEST
# ============================================================

print()
print("=" * 70)
print("FINAL HUMAN TEST RESULTS")
print("=" * 70)


test_results = trainer.evaluate(
    eval_dataset=test_dataset
)


for key, value in test_results.items():

    if isinstance(
        value,
        (float, np.floating)
    ):

        print(
            f"{key:25s}: {value:.4f}"
        )

    else:

        print(
            f"{key:25s}: {value}"
        )


# ============================================================
# PREDICTIONS
# ============================================================

print()
print("=" * 70)
print("GENERATING TEST PREDICTIONS")
print("=" * 70)


prediction_output = trainer.predict(
    test_dataset
)


logits = (
    prediction_output.predictions
)


predicted_ids = np.argmax(
    logits,
    axis=1
)


predicted_labels = [
    ID2LABEL[int(i)]
    for i in predicted_ids
]


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

true_labels = (
    test_df["label_id"].values
)


print()
print("=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print()


print(
    classification_report(
        true_labels,
        predicted_ids,
        target_names=[
            "negative",
            "neutral",
            "positive"
        ],
        zero_division=0
    )
)


# ============================================================
# CONFUSION MATRIX
# ============================================================

print()
print("=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)


cm = confusion_matrix(
    true_labels,
    predicted_ids,
    labels=[0, 1, 2]
)


print()

print(
    "                 Predicted"
)

print(
    "              Neg   Neu   Pos"
)

print(
    f"Actual Neg   "
    f"{cm[0][0]:3d}   "
    f"{cm[0][1]:3d}   "
    f"{cm[0][2]:3d}"
)

print(
    f"Actual Neu   "
    f"{cm[1][0]:3d}   "
    f"{cm[1][1]:3d}   "
    f"{cm[1][2]:3d}"
)

print(
    f"Actual Pos   "
    f"{cm[2][0]:3d}   "
    f"{cm[2][1]:3d}   "
    f"{cm[2][2]:3d}"
)


# ============================================================
# SAVE PREDICTIONS
# ============================================================

prediction_df = test_df.copy()


prediction_df[
    "predicted_sentiment"
] = predicted_labels


prediction_df[
    "correct"
] = (
    prediction_df["label"]
    ==
    prediction_df["predicted_sentiment"]
)


# Confidence

probabilities = torch.softmax(
    torch.tensor(logits),
    dim=1
).numpy()


prediction_df[
    "confidence"
] = probabilities.max(
    axis=1
)


prediction_df.to_csv(
    PREDICTION_FILE,
    index=False
)


# ============================================================
# SAVE MODEL
# ============================================================

print()
print("=" * 70)
print("SAVING WEIGHTED MODEL")
print("=" * 70)


trainer.save_model(
    OUTPUT_DIR
)


tokenizer.save_pretrained(
    OUTPUT_DIR
)


print()

print(
    f"Model saved to:\n{OUTPUT_DIR}"
)

print()

print(
    f"Predictions saved to:\n{PREDICTION_FILE}"
)


# ============================================================
# SAVE EXPERIMENT SUMMARY
# ============================================================

summary = {

    "experiment":
        "Class-Weighted RoBERTa",

    "model":
        MODEL_NAME,

    "seed":
        SEED,

    "training_records":
        len(train_df),

    "validation_records":
        len(val_df),

    "test_records":
        len(test_df),

    "class_distribution": {

        "negative":
            int(
                (train_df["label"] == "negative")
                .sum()
            ),

        "neutral":
            int(
                (train_df["label"] == "neutral")
                .sum()
            ),

        "positive":
            int(
                (train_df["label"] == "positive")
                .sum()
            )
    },

    "class_weights": {

        ID2LABEL[i]:
            float(
                class_weights[i].item()
            )

        for i in range(3)
    },

    "validation_results": {

        key:
            float(value)

        for key, value
        in validation_results.items()

        if isinstance(
            value,
            (float, np.floating)
        )
    },

    "test_results": {

        key:
            float(value)

        for key, value
        in test_results.items()

        if isinstance(
            value,
            (float, np.floating)
        )
    }
}


with open(
    SUMMARY_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        summary,
        f,
        indent=4
    )


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("CLASS-WEIGHTED RoBERTa TRAINING COMPLETE")
print("=" * 70)

print()

print(
    f"Validation Macro F1: "
    f"{validation_results.get('eval_macro_f1', 0):.4f}"
)

print(
    f"Test Accuracy: "
    f"{test_results.get('eval_accuracy', 0):.4f}"
)

print(
    f"Test Macro F1: "
    f"{test_results.get('eval_macro_f1', 0):.4f}"
)

print()

print(
    "Experiment completed successfully."
)