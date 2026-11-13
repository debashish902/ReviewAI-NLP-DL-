import pandas as pd

INPUT_FILE = "ai-engine/datasets/aspect_sentiment_sample.csv"

OUTPUT_FILE = "ai-engine/datasets/validation_dataset.csv"

VALIDATION_SIZE = 300


print("Loading aspect-sentiment dataset...")

df = pd.read_csv(INPUT_FILE)

print("Total records:", len(df))


# Remove records with missing values
df = df.dropna(
    subset=["sentence", "aspect", "aspect_sentiment"]
)


# -----------------------------------------
# Stratified sampling
# -----------------------------------------

samples_per_class = VALIDATION_SIZE // 3

validation_parts = []

for sentiment in ["positive", "neutral", "negative"]:

    sentiment_df = df[
        df["aspect_sentiment"] == sentiment
    ]

    sample_size = min(
        samples_per_class,
        len(sentiment_df)
    )

    sample = sentiment_df.sample(
        n=sample_size,
        random_state=42
    )

    validation_parts.append(sample)


validation_df = pd.concat(
    validation_parts,
    ignore_index=True
)


# Shuffle final dataset
validation_df = validation_df.sample(
    frac=1,
    random_state=42
).reset_index(drop=True)


# -----------------------------------------
# Add manual validation column
# -----------------------------------------

validation_df["validated_sentiment"] = ""


# Save
validation_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\n========== VALIDATION DATASET ==========")

print(
    "Validation records:",
    len(validation_df)
)

print("\nAutomatic sentiment distribution:")

print(
    validation_df[
        "aspect_sentiment"
    ].value_counts()
)

print("\nColumns:")

print(
    validation_df.columns.tolist()
)

print("\nSample records:\n")

print(
    validation_df[
        [
            "sentence",
            "aspect",
            "aspect_sentiment",
            "validated_sentiment"
        ]
    ]
    .head(15)
    .to_string(index=False)
)

print("\nSaved to:")

print(OUTPUT_FILE)

print(
    "\n========================================"
)