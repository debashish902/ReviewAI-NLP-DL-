import pandas as pd
from sklearn.model_selection import train_test_split


INPUT_FILE = "ai-engine/datasets/aspect_sentiment_sample.csv"
VALIDATION_FILE = "ai-engine/datasets/validation_dataset.csv"

TRAIN_FILE = "ai-engine/datasets/absa_train.csv"
VAL_FILE = "ai-engine/datasets/absa_validation.csv"
TEST_FILE = "ai-engine/datasets/absa_test.csv"


print("Loading aspect-sentiment dataset...")

df = pd.read_csv(INPUT_FILE)

print("Total aspect-sentence pairs:", len(df))


# -------------------------------------------------
# Clean labels
# -------------------------------------------------

df["aspect_sentiment"] = (
    df["aspect_sentiment"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)

df["sentence"] = (
    df["sentence"]
    .fillna("")
    .astype(str)
)

df["aspect"] = (
    df["aspect"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)


# Keep only valid sentiment labels
df = df[
    df["aspect_sentiment"].isin(
        ["positive", "neutral", "negative"]
    )
]

# Remove empty sentences/aspects
df = df[
    (df["sentence"].str.strip() != "")
    &
    (df["aspect"].str.strip() != "")
]


# -------------------------------------------------
# Remove manually validated examples
# -------------------------------------------------

print("Loading manually validated records...")

validation_df = pd.read_csv(VALIDATION_FILE)

validation_keys = set(
    zip(
        validation_df["sentence"].astype(str).str.strip(),
        validation_df["aspect"].astype(str).str.strip().str.lower()
    )
)


def make_key(row):
    return (
        row["sentence"].strip(),
        row["aspect"].strip().lower()
    )


df["validation_key"] = df.apply(
    make_key,
    axis=1
)


before = len(df)

df = df[
    ~df["validation_key"].isin(validation_keys)
].copy()

df.drop(
    columns=["validation_key"],
    inplace=True
)

print(
    "Removed manually validated pairs:",
    before - len(df)
)

print(
    "Remaining records for training/testing:",
    len(df)
)


# -------------------------------------------------
# Select useful columns
# -------------------------------------------------

df = df[
    [
        "sentence",
        "aspect",
        "aspect_sentiment"
    ]
]


# -------------------------------------------------
# First split: 80% train, 20% temporary
# -------------------------------------------------

train_df, temp_df = train_test_split(
    df,
    test_size=0.20,
    random_state=42,
    stratify=df["aspect_sentiment"]
)


# -------------------------------------------------
# Second split: 10% validation, 10% test
# -------------------------------------------------

val_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    random_state=42,
    stratify=temp_df["aspect_sentiment"]
)


# -------------------------------------------------
# Reset indexes
# -------------------------------------------------

train_df = train_df.reset_index(drop=True)
val_df = val_df.reset_index(drop=True)
test_df = test_df.reset_index(drop=True)


# -------------------------------------------------
# Save datasets
# -------------------------------------------------

train_df.to_csv(
    TRAIN_FILE,
    index=False
)

val_df.to_csv(
    VAL_FILE,
    index=False
)

test_df.to_csv(
    TEST_FILE,
    index=False
)


# -------------------------------------------------
# Display results
# -------------------------------------------------

print("\n========== TRAINING DATA SPLIT ==========")

print("\nTrain records:", len(train_df))

print("\nValidation records:", len(val_df))

print("\nTest records:", len(test_df))


print("\nTrain distribution:")
print(
    train_df["aspect_sentiment"]
    .value_counts()
)


print("\nValidation distribution:")
print(
    val_df["aspect_sentiment"]
    .value_counts()
)


print("\nTest distribution:")
print(
    test_df["aspect_sentiment"]
    .value_counts()
)


print("\nSaved files:")

print(TRAIN_FILE)
print(VAL_FILE)
print(TEST_FILE)

print(
    "\n========================================="
)