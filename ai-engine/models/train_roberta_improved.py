import os
import random
import numpy as np
import pandas as pd
import torch

from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_cosine_schedule_with_warmup
)
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)


# ============================================================
# SMARTREVIEW AI - EXPERIMENT 6
# IMPROVED HYBRID RoBERTa TRAINING
# ============================================================

print("=" * 70)
print("SMARTREVIEW AI - EXPERIMENT 6")
print("IMPROVED HYBRID RoBERTa TRAINING")
print("=" * 70)


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42

MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"

MAX_LENGTH = 128

BATCH_SIZE = 8

WEIGHT_DECAY = 0.01

LABEL_SMOOTHING = 0.1

WARMUP_RATIO = 0.1

MAX_GRAD_NORM = 1.0

# Curriculum learning
PHASE_1_EPOCHS = 2   # Human-only data

PHASE_1_LR = 3e-5    # Higher LR for clean data

PHASE_2_EPOCHS = 3   # Full hybrid data  

PHASE_2_LR = 1e-5    # Lower LR for noisy data

PATIENCE = 2         # Early stopping patience (Phase 2 only)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

DATASET_DIR = os.path.join(
    BASE_DIR,
    "ai-engine",
    "datasets"
)

HUMAN_DIR = os.path.join(
    DATASET_DIR,
    "human"
)

HUMAN_TRAIN = os.path.join(
    HUMAN_DIR,
    "human_train.csv"
)

AUGMENTED_FILE = os.path.join(
    HUMAN_DIR,
    "augmented_human_train.csv"
)

HYBRID_FILE = os.path.join(
    DATASET_DIR,
    "improved_hybrid_train.csv"
)

VALIDATION_FILE = os.path.join(
    HUMAN_DIR,
    "human_validation.csv"
)

TEST_FILE = os.path.join(
    HUMAN_DIR,
    "human_test.csv"
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "ai-engine",
    "models",
    "roberta_absa_improved"
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
# REPRODUCIBILITY
# ============================================================

def set_seed(seed=SEED):

    random.seed(seed)

    np.random.seed(seed)

    torch.manual_seed(seed)

    if torch.cuda.is_available():

        torch.cuda.manual_seed_all(seed)


set_seed(SEED)


# ============================================================
# DEVICE CONFIGURATION
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

USE_AMP = torch.cuda.is_available()

print()
print("DEVICE INFORMATION")
print("-" * 70)

print("Device:", DEVICE)
print("Mixed Precision (FP16):", USE_AMP)

if torch.cuda.is_available():

    print("GPU:", torch.cuda.get_device_name(0))

    gpu_mem = round(
        torch.cuda.get_device_properties(0).total_memory / (1024 ** 3),
        2
    )

    print("GPU Memory:", gpu_mem, "GB")

else:

    print("WARNING: CUDA is not available. Training will run on CPU.")


# ============================================================
# DATASET CLASS
# ============================================================

class ABSADataset(Dataset):

    def __init__(
        self,
        dataframe,
        tokenizer,
        max_length=MAX_LENGTH,
        include_weight=False
    ):

        self.data = dataframe.reset_index(drop=True)

        self.tokenizer = tokenizer

        self.max_length = max_length

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
            max_length=self.max_length,
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

            item["token_type_ids"] = encoding["token_type_ids"].squeeze(0)

        if self.include_weight:

            item["sample_weight"] = torch.tensor(
                float(row["final_weight"]),
                dtype=torch.float
            )

        return item


# ============================================================
# EVALUATION FUNCTION
# ============================================================

def evaluate(model, dataloader, device):

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

            input_ids = batch["input_ids"].to(device)

            attention_mask = batch["attention_mask"].to(device)

            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            logits = outputs.logits

            loss = criterion(
                logits,
                labels
            )

            total_loss += loss.item()

            total_samples += labels.size(0)

            preds = torch.argmax(
                logits,
                dim=1
            )

            all_predictions.extend(
                preds.cpu().numpy()
            )

            all_labels.extend(
                labels.cpu().numpy()
            )

    avg_loss = total_loss / total_samples

    accuracy = accuracy_score(
        all_labels,
        all_predictions
    )

    precision, recall, f1, _ = precision_recall_fscore_support(
        all_labels,
        all_predictions,
        average="macro",
        zero_division=0
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
# MAIN EXECUTION
# ============================================================

def main():

    # --------------------------------------------------------
    # 1. Check Required Files
    # --------------------------------------------------------

    print()
    print("CHECKING DATASET FILES")
    print("-" * 70)

    for required_file in [
        HUMAN_TRAIN,
        HYBRID_FILE,
        VALIDATION_FILE,
        TEST_FILE
    ]:

        if not os.path.exists(required_file):

            raise FileNotFoundError(
                f"Required dataset file not found:\n{required_file}"
            )

        print("FOUND:", required_file)

    has_augmented = os.path.exists(AUGMENTED_FILE)

    if has_augmented:

        print("FOUND OPTIONAL AUGMENTATION:", AUGMENTED_FILE)

    else:

        print("INFO: No augmented data found. Phase 1 will use human_train only.")

    # --------------------------------------------------------
    # 2. Load Datasets
    # --------------------------------------------------------

    print()
    print("LOADING DATASETS")
    print("-" * 70)

    human_df = pd.read_csv(HUMAN_TRAIN)

    if has_augmented:

        aug_df = pd.read_csv(AUGMENTED_FILE)

        phase1_df = pd.concat(
            [human_df, aug_df],
            ignore_index=True
        )

        print(
            f"Phase 1 combined {len(human_df)} human + {len(aug_df)} augmented samples."
        )

    else:

        phase1_df = human_df.copy()

    hybrid_df = pd.read_csv(HYBRID_FILE)

    val_df = pd.read_csv(VALIDATION_FILE)

    test_df = pd.read_csv(TEST_FILE)

    # --------------------------------------------------------
    # 3. Validate Columns
    # --------------------------------------------------------

    base_required_cols = ["sentence", "aspect", "label"]

    for col in base_required_cols:

        if col not in phase1_df.columns:

            raise ValueError(
                f"Column '{col}' missing from Phase 1 training data."
            )

        if col not in val_df.columns:

            raise ValueError(
                f"Column '{col}' missing from validation data."
            )

        if col not in test_df.columns:

            raise ValueError(
                f"Column '{col}' missing from test data."
            )

    hybrid_required_cols = ["sentence", "aspect", "label", "final_weight"]

    for col in hybrid_required_cols:

        if col not in hybrid_df.columns:

            raise ValueError(
                f"Column '{col}' missing from hybrid training data."
            )

    # --------------------------------------------------------
    # 4. Clean Data and Encode Labels
    # --------------------------------------------------------

    # Clean Phase 1 data
    phase1_df = phase1_df.dropna(subset=base_required_cols).copy()

    phase1_df["sentence"] = phase1_df["sentence"].astype(str)

    phase1_df["aspect"] = phase1_df["aspect"].astype(str)

    phase1_df["label"] = phase1_df["label"].astype(str).str.lower()

    phase1_df = phase1_df[phase1_df["label"].isin(LABEL2ID.keys())].copy()

    phase1_df["label_id"] = phase1_df["label"].map(LABEL2ID)

    # Clean Hybrid data (Phase 2)
    hybrid_df = hybrid_df.dropna(subset=hybrid_required_cols).copy()

    hybrid_df["sentence"] = hybrid_df["sentence"].astype(str)

    hybrid_df["aspect"] = hybrid_df["aspect"].astype(str)

    hybrid_df["label"] = hybrid_df["label"].astype(str).str.lower()

    hybrid_df = hybrid_df[hybrid_df["label"].isin(LABEL2ID.keys())].copy()

    hybrid_df["final_weight"] = pd.to_numeric(
        hybrid_df["final_weight"],
        errors="coerce"
    )

    hybrid_df = hybrid_df.dropna(subset=["final_weight"]).copy()

    hybrid_df["label_id"] = hybrid_df["label"].map(LABEL2ID)

    # Clean Validation data
    val_df = val_df.dropna(subset=base_required_cols).copy()

    val_df["sentence"] = val_df["sentence"].astype(str)

    val_df["aspect"] = val_df["aspect"].astype(str)

    val_df["label"] = val_df["label"].astype(str).str.lower()

    val_df = val_df[val_df["label"].isin(LABEL2ID.keys())].copy()

    val_df["label_id"] = val_df["label"].map(LABEL2ID)

    # Clean Test data
    test_df = test_df.dropna(subset=base_required_cols).copy()

    test_df["sentence"] = test_df["sentence"].astype(str)

    test_df["aspect"] = test_df["aspect"].astype(str)

    test_df["label"] = test_df["label"].astype(str).str.lower()

    test_df = test_df[test_df["label"].isin(LABEL2ID.keys())].copy()

    test_df["label_id"] = test_df["label"].map(LABEL2ID)

    # --------------------------------------------------------
    # 5. Dataset Statistics
    # --------------------------------------------------------

    print()
    print("DATASET SIZES")
    print("-" * 70)

    print("Phase 1 (Clean Human Train) :", len(phase1_df))

    print("Phase 2 (Hybrid Train)      :", len(hybrid_df))

    print("Validation                  :", len(val_df))

    print("Test                        :", len(test_df))

    print()
    print("LABEL DISTRIBUTIONS")
    print("-" * 70)

    print("Phase 1 Distribution:")
    print(phase1_df["label"].value_counts().to_string())

    print()
    print("Phase 2 (Hybrid) Distribution:")
    print(hybrid_df["label"].value_counts().to_string())

    print()
    print("Validation Distribution:")
    print(val_df["label"].value_counts().to_string())

    print()
    print("Test Distribution:")
    print(test_df["label"].value_counts().to_string())

    print()
    print("HYBRID FINAL WEIGHT SUMMARY")
    print("-" * 70)

    print(hybrid_df["final_weight"].describe().to_string())

    # --------------------------------------------------------
    # 6. Load Tokenizer & Model
    # --------------------------------------------------------

    print()
    print("LOADING TOKENIZER & PRETRAINED MODEL")
    print("-" * 70)

    print("Model:", MODEL_NAME)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=3,
        id2label=ID2LABEL,
        label2id=LABEL2ID
    )

    model.to(DEVICE)

    print("Model and tokenizer loaded successfully.")

    # --------------------------------------------------------
    # 7. Common Evaluation DataLoaders
    # --------------------------------------------------------

    val_dataset = ABSADataset(
        val_df,
        tokenizer,
        max_length=MAX_LENGTH,
        include_weight=False
    )

    test_dataset = ABSADataset(
        test_df,
        tokenizer,
        max_length=MAX_LENGTH,
        include_weight=False
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

    # Prepare model save directory
    os.makedirs(MODEL_DIR, exist_ok=True)

    best_f1 = -1.0

    scaler = torch.cuda.amp.GradScaler(enabled=USE_AMP)

    # ========================================================
    # PHASE 1: HUMAN-ONLY TRAINING (CURRICULUM - CLEAN DATA)
    # ========================================================

    print()
    print("=" * 70)
    print("STARTING PHASE 1: HUMAN-ONLY TRAINING (CLEAN CURRICULUM)")
    print("=" * 70)

    print(f"Phase 1 Epochs       : {PHASE_1_EPOCHS}")
    print(f"Phase 1 Learning Rate: {PHASE_1_LR}")
    print(f"Batch Size           : {BATCH_SIZE}")
    print(f"Label Smoothing      : {LABEL_SMOOTHING}")
    print(f"Warmup Ratio         : {WARMUP_RATIO}")
    print(f"Max Gradient Norm    : {MAX_GRAD_NORM}")

    phase1_dataset = ABSADataset(
        phase1_df,
        tokenizer,
        max_length=MAX_LENGTH,
        include_weight=False
    )

    phase1_loader = DataLoader(
        phase1_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True
    )

    optimizer_phase1 = torch.optim.AdamW(
        model.parameters(),
        lr=PHASE_1_LR,
        weight_decay=WEIGHT_DECAY
    )

    total_phase1_steps = len(phase1_loader) * PHASE_1_EPOCHS

    warmup_phase1_steps = int(WARMUP_RATIO * total_phase1_steps)

    scheduler_phase1 = get_cosine_schedule_with_warmup(
        optimizer_phase1,
        num_warmup_steps=warmup_phase1_steps,
        num_training_steps=total_phase1_steps
    )

    criterion_phase1 = torch.nn.CrossEntropyLoss(
        label_smoothing=LABEL_SMOOTHING
    )

    for epoch in range(PHASE_1_EPOCHS):

        print()
        print("-" * 70)
        print(f"PHASE 1 | EPOCH {epoch + 1}/{PHASE_1_EPOCHS}")
        print("-" * 70)

        model.train()

        running_loss = 0.0

        processed_samples = 0

        for step, batch in enumerate(phase1_loader):

            input_ids = batch["input_ids"].to(DEVICE)

            attention_mask = batch["attention_mask"].to(DEVICE)

            labels = batch["labels"].to(DEVICE)

            optimizer_phase1.zero_grad()

            with torch.cuda.amp.autocast(enabled=USE_AMP):

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )

                logits = outputs.logits

                loss = criterion_phase1(
                    logits,
                    labels
                )

            scaler.scale(loss).backward()

            scaler.unscale_(optimizer_phase1)

            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=MAX_GRAD_NORM
            )

            scaler.step(optimizer_phase1)

            scaler.update()

            scheduler_phase1.step()

            batch_size_cur = labels.size(0)

            running_loss += loss.item() * batch_size_cur

            processed_samples += batch_size_cur

            if (step + 1) % 10 == 0 or (step + 1) == len(phase1_loader):

                avg_running_loss = running_loss / processed_samples

                print(
                    f"Phase 1 | Epoch {epoch + 1}/{PHASE_1_EPOCHS} "
                    f"| Step {step + 1:3d}/{len(phase1_loader)} "
                    f"| Loss: {avg_running_loss:.4f}"
                )

        # Validation after each epoch
        train_loss = running_loss / processed_samples

        val_results = evaluate(model, val_loader, DEVICE)

        print()
        print(f"PHASE 1 | EPOCH {epoch + 1} VALIDATION RESULTS")
        print("-" * 70)

        print(f"Train Loss : {train_loss:.4f}")
        print(f"Val Loss   : {val_results['loss']:.4f}")
        print(f"Accuracy   : {val_results['accuracy']:.4f}")
        print(f"Precision  : {val_results['precision']:.4f}")
        print(f"Recall     : {val_results['recall']:.4f}")
        print(f"Macro F1   : {val_results['macro_f1']:.4f}")

        if val_results["macro_f1"] > best_f1:

            best_f1 = val_results["macro_f1"]

            print()
            print("NEW BEST MODEL FOUND IN PHASE 1!")
            print(f"Best Validation Macro F1: {best_f1:.4f}")

            model.save_pretrained(MODEL_DIR)

            tokenizer.save_pretrained(MODEL_DIR)

    # ========================================================
    # PHASE 2: FULL HYBRID TRAINING (CURRICULUM - EXPANDED DATA)
    # ========================================================

    print()
    print("=" * 70)
    print("STARTING PHASE 2: FULL HYBRID TRAINING (EXPANDED CURRICULUM)")
    print("=" * 70)

    # Load best checkpoint from Phase 1 if saved
    if os.path.exists(os.path.join(MODEL_DIR, "config.json")):

        print("Loading best model checkpoint from Phase 1...")

        model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

        model.to(DEVICE)

        print(f"Loaded checkpoint with baseline Validation Macro F1: {best_f1:.4f}")

    print(f"Phase 2 Epochs       : {PHASE_2_EPOCHS}")
    print(f"Phase 2 Learning Rate: {PHASE_2_LR}")
    print(f"Batch Size           : {BATCH_SIZE}")
    print(f"Label Smoothing      : {LABEL_SMOOTHING}")
    print(f"Patience             : {PATIENCE}")
    print(f"Max Gradient Norm    : {MAX_GRAD_NORM}")

    phase2_dataset = ABSADataset(
        hybrid_df,
        tokenizer,
        max_length=MAX_LENGTH,
        include_weight=True
    )

    sampler_weights = hybrid_df["final_weight"].values.astype(np.float64)

    sampler = WeightedRandomSampler(
        weights=sampler_weights,
        num_samples=len(sampler_weights),
        replacement=True
    )

    phase2_loader = DataLoader(
        phase2_dataset,
        batch_size=BATCH_SIZE,
        sampler=sampler
    )

    optimizer_phase2 = torch.optim.AdamW(
        model.parameters(),
        lr=PHASE_2_LR,
        weight_decay=WEIGHT_DECAY
    )

    total_phase2_steps = len(phase2_loader) * PHASE_2_EPOCHS

    warmup_phase2_steps = int(WARMUP_RATIO * total_phase2_steps)

    scheduler_phase2 = get_cosine_schedule_with_warmup(
        optimizer_phase2,
        num_warmup_steps=warmup_phase2_steps,
        num_training_steps=total_phase2_steps
    )

    criterion_phase2 = torch.nn.CrossEntropyLoss(
        label_smoothing=LABEL_SMOOTHING,
        reduction="none"
    )

    patience_counter = 0

    for epoch in range(PHASE_2_EPOCHS):

        print()
        print("-" * 70)
        print(f"PHASE 2 | EPOCH {epoch + 1}/{PHASE_2_EPOCHS}")
        print("-" * 70)

        model.train()

        running_loss = 0.0

        processed_samples = 0

        for step, batch in enumerate(phase2_loader):

            input_ids = batch["input_ids"].to(DEVICE)

            attention_mask = batch["attention_mask"].to(DEVICE)

            labels = batch["labels"].to(DEVICE)

            sample_weights = batch["sample_weight"].to(DEVICE)

            optimizer_phase2.zero_grad()

            with torch.cuda.amp.autocast(enabled=USE_AMP):

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )

                logits = outputs.logits

                per_sample_loss = criterion_phase2(
                    logits,
                    labels
                )

                weighted_loss = (per_sample_loss * sample_weights).mean()

            scaler.scale(weighted_loss).backward()

            scaler.unscale_(optimizer_phase2)

            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=MAX_GRAD_NORM
            )

            scaler.step(optimizer_phase2)

            scaler.update()

            scheduler_phase2.step()

            batch_size_cur = labels.size(0)

            running_loss += weighted_loss.item() * batch_size_cur

            processed_samples += batch_size_cur

            if (step + 1) % 50 == 0 or (step + 1) == len(phase2_loader):

                avg_running_loss = running_loss / processed_samples

                print(
                    f"Phase 2 | Epoch {epoch + 1}/{PHASE_2_EPOCHS} "
                    f"| Step {step + 1:3d}/{len(phase2_loader)} "
                    f"| Loss: {avg_running_loss:.4f}"
                )

        # Validation after each epoch
        train_loss = running_loss / processed_samples

        val_results = evaluate(model, val_loader, DEVICE)

        print()
        print(f"PHASE 2 | EPOCH {epoch + 1} VALIDATION RESULTS")
        print("-" * 70)

        print(f"Train Loss : {train_loss:.4f}")
        print(f"Val Loss   : {val_results['loss']:.4f}")
        print(f"Accuracy   : {val_results['accuracy']:.4f}")
        print(f"Precision  : {val_results['precision']:.4f}")
        print(f"Recall     : {val_results['recall']:.4f}")
        print(f"Macro F1   : {val_results['macro_f1']:.4f}")

        # Check early stopping and checkpoint saving
        if val_results["macro_f1"] > best_f1:

            best_f1 = val_results["macro_f1"]

            patience_counter = 0

            print()
            print("NEW BEST MODEL FOUND IN PHASE 2!")
            print(f"Best Validation Macro F1: {best_f1:.4f}")

            model.save_pretrained(MODEL_DIR)

            tokenizer.save_pretrained(MODEL_DIR)

        else:

            patience_counter += 1

            print()
            print(
                f"No improvement in Macro F1. "
                f"Patience: {patience_counter}/{PATIENCE}"
            )

            if patience_counter >= PATIENCE:

                print()
                print("Early stopping triggered in Phase 2.")

                break

    # ========================================================
    # FINAL EVALUATION ON HUMAN TEST SET
    # ========================================================

    print()
    print("=" * 70)
    print("LOADING BEST MODEL FOR FINAL TEST EVALUATION")
    print("=" * 70)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR
    )

    model.to(DEVICE)

    print()
    print("=" * 70)
    print("FINAL HUMAN TEST RESULTS")
    print("=" * 70)

    test_results = evaluate(model, test_loader, DEVICE)

    print()
    print(f"Test Loss     : {test_results['loss']:.4f}")
    print(f"Test Accuracy : {test_results['accuracy']:.4f}")
    print(f"Test Precision: {test_results['precision']:.4f}")
    print(f"Test Recall   : {test_results['recall']:.4f}")
    print(f"Test Macro F1 : {test_results['macro_f1']:.4f}")

    # Classification Report
    print()
    print("=" * 70)
    print("CLASSIFICATION REPORT")
    print("=" * 70)

    report_str = classification_report(
        test_results["labels"],
        test_results["predictions"],
        labels=[0, 1, 2],
        target_names=["negative", "neutral", "positive"],
        zero_division=0
    )

    print(report_str)

    # Confusion Matrix
    print()
    print("=" * 70)
    print("CONFUSION MATRIX")
    print("=" * 70)

    cm = confusion_matrix(
        test_results["labels"],
        test_results["predictions"],
        labels=[0, 1, 2]
    )

    cm_formatted = (
        "             Predicted\n"
        "             Neg  Neu  Pos\n"
        f"Actual Neg  {cm[0][0]:3d}  {cm[0][1]:3d}  {cm[0][2]:3d}\n"
        f"Actual Neu  {cm[1][0]:3d}  {cm[1][1]:3d}  {cm[1][2]:3d}\n"
        f"Actual Pos  {cm[2][0]:3d}  {cm[2][1]:3d}  {cm[2][2]:3d}"
    )

    print(cm_formatted)

    # --------------------------------------------------------
    # Save Test Predictions
    # --------------------------------------------------------

    prediction_df = test_df[["sentence", "aspect", "label"]].copy()

    prediction_df["predicted_label"] = [
        ID2LABEL[p] for p in test_results["predictions"]
    ]

    prediction_file = os.path.join(
        DATASET_DIR,
        "improved_test_predictions.csv"
    )

    prediction_df.to_csv(
        prediction_file,
        index=False
    )

    print()
    print("Predictions saved to:")
    print(prediction_file)

    # --------------------------------------------------------
    # Save Experiment Summary
    # --------------------------------------------------------

    summary_file = os.path.join(
        DATASET_DIR,
        "improved_experiment_results.txt"
    )

    with open(summary_file, "w", encoding="utf-8") as f:

        f.write("SMARTREVIEW AI - EXPERIMENT 6\n")
        f.write("IMPROVED HYBRID RoBERTa TRAINING RESULTS\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Model Name           : {MODEL_NAME}\n")
        f.write(f"Max Length           : {MAX_LENGTH}\n")
        f.write(f"Batch Size           : {BATCH_SIZE}\n")
        f.write(f"Weight Decay         : {WEIGHT_DECAY}\n")
        f.write(f"Label Smoothing      : {LABEL_SMOOTHING}\n")
        f.write(f"Warmup Ratio         : {WARMUP_RATIO}\n")
        f.write(f"Max Grad Norm        : {MAX_GRAD_NORM}\n\n")

        f.write(f"Phase 1 Epochs       : {PHASE_1_EPOCHS} (LR: {PHASE_1_LR})\n")
        f.write(f"Phase 2 Epochs       : {PHASE_2_EPOCHS} (LR: {PHASE_2_LR})\n")
        f.write(f"Phase 2 Patience     : {PATIENCE}\n\n")

        f.write(f"Phase 1 Training Rows: {len(phase1_df)}\n")
        f.write(f"Phase 2 Training Rows: {len(hybrid_df)}\n")
        f.write(f"Validation Rows      : {len(val_df)}\n")
        f.write(f"Test Rows            : {len(test_df)}\n\n")

        f.write(f"Best Validation F1   : {best_f1:.4f}\n\n")

        f.write(f"Test Loss            : {test_results['loss']:.4f}\n")
        f.write(f"Test Accuracy        : {test_results['accuracy']:.4f}\n")
        f.write(f"Test Precision       : {test_results['precision']:.4f}\n")
        f.write(f"Test Recall          : {test_results['recall']:.4f}\n")
        f.write(f"Test Macro F1        : {test_results['macro_f1']:.4f}\n\n")

        f.write("Classification Report:\n")
        f.write(report_str + "\n\n")

        f.write("Confusion Matrix:\n")
        f.write(cm_formatted + "\n")

    print()
    print("Experiment summary saved to:")
    print(summary_file)

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("IMPROVED RoBERTa TRAINING COMPLETE")
    print("=" * 70)

    print()
    print(f"Best Validation Macro F1: {best_f1:.4f}")
    print(f"Final Test Accuracy     : {test_results['accuracy']:.4f}")
    print(f"Final Test Macro F1     : {test_results['macro_f1']:.4f}")
    print()
    print("Model saved to:", MODEL_DIR)
    print("Experiment 6 completed successfully.")


if __name__ == "__main__":

    main()
