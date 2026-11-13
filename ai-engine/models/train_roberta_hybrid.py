import os
import random
import numpy as np
import pandas as pd
import torch

from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)


# ============================================================
# SMARTREVIEW AI
# EXPERIMENT 4 - HYBRID HUMAN + PSEUDO-LABELED RoBERTa
# ============================================================

print("=" * 70)
print("SMARTREVIEW AI - EXPERIMENT 4")
print("HYBRID HUMAN + PSEUDO-LABELED RoBERTa TRAINING")
print("=" * 70)


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42

MODEL_NAME = "roberta-base"

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

DATASET_DIR = os.path.join(
    BASE_DIR,
    "ai-engine",
    "datasets"
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "ai-engine",
    "models",
    "roberta_absa_hybrid"
)

HYBRID_FILE = os.path.join(
    DATASET_DIR,
    "hybrid_train.csv"
)

VALIDATION_FILE = os.path.join(
    DATASET_DIR,
    "human",
    "human_validation.csv"
)

TEST_FILE = os.path.join(
    DATASET_DIR,
    "human",
    "human_test.csv"
)


# Training parameters
MAX_LENGTH = 128
BATCH_SIZE = 8
EPOCHS = 5
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 0.01

PATIENCE = 2

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
# REPRODUCIBILITY
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
    "cuda" if torch.cuda.is_available() else "cpu"
)

print()
print("DEVICE INFORMATION")
print("-" * 70)

print("Device:", DEVICE)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print(
        "GPU Memory:",
        round(
            torch.cuda.get_device_properties(0).total_memory
            / (1024 ** 3),
            2
        ),
        "GB"
    )

else:
    print("WARNING: CUDA is not available. Training will use CPU.")


# ============================================================
# CHECK FILES
# ============================================================

print()
print("CHECKING DATASETS")
print("-" * 70)

for file_path in [
    HYBRID_FILE,
    VALIDATION_FILE,
    TEST_FILE
]:

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            f"Required file not found:\n{file_path}"
        )

    print("FOUND:", file_path)


# ============================================================
# LOAD DATA
# ============================================================

print()
print("LOADING DATASETS")
print("-" * 70)

train_df = pd.read_csv(HYBRID_FILE)
val_df = pd.read_csv(VALIDATION_FILE)
test_df = pd.read_csv(TEST_FILE)


print()
print("DATASET SIZES")
print("-" * 70)

print("Training:", len(train_df))
print("Validation:", len(val_df))
print("Test:", len(test_df))


# ============================================================
# VALIDATE COLUMNS
# ============================================================

required_train_columns = [
    "sentence",
    "aspect",
    "label",
    "sample_weight"
]

required_eval_columns = [
    "sentence",
    "aspect",
    "label"
]


for column in required_train_columns:

    if column not in train_df.columns:

        raise ValueError(
            f"Column '{column}' missing from hybrid training dataset."
        )


for column in required_eval_columns:

    if column not in val_df.columns:

        raise ValueError(
            f"Column '{column}' missing from validation dataset."
        )

    if column not in test_df.columns:

        raise ValueError(
            f"Column '{column}' missing from test dataset."
        )


# ============================================================
# CLEAN DATA
# ============================================================

train_df = train_df.dropna(
    subset=[
        "sentence",
        "aspect",
        "label",
        "sample_weight"
    ]
).copy()

val_df = val_df.dropna(
    subset=[
        "sentence",
        "aspect",
        "label"
    ]
).copy()

test_df = test_df.dropna(
    subset=[
        "sentence",
        "aspect",
        "label"
    ]
).copy()


# Convert text fields to string
train_df["sentence"] = train_df["sentence"].astype(str)
train_df["aspect"] = train_df["aspect"].astype(str)

val_df["sentence"] = val_df["sentence"].astype(str)
val_df["aspect"] = val_df["aspect"].astype(str)

test_df["sentence"] = test_df["sentence"].astype(str)
test_df["aspect"] = test_df["aspect"].astype(str)


# Normalize labels
train_df["label"] = train_df["label"].astype(str).str.lower()
val_df["label"] = val_df["label"].astype(str).str.lower()
test_df["label"] = test_df["label"].astype(str).str.lower()


# Remove unexpected labels
train_df = train_df[
    train_df["label"].isin(LABEL2ID.keys())
].copy()

val_df = val_df[
    val_df["label"].isin(LABEL2ID.keys())
].copy()

test_df = test_df[
    test_df["label"].isin(LABEL2ID.keys())
].copy()


# Convert sample weights
train_df["sample_weight"] = pd.to_numeric(
    train_df["sample_weight"],
    errors="coerce"
)

train_df = train_df.dropna(
    subset=["sample_weight"]
).copy()


# ============================================================
# DATASET STATISTICS
# ============================================================

print()
print("HYBRID TRAINING DISTRIBUTION")
print("-" * 70)

print(
    train_df["label"].value_counts()
)

print()
print("SOURCE DISTRIBUTION")

if "source" in train_df.columns:
    print(
        train_df["source"].value_counts()
    )

print()
print("SAMPLE WEIGHT DISTRIBUTION")

print(
    train_df["sample_weight"].value_counts()
)


# ============================================================
# LABEL ENCODING
# ============================================================

train_df["label_id"] = train_df["label"].map(LABEL2ID)
val_df["label_id"] = val_df["label"].map(LABEL2ID)
test_df["label_id"] = test_df["label"].map(LABEL2ID)


# ============================================================
# CUSTOM DATASET
# ============================================================

class ABSADataset(Dataset):

    def __init__(
        self,
        dataframe,
        tokenizer,
        include_weight=False
    ):

        self.data = dataframe.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.include_weight = include_weight

    def __len__(self):

        return len(self.data)

    def __getitem__(self, index):

        row = self.data.iloc[index]

        sentence = str(row["sentence"])
        aspect = str(row["aspect"])

        encoding = self.tokenizer(
            sentence,
            aspect,
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )

        item = {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": torch.tensor(
                int(row["label_id"]),
                dtype=torch.long
            )
        }

        if "token_type_ids" in encoding:

            item["token_type_ids"] = (
                encoding["token_type_ids"].squeeze(0)
            )

        if self.include_weight:

            item["sample_weight"] = torch.tensor(
                float(row["sample_weight"]),
                dtype=torch.float
            )

        return item


# ============================================================
# LOAD TOKENIZER
# ============================================================

print()
print("LOADING RoBERTa TOKENIZER")
print("-" * 70)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

print("Tokenizer loaded successfully.")


# ============================================================
# CREATE DATASETS
# ============================================================

train_dataset = ABSADataset(
    train_df,
    tokenizer,
    include_weight=True
)

val_dataset = ABSADataset(
    val_df,
    tokenizer,
    include_weight=False
)

test_dataset = ABSADataset(
    test_df,
    tokenizer,
    include_weight=False
)


# ============================================================
# CREATE DATALOADERS
# ============================================================

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)


# ============================================================
# LOAD MODEL
# ============================================================

print()
print("LOADING RoBERTa MODEL")
print("-" * 70)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3,
    id2label=ID2LABEL,
    label2id=LABEL2ID
)

model.to(DEVICE)

print("Model loaded successfully.")


# ============================================================
# OPTIMIZER
# ============================================================

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY
)


# ============================================================
# LEARNING RATE SCHEDULER
# ============================================================

total_training_steps = (
    len(train_loader) * EPOCHS
)

scheduler = torch.optim.lr_scheduler.LinearLR(
    optimizer,
    start_factor=1.0,
    end_factor=0.1,
    total_iters=total_training_steps
)


# ============================================================
# EVALUATION FUNCTION
# ============================================================

def evaluate(model, dataloader):

    model.eval()

    all_predictions = []
    all_labels = []

    total_loss = 0.0
    total_samples = 0

    criterion = torch.nn.CrossEntropyLoss(
        reduction="sum"
    )

    with torch.no_grad():

        for batch in dataloader:

            input_ids = batch["input_ids"].to(DEVICE)
            attention_mask = batch["attention_mask"].to(DEVICE)
            labels = batch["labels"].to(DEVICE)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            logits = outputs.logits

            loss = criterion(
                logits,
                labels
            )

            batch_size = labels.size(0)

            total_loss += loss.item()
            total_samples += batch_size

            predictions = torch.argmax(
                logits,
                dim=1
            )

            all_predictions.extend(
                predictions.cpu().numpy()
            )

            all_labels.extend(
                labels.cpu().numpy()
            )

    avg_loss = total_loss / total_samples

    accuracy = accuracy_score(
        all_labels,
        all_predictions
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            all_labels,
            all_predictions,
            average="macro",
            zero_division=0
        )
    )

    return {
        "loss": avg_loss,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "macro_f1": f1,
        "predictions": all_predictions,
        "labels": all_labels
    }


# ============================================================
# TRAINING
# ============================================================

print()
print("=" * 70)
print("STARTING HYBRID TRAINING")
print("=" * 70)

print()
print("Training configuration:")
print("Model:", MODEL_NAME)
print("Epochs:", EPOCHS)
print("Batch size:", BATCH_SIZE)
print("Learning rate:", LEARNING_RATE)
print("Max length:", MAX_LENGTH)
print("Human sample weight: 5.0")
print("Pseudo sample weight: 1.0")


best_f1 = -1.0
patience_counter = 0

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


for epoch in range(EPOCHS):

    print()
    print("=" * 70)
    print(f"EPOCH {epoch + 1}/{EPOCHS}")
    print("=" * 70)

    model.train()

    running_loss = 0.0
    processed_samples = 0

    for step, batch in enumerate(train_loader):

        input_ids = batch["input_ids"].to(DEVICE)
        attention_mask = batch["attention_mask"].to(DEVICE)
        labels = batch["labels"].to(DEVICE)
        sample_weights = batch["sample_weight"].to(DEVICE)

        optimizer.zero_grad()

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        logits = outputs.logits

        # ----------------------------------------------------
        # PER-SAMPLE LOSS
        # ----------------------------------------------------

        criterion = torch.nn.CrossEntropyLoss(
            reduction="none"
        )

        individual_losses = criterion(
            logits,
            labels
        )

        # ----------------------------------------------------
        # APPLY HUMAN / PSEUDO SAMPLE WEIGHTS
        # ----------------------------------------------------

        weighted_loss = (
            individual_losses * sample_weights
        ).mean()

        weighted_loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )

        optimizer.step()
        scheduler.step()

        running_loss += (
            weighted_loss.item()
            * labels.size(0)
        )

        processed_samples += labels.size(0)

        if (
            (step + 1) % 100 == 0
            or step == len(train_loader) - 1
        ):

            avg_running_loss = (
                running_loss
                / processed_samples
            )

            print(
                f"Step {step + 1}/{len(train_loader)} "
                f"| Loss: {avg_running_loss:.4f}"
            )


    # ========================================================
    # VALIDATION
    # ========================================================

    train_loss = (
        running_loss
        / processed_samples
    )

    results = evaluate(
        model,
        val_loader
    )

    print()
    print("VALIDATION RESULTS")
    print("-" * 70)

    print(
        f"Train Loss : {train_loss:.4f}"
    )

    print(
        f"Val Loss   : {results['loss']:.4f}"
    )

    print(
        f"Accuracy   : {results['accuracy']:.4f}"
    )

    print(
        f"Precision  : {results['precision']:.4f}"
    )

    print(
        f"Recall     : {results['recall']:.4f}"
    )

    print(
        f"Macro F1   : {results['macro_f1']:.4f}"
    )


    # ========================================================
    # SAVE BEST MODEL
    # ========================================================

    if results["macro_f1"] > best_f1:

        best_f1 = results["macro_f1"]

        patience_counter = 0

        print()
        print("NEW BEST MODEL FOUND!")
        print(
            f"Best Validation Macro F1: {best_f1:.4f}"
        )

        model.save_pretrained(
            MODEL_DIR
        )

        tokenizer.save_pretrained(
            MODEL_DIR
        )

    else:

        patience_counter += 1

        print()
        print(
            f"No improvement. "
            f"Patience: {patience_counter}/{PATIENCE}"
        )

        if patience_counter >= PATIENCE:

            print()
            print(
                "Early stopping triggered."
            )

            break


# ============================================================
# LOAD BEST MODEL
# ============================================================

print()
print("=" * 70)
print("LOADING BEST HYBRID MODEL")
print("=" * 70)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_DIR
)

model.to(DEVICE)


# ============================================================
# FINAL HUMAN TEST
# ============================================================

print()
print("=" * 70)
print("FINAL HUMAN TEST RESULTS")
print("=" * 70)

test_results = evaluate(
    model,
    test_loader
)

print()
print(
    f"Test Loss     : {test_results['loss']:.4f}"
)

print(
    f"Test Accuracy : {test_results['accuracy']:.4f}"
)

print(
    f"Test Precision: {test_results['precision']:.4f}"
)

print(
    f"Test Recall   : {test_results['recall']:.4f}"
)

print(
    f"Test Macro F1 : {test_results['macro_f1']:.4f}"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print()
print("=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        test_results["labels"],
        test_results["predictions"],
        labels=[0, 1, 2],
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
    test_results["labels"],
    test_results["predictions"],
    labels=[0, 1, 2]
)

print()
print(
    "             Predicted"
)

print(
    "             Neg  Neu  Pos"
)

print(
    f"Actual Neg  {cm[0][0]:3d}  "
    f"{cm[0][1]:3d}  "
    f"{cm[0][2]:3d}"
)

print(
    f"Actual Neu  {cm[1][0]:3d}  "
    f"{cm[1][1]:3d}  "
    f"{cm[1][2]:3d}"
)

print(
    f"Actual Pos  {cm[2][0]:3d}  "
    f"{cm[2][1]:3d}  "
    f"{cm[2][2]:3d}"
)


# ============================================================
# SAVE TEST PREDICTIONS
# ============================================================

prediction_df = test_df[
    [
        "sentence",
        "aspect",
        "label"
    ]
].copy()

prediction_df["predicted_label"] = [
    ID2LABEL[p]
    for p in test_results["predictions"]
]


prediction_file = os.path.join(
    DATASET_DIR,
    "human_hybrid_test_predictions.csv"
)

prediction_df.to_csv(
    prediction_file,
    index=False
)


# ============================================================
# SAVE EXPERIMENT SUMMARY
# ============================================================

summary_file = os.path.join(
    DATASET_DIR,
    "hybrid_experiment_results.txt"
)

with open(
    summary_file,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "SMARTREVIEW AI - EXPERIMENT 4\n"
    )

    f.write(
        "HYBRID HUMAN + PSEUDO-LABELED RoBERTa\n\n"
    )

    f.write(
        f"Training records: {len(train_df)}\n"
    )

    f.write(
        f"Validation records: {len(val_df)}\n"
    )

    f.write(
        f"Test records: {len(test_df)}\n\n"
    )

    f.write(
        f"Best Validation Macro F1: "
        f"{best_f1:.4f}\n"
    )

    f.write(
        f"Test Accuracy: "
        f"{test_results['accuracy']:.4f}\n"
    )

    f.write(
        f"Test Precision: "
        f"{test_results['precision']:.4f}\n"
    )

    f.write(
        f"Test Recall: "
        f"{test_results['recall']:.4f}\n"
    )

    f.write(
        f"Test Macro F1: "
        f"{test_results['macro_f1']:.4f}\n"
    )


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 70)
print("HYBRID RoBERTa TRAINING COMPLETE")
print("=" * 70)

print()
print(
    f"Best Validation Macro F1: {best_f1:.4f}"
)

print(
    f"Final Test Accuracy: "
    f"{test_results['accuracy']:.4f}"
)

print(
    f"Final Test Macro F1: "
    f"{test_results['macro_f1']:.4f}"
)

print()
print(
    "Model saved to:"
)

print(MODEL_DIR)

print()
print(
    "Predictions saved to:"
)

print(prediction_file)

print()
print(
    "Experiment summary saved to:"
)

print(summary_file)

print()
print(
    "Experiment 4 completed successfully."
)