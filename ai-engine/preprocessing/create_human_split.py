import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split


# ============================================================
# SMARTREVIEW AI
# Human-Validated Dataset Split
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "ai-engine"
    / "datasets"
    / "validation_dataset.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "ai-engine"
    / "datasets"
    / "human"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("=" * 70)
print("SMARTREVIEW AI - HUMAN DATASET SPLIT")
print("=" * 70)


# ------------------------------------------------------------
# 1. Load dataset
# ------------------------------------------------------------

print("\nLoading human-validated dataset...")

df = pd.read_csv(INPUT_FILE)

print(f"Total rows in file: {len(df)}")


# ------------------------------------------------------------
# 2. Keep only human-labelled records
# ------------------------------------------------------------

valid_labels = [
    "positive",
    "neutral",
    "negative"
]

df = df[
    df["validated_sentiment"].isin(valid_labels)
].copy()


print(f"Human-labelled records: {len(df)}")


# ------------------------------------------------------------
# 3. Remove duplicate sentence/aspect pairs
# ------------------------------------------------------------

before_duplicates = len(df)

df = df.drop_duplicates(
    subset=["sentence", "aspect"]
).reset_index(drop=True)

duplicates_removed = before_duplicates - len(df)

print(f"Duplicate pairs removed: {duplicates_removed}")
print(f"Records after deduplication: {len(df)}")


# ------------------------------------------------------------
# 4. Show class distribution
# ------------------------------------------------------------

print("\nClass distribution:")

print(
    df["validated_sentiment"]
    .value_counts()
)


# ------------------------------------------------------------
# 5. First split
#
# 70% training
# 30% temporary
# ------------------------------------------------------------

train_df, temp_df = train_test_split(
    df,
    test_size=0.30,
    random_state=42,
    stratify=df["validated_sentiment"]
)


# ------------------------------------------------------------
# 6. Second split
#
# Temporary 30%:
# 15% validation
# 15% test
# ------------------------------------------------------------

validation_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    random_state=42,
    stratify=temp_df["validated_sentiment"]
)


# ------------------------------------------------------------
# 7. Rename label column
# ------------------------------------------------------------

train_df = train_df.rename(
    columns={
        "validated_sentiment": "label"
    }
)

validation_df = validation_df.rename(
    columns={
        "validated_sentiment": "label"
    }
)

test_df = test_df.rename(
    columns={
        "validated_sentiment": "label"
    }
)


# ------------------------------------------------------------
# 8. Keep required columns
# ------------------------------------------------------------

required_columns = [
    "sentence",
    "aspect",
    "label"
]

train_df = train_df[required_columns]
validation_df = validation_df[required_columns]
test_df = test_df[required_columns]


# ------------------------------------------------------------
# 9. Save datasets
# ------------------------------------------------------------

train_file = OUTPUT_DIR / "human_train.csv"
validation_file = OUTPUT_DIR / "human_validation.csv"
test_file = OUTPUT_DIR / "human_test.csv"


train_df.to_csv(
    train_file,
    index=False
)

validation_df.to_csv(
    validation_file,
    index=False
)

test_df.to_csv(
    test_file,
    index=False
)


# ------------------------------------------------------------
# 10. Print results
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("HUMAN DATASET SPLIT COMPLETE")
print("=" * 70)

print(f"\nTraining records   : {len(train_df)}")
print(f"Validation records : {len(validation_df)}")
print(f"Test records       : {len(test_df)}")


print("\nTraining distribution:")
print(
    train_df["label"].value_counts()
)


print("\nValidation distribution:")
print(
    validation_df["label"].value_counts()
)


print("\nTest distribution:")
print(
    test_df["label"].value_counts()
)


print("\nFiles saved:")

print(train_file)
print(validation_file)
print(test_file)


print("\n" + "=" * 70)