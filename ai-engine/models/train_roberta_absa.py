import os
import numpy as np
import pandas as pd
import torch

from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    DataCollatorWithPadding,
    TrainingArguments,
    Trainer
)
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support
)


# ============================================================
# 1. PROJECT PATHS
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

TRAIN_FILE = os.path.join(
    DATASET_DIR,
    "absa_train.csv"
)

VALIDATION_FILE = os.path.join(
    DATASET_DIR,
    "absa_validation.csv"
)

TEST_FILE = os.path.join(
    DATASET_DIR,
    "absa_test.csv"
)


# ============================================================
# 2. MODEL CONFIGURATION
# ============================================================

MODEL_NAME = "roberta-base"

MAX_LENGTH = 128


# ============================================================
# 3. LABEL MAPPING
# ============================================================

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
# 4. DEVICE CHECK
# ============================================================

print("\n" + "=" * 65)
print("SMARTREVIEW AI - RoBERTa ABSA TRAINING")
print("=" * 65)

print(f"PyTorch version : {torch.__version__}")
print(f"CUDA available  : {torch.cuda.is_available()}")

if torch.cuda.is_available():

    device = "cuda"

    print(f"Training device : {device}")
    print(
        f"GPU             : "
        f"{torch.cuda.get_device_name(0)}"
    )

    print(
        f"GPU memory      : "
        f"{torch.cuda.get_device_properties(0).total_memory / (1024 ** 3):.2f} GB"
    )

else:

    device = "cpu"

    print("Training device : CPU")
    print("WARNING: CUDA is not available.")

print("=" * 65)


# ============================================================
# 5. CHECK DATASET FILES
# ============================================================

print("\nChecking dataset files...")

required_files = [
    TRAIN_FILE,
    VALIDATION_FILE,
    TEST_FILE
]

for file_path in required_files:

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            f"Dataset file not found:\n{file_path}"
        )

    print(f"FOUND: {file_path}")


# ============================================================
# 6. LOAD DATASETS
# ============================================================

print("\nLoading datasets...")

train_df = pd.read_csv(
    TRAIN_FILE
)

validation_df = pd.read_csv(
    VALIDATION_FILE
)

test_df = pd.read_csv(
    TEST_FILE
)

print(
    f"Training records   : {len(train_df)}"
)

print(
    f"Validation records : {len(validation_df)}"
)

print(
    f"Test records       : {len(test_df)}"
)


# ============================================================
# 7. CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "sentence",
    "aspect",
    "aspect_sentiment"
]

for column in required_columns:

    if column not in train_df.columns:

        raise ValueError(
            f"Missing column in training dataset: {column}"
        )

    if column not in validation_df.columns:

        raise ValueError(
            f"Missing column in validation dataset: {column}"
        )

    if column not in test_df.columns:

        raise ValueError(
            f"Missing column in test dataset: {column}"
        )


# ============================================================
# 8. PREPARE DATA
# ============================================================

def prepare_dataframe(df):

    df = df.copy()

    # Remove rows with missing required values
    df = df.dropna(
        subset=[
            "sentence",
            "aspect",
            "aspect_sentiment"
        ]
    )

    # Normalize labels
    df["aspect_sentiment"] = (
        df["aspect_sentiment"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # Convert sentiment labels to numerical IDs
    df["label"] = df[
        "aspect_sentiment"
    ].map(label2id)

    # Remove unexpected labels
    df = df.dropna(
        subset=["label"]
    )

    df["label"] = df[
        "label"
    ].astype(int)

    # --------------------------------------------------------
    # Aspect-conditioned input
    # --------------------------------------------------------
    #
    # Example:
    #
    # Sentence: The battery is terrible.
    # Aspect: battery
    #
    # --------------------------------------------------------

    df["text"] = (
        "Sentence: "
        + df["sentence"].astype(str)
        + " Aspect: "
        + df["aspect"].astype(str)
    )

    return df[
        [
            "text",
            "label"
        ]
    ]


print("\nPreparing datasets...")

train_df = prepare_dataframe(
    train_df
)

validation_df = prepare_dataframe(
    validation_df
)

test_df = prepare_dataframe(
    test_df
)

print(
    f"Prepared training records   : "
    f"{len(train_df)}"
)

print(
    f"Prepared validation records : "
    f"{len(validation_df)}"
)

print(
    f"Prepared test records       : "
    f"{len(test_df)}"
)


# ============================================================
# 9. DISPLAY LABEL DISTRIBUTION
# ============================================================

print("\nTraining label distribution:")

print(
    train_df["label"]
    .value_counts()
    .sort_index()
    .rename(
        index=id2label
    )
)


# ============================================================
# 10. CONVERT TO HUGGING FACE DATASETS
# ============================================================

print("\nConverting datasets...")

train_dataset = Dataset.from_pandas(
    train_df,
    preserve_index=False
)

validation_dataset = Dataset.from_pandas(
    validation_df,
    preserve_index=False
)

test_dataset = Dataset.from_pandas(
    test_df,
    preserve_index=False
)


# ============================================================
# 11. LOAD TOKENIZER
# ============================================================

print("\nLoading RoBERTa tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)


# ============================================================
# 12. TOKENIZATION
# ============================================================

def tokenize_function(examples):

    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=MAX_LENGTH
    )


print("\nTokenizing datasets...")

train_dataset = train_dataset.map(
    tokenize_function,
    batched=True
)

validation_dataset = validation_dataset.map(
    tokenize_function,
    batched=True
)

test_dataset = test_dataset.map(
    tokenize_function,
    batched=True
)

print("Tokenization completed.")


# ============================================================
# 13. DATA COLLATOR
# ============================================================

data_collator = DataCollatorWithPadding(
    tokenizer=tokenizer
)


# ============================================================
# 14. LOAD RoBERTa MODEL
# ============================================================

print("\nLoading RoBERTa model...")

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3,
    id2label=id2label,
    label2id=label2id
)


# ============================================================
# 15. METRICS
# ============================================================

def compute_metrics(eval_pred):

    predictions, labels = eval_pred

    predictions = np.argmax(
        predictions,
        axis=1
    )

    accuracy = accuracy_score(
        labels,
        predictions
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            labels,
            predictions,
            average="weighted",
            zero_division=0
        )
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }


# ============================================================
# 16. TRAINING ARGUMENTS
# ============================================================

print("\nPreparing training configuration...")

training_args = TrainingArguments(

    # Where checkpoints and model files are stored
    output_dir=MODEL_DIR,

    # --------------------------------------------------------
    # Batch configuration
    # --------------------------------------------------------

    per_device_train_batch_size=8,

    per_device_eval_batch_size=8,

    gradient_accumulation_steps=2,

    # --------------------------------------------------------
    # Training
    # --------------------------------------------------------

    num_train_epochs=3,

    learning_rate=2e-5,

    weight_decay=0.01,

    # IMPORTANT:
    # Transformers 5.x uses warmup_steps.
    # 0.1 means approximately 10% of training steps.
    warmup_steps=0.1,

    # --------------------------------------------------------
    # Evaluation
    # --------------------------------------------------------

    eval_strategy="epoch",

    save_strategy="epoch",

    load_best_model_at_end=True,

    metric_for_best_model="f1",

    greater_is_better=True,

    # --------------------------------------------------------
    # Logging
    # --------------------------------------------------------

    logging_strategy="steps",

    logging_steps=100,

    report_to="none",

    # --------------------------------------------------------
    # GPU optimization
    # --------------------------------------------------------

    fp16=torch.cuda.is_available(),

    # --------------------------------------------------------
    # Reproducibility
    # --------------------------------------------------------

    seed=42
)


# ============================================================
# 17. CREATE TRAINER
# ============================================================

print("\nCreating Trainer...")

trainer = Trainer(

    model=model,

    args=training_args,

    train_dataset=train_dataset,

    eval_dataset=validation_dataset,

    processing_class=tokenizer,

    data_collator=data_collator,

    compute_metrics=compute_metrics
)


# ============================================================
# 18. START TRAINING
# ============================================================

print("\n")
print("=" * 65)
print("STARTING RoBERTa FINE-TUNING")
print("=" * 65)

print(
    "\nModel           : roberta-base"
)

print(
    "Task            : Aspect-Based Sentiment Analysis"
)

print(
    "Classes         : negative / neutral / positive"
)

print(
    f"Train records   : {len(train_dataset)}"
)

print(
    f"Validation      : {len(validation_dataset)}"
)

print(
    f"Test records    : {len(test_dataset)}"
)

print(
    f"Epochs          : {training_args.num_train_epochs}"
)

print(
    f"Batch size      : {training_args.per_device_train_batch_size}"
)

print(
    f"Gradient accum. : {training_args.gradient_accumulation_steps}"
)

print(
    f"Max length      : {MAX_LENGTH}"
)

print(
    f"Learning rate   : {training_args.learning_rate}"
)

print(
    f"FP16            : {training_args.fp16}"
)

print("=" * 65)


train_result = trainer.train()


# ============================================================
# 19. TRAINING SUMMARY
# ============================================================

print("\n")
print("=" * 65)
print("TRAINING COMPLETED")
print("=" * 65)

print(
    f"Training loss: "
    f"{train_result.training_loss:.4f}"
)


# ============================================================
# 20. EVALUATE ON TEST DATA
# ============================================================

print("\n")
print("=" * 65)
print("EVALUATING ON TEST DATA")
print("=" * 65)

test_results = trainer.evaluate(
    eval_dataset=test_dataset
)


# ============================================================
# 21. DISPLAY TEST RESULTS
# ============================================================

print("\nTEST RESULTS")
print("=" * 65)

for key, value in test_results.items():

    if isinstance(value, float):

        print(
            f"{key}: {value:.4f}"
        )

    else:

        print(
            f"{key}: {value}"
        )


# ============================================================
# 22. SAVE TRAINED MODEL
# ============================================================

print("\n")
print("=" * 65)
print("SAVING TRAINED MODEL")
print("=" * 65)

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

trainer.save_model(
    MODEL_DIR
)

tokenizer.save_pretrained(
    MODEL_DIR
)

print(
    f"\nModel saved successfully!"
)

print(
    f"Model location:\n{MODEL_DIR}"
)


# ============================================================
# 23. FINAL MESSAGE
# ============================================================

print("\n")
print("=" * 65)
print("SMARTREVIEW AI - TRAINING FINISHED")
print("=" * 65)

print(
    "\nRoBERTa fine-tuning completed successfully."
)

print(
    "The trained model is ready for the next evaluation "
    "and inference phase."
)