import os
import random
import numpy as np
import pandas as pd
import torch

from pathlib import Path
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup
)
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)


# ============================================================
# SMARTREVIEW AI
# HUMAN-SUPERVISED RoBERTa FINE-TUNING
# ============================================================


# ------------------------------------------------------------
# 1. Reproducibility
# ------------------------------------------------------------

SEED = 42

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ------------------------------------------------------------
# 2. Paths
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    BASE_DIR
    / "ai-engine"
    / "datasets"
    / "human"
)

MODEL_DIR = (
    BASE_DIR
    / "ai-engine"
    / "models"
    / "roberta_absa_human"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


TRAIN_FILE = DATA_DIR / "human_train.csv"
VALIDATION_FILE = DATA_DIR / "human_validation.csv"
TEST_FILE = DATA_DIR / "human_test.csv"


# ------------------------------------------------------------
# 3. Configuration
# ------------------------------------------------------------

MODEL_NAME = "roberta-base"

MAX_LENGTH = 128

BATCH_SIZE = 8

EPOCHS = 5

LEARNING_RATE = 2e-5

WEIGHT_DECAY = 0.01

PATIENCE = 2


# ------------------------------------------------------------
# 4. Device
# ------------------------------------------------------------

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


print("=" * 70)
print("SMARTREVIEW AI - HUMAN SUPERVISED RoBERTa")
print("=" * 70)

print(f"\nDevice: {DEVICE}")

if torch.cuda.is_available():
    print(
        f"GPU: {torch.cuda.get_device_name(0)}"
    )

    print(
        f"GPU Memory: "
        f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB"
    )
else:
    print("WARNING: CUDA is not available.")


# ------------------------------------------------------------
# 5. Load datasets
# ------------------------------------------------------------

print("\nLoading human datasets...")

train_df = pd.read_csv(TRAIN_FILE)

validation_df = pd.read_csv(
    VALIDATION_FILE
)

test_df = pd.read_csv(TEST_FILE)


print(f"Training records   : {len(train_df)}")
print(f"Validation records : {len(validation_df)}")
print(f"Test records       : {len(test_df)}")


# ------------------------------------------------------------
# 6. Label mapping
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# 7. Convert labels
# ------------------------------------------------------------

train_df["label_id"] = (
    train_df["label"]
    .map(label2id)
)

validation_df["label_id"] = (
    validation_df["label"]
    .map(label2id)
)

test_df["label_id"] = (
    test_df["label"]
    .map(label2id)
)


# ------------------------------------------------------------
# 8. Dataset class
# ------------------------------------------------------------

class ABSADataset(Dataset):

    def __init__(
        self,
        dataframe,
        tokenizer,
        max_length
    ):

        self.dataframe = dataframe.reset_index(
            drop=True
        )

        self.tokenizer = tokenizer

        self.max_length = max_length


    def __len__(self):

        return len(self.dataframe)


    def __getitem__(self, index):

        row = self.dataframe.iloc[index]

        sentence = str(
            row["sentence"]
        )

        aspect = str(
            row["aspect"]
        )

        label = int(
            row["label_id"]
        )

        # Aspect-conditioned input
        text = (
            sentence
            + " [ASPECT] "
            + aspect
        )

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt"
        )

        item = {
            "input_ids":
                encoding["input_ids"].squeeze(0),

            "attention_mask":
                encoding["attention_mask"].squeeze(0),

            "labels":
                torch.tensor(
                    label,
                    dtype=torch.long
                )
        }

        return item


# ------------------------------------------------------------
# 9. Load tokenizer
# ------------------------------------------------------------

print("\nLoading RoBERTa tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)


# ------------------------------------------------------------
# 10. Create datasets
# ------------------------------------------------------------

train_dataset = ABSADataset(
    train_df,
    tokenizer,
    MAX_LENGTH
)

validation_dataset = ABSADataset(
    validation_df,
    tokenizer,
    MAX_LENGTH
)

test_dataset = ABSADataset(
    test_df,
    tokenizer,
    MAX_LENGTH
)


# ------------------------------------------------------------
# 11. Create DataLoaders
# ------------------------------------------------------------

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

validation_loader = DataLoader(
    validation_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)


# ------------------------------------------------------------
# 12. Load RoBERTa
# ------------------------------------------------------------

print("\nLoading RoBERTa model...")

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3,
    id2label=id2label,
    label2id=label2id
)

model.to(DEVICE)


# ------------------------------------------------------------
# 13. Optimizer
# ------------------------------------------------------------

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY
)


# ------------------------------------------------------------
# 14. Scheduler
# ------------------------------------------------------------

total_training_steps = (
    len(train_loader)
    * EPOCHS
)

scheduler = get_linear_schedule_with_warmup(
    optimizer,
    num_warmup_steps=0,
    num_training_steps=total_training_steps
)


# ------------------------------------------------------------
# 15. Evaluation function
# ------------------------------------------------------------

def evaluate(
    model,
    dataloader
):

    model.eval()

    predictions = []

    actual_labels = []

    total_loss = 0.0

    with torch.no_grad():

        for batch in dataloader:

            input_ids = batch[
                "input_ids"
            ].to(DEVICE)

            attention_mask = batch[
                "attention_mask"
            ].to(DEVICE)

            labels = batch[
                "labels"
            ].to(DEVICE)


            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )


            total_loss += (
                outputs.loss.item()
            )


            logits = outputs.logits

            preds = torch.argmax(
                logits,
                dim=1
            )


            predictions.extend(
                preds.cpu().numpy()
            )

            actual_labels.extend(
                labels.cpu().numpy()
            )


    average_loss = (
        total_loss
        / len(dataloader)
    )


    accuracy = accuracy_score(
        actual_labels,
        predictions
    )


    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            actual_labels,
            predictions,
            average="macro",
            zero_division=0
        )
    )


    return (
        average_loss,
        accuracy,
        precision,
        recall,
        f1,
        actual_labels,
        predictions
    )


# ------------------------------------------------------------
# 16. Training
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STARTING HUMAN-SUPERVISED RoBERTa TRAINING")
print("=" * 70)

print(f"\nModel          : {MODEL_NAME}")
print(f"Max length     : {MAX_LENGTH}")
print(f"Batch size     : {BATCH_SIZE}")
print(f"Learning rate  : {LEARNING_RATE}")
print(f"Epochs         : {EPOCHS}")
print(f"Device         : {DEVICE}")


best_f1 = -1.0

patience_counter = 0


for epoch in range(EPOCHS):

    print(
        f"\n{'=' * 70}"
    )

    print(
        f"EPOCH {epoch + 1}/{EPOCHS}"
    )

    print(
        f"{'=' * 70}"
    )


    model.train()

    total_train_loss = 0.0


    for step, batch in enumerate(
        train_loader
    ):

        input_ids = batch[
            "input_ids"
        ].to(DEVICE)

        attention_mask = batch[
            "attention_mask"
        ].to(DEVICE)

        labels = batch[
            "labels"
        ].to(DEVICE)


        optimizer.zero_grad()


        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )


        loss = outputs.loss


        loss.backward()


        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            max_norm=1.0
        )


        optimizer.step()

        scheduler.step()


        total_train_loss += (
            loss.item()
        )


        if (
            (step + 1) % 10 == 0
            or
            (step + 1) == len(train_loader)
        ):

            print(
                f"Step "
                f"{step + 1}/{len(train_loader)} "
                f"| Loss: {loss.item():.4f}"
            )


    average_train_loss = (
        total_train_loss
        / len(train_loader)
    )


    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    (
        val_loss,
        val_accuracy,
        val_precision,
        val_recall,
        val_f1,
        _,
        _
    ) = evaluate(
        model,
        validation_loader
    )


    print("\nValidation Results:")

    print(
        f"Train Loss : "
        f"{average_train_loss:.4f}"
    )

    print(
        f"Val Loss   : "
        f"{val_loss:.4f}"
    )

    print(
        f"Accuracy   : "
        f"{val_accuracy:.4f}"
    )

    print(
        f"Precision  : "
        f"{val_precision:.4f}"
    )

    print(
        f"Recall     : "
        f"{val_recall:.4f}"
    )

    print(
        f"Macro F1   : "
        f"{val_f1:.4f}"
    )


    # --------------------------------------------------------
    # Save best model
    # --------------------------------------------------------

    if val_f1 > best_f1:

        best_f1 = val_f1

        patience_counter = 0

        print(
            "\nNew best model found!"
        )

        print(
            f"Best validation F1: "
            f"{best_f1:.4f}"
        )


        model.save_pretrained(
            MODEL_DIR
        )

        tokenizer.save_pretrained(
            MODEL_DIR
        )

    else:

        patience_counter += 1

        print(
            f"\nNo improvement."
            f" Patience: "
            f"{patience_counter}/{PATIENCE}"
        )


        if patience_counter >= PATIENCE:

            print(
                "\nEarly stopping triggered."
            )

            break


# ------------------------------------------------------------
# 17. Load best model
# ------------------------------------------------------------

print("\n" + "=" * 70)

print("LOADING BEST MODEL")

print("=" * 70)


model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_DIR
)

model.to(DEVICE)


# ------------------------------------------------------------
# 18. Final test evaluation
# ------------------------------------------------------------

print("\n" + "=" * 70)

print("FINAL HUMAN TEST RESULTS")

print("=" * 70)


(
    test_loss,
    test_accuracy,
    test_precision,
    test_recall,
    test_f1,
    actual,
    predicted
) = evaluate(
    model,
    test_loader
)


print(
    f"\nTest Loss   : {test_loss:.4f}"
)

print(
    f"Accuracy    : {test_accuracy:.4f}"
)

print(
    f"Precision   : {test_precision:.4f}"
)

print(
    f"Recall      : {test_recall:.4f}"
)

print(
    f"Macro F1    : {test_f1:.4f}"
)


# ------------------------------------------------------------
# 19. Classification report
# ------------------------------------------------------------

print("\n" + "=" * 70)

print("CLASSIFICATION REPORT")

print("=" * 70)


print(
    classification_report(
        actual,
        predicted,
        target_names=[
            "negative",
            "neutral",
            "positive"
        ],
        zero_division=0
    )
)


# ------------------------------------------------------------
# 20. Confusion matrix
# ------------------------------------------------------------

print("=" * 70)

print("CONFUSION MATRIX")

print("=" * 70)


cm = confusion_matrix(
    actual,
    predicted
)


print(
    "\n              Predicted"
)

print(
    "              Neg  Neu  Pos"
)

print(
    f"Actual Neg    "
    f"{cm[0][0]:3d}  "
    f"{cm[0][1]:3d}  "
    f"{cm[0][2]:3d}"
)

print(
    f"Actual Neu    "
    f"{cm[1][0]:3d}  "
    f"{cm[1][1]:3d}  "
    f"{cm[1][2]:3d}"
)

print(
    f"Actual Pos    "
    f"{cm[2][0]:3d}  "
    f"{cm[2][1]:3d}  "
    f"{cm[2][2]:3d}"
)


# ------------------------------------------------------------
# 21. Save test predictions
# ------------------------------------------------------------

results_df = test_df.copy()

results_df["predicted_label"] = [
    id2label[p]
    for p in predicted
]


results_df["correct"] = (
    results_df["label_id"]
    ==
    predicted
)


prediction_file = (
    BASE_DIR
    / "ai-engine"
    / "datasets"
    / "human_test_predictions.csv"
)


results_df.to_csv(
    prediction_file,
    index=False
)


# ------------------------------------------------------------
# 22. Final information
# ------------------------------------------------------------

print("\n" + "=" * 70)

print("HUMAN-SUPERVISED TRAINING COMPLETE")

print("=" * 70)

print(
    f"\nBest Validation Macro F1 : "
    f"{best_f1:.4f}"
)

print(
    f"Final Test Accuracy      : "
    f"{test_accuracy:.4f}"
)

print(
    f"Final Test Macro F1      : "
    f"{test_f1:.4f}"
)

print(
    f"\nModel saved to:"
)

print(
    MODEL_DIR
)

print(
    f"\nPredictions saved to:"
)

print(
    prediction_file
)

print(
    "\nThe human-supervised RoBERTa experiment is complete."
)