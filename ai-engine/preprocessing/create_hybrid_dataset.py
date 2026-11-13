# ============================================================
# SMARTREVIEW AI
# EXPERIMENT 4
# HYBRID HUMAN + PSEUDO-LABELED DATASET
# ============================================================

import os
import pandas as pd


# ============================================================
# CONFIGURATION
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

HUMAN_DIR = os.path.join(
    DATASET_DIR,
    "human"
)

OUTPUT_FILE = os.path.join(
    DATASET_DIR,
    "hybrid_train.csv"
)

VALID_LABELS = {
    "positive",
    "negative",
    "neutral"
}

HUMAN_WEIGHT = 5.0
PSEUDO_WEIGHT = 1.0


# ============================================================
# HEADER
# ============================================================

print()
print("=" * 70)
print("SMARTREVIEW AI - EXPERIMENT 4")
print("HYBRID HUMAN + PSEUDO-LABELED DATASET")
print("=" * 70)


# ============================================================
# FIND HUMAN TRAINING FILE
# ============================================================

human_train_file = os.path.join(
    HUMAN_DIR,
    "human_train.csv"
)

if not os.path.exists(human_train_file):

    raise FileNotFoundError(
        "\nHuman training file not found:\n"
        + human_train_file
    )


print()
print("Human training file:")
print(human_train_file)


# ============================================================
# LOAD HUMAN TRAINING DATA
# ============================================================

print()
print("Loading human training data...")

human_df = pd.read_csv(
    human_train_file
)

print(
    f"Human records loaded: {len(human_df)}"
)

print(
    "Human columns:"
)

print(
    list(human_df.columns)
)


# ============================================================
# VERIFY HUMAN COLUMNS
# ============================================================

required_human_columns = [
    "sentence",
    "aspect",
    "label"
]

for column in required_human_columns:

    if column not in human_df.columns:

        raise ValueError(
            f"\nColumn '{column}' is missing "
            f"from human_train.csv.\n"
            f"Available columns: "
            f"{list(human_df.columns)}"
        )


# ============================================================
# PREPARE HUMAN DATA
# ============================================================

human_df = human_df[
    [
        "sentence",
        "aspect",
        "label"
    ]
].copy()

human_df["sentence"] = (
    human_df["sentence"]
    .fillna("")
    .astype(str)
    .str.strip()
)

human_df["aspect"] = (
    human_df["aspect"]
    .fillna("")
    .astype(str)
    .str.strip()
)

human_df["label"] = (
    human_df["label"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)

human_df = human_df[
    human_df["label"].isin(VALID_LABELS)
].copy()

human_df = human_df[
    (human_df["sentence"] != "") &
    (human_df["aspect"] != "")
].copy()

human_df["source"] = "human"

human_df["sample_weight"] = HUMAN_WEIGHT


# ============================================================
# FIND PSEUDO-LABELED DATASET
# ============================================================

print()
print("Searching for pseudo-labeled ABSA dataset...")


candidate_files = []


for root, dirs, files in os.walk(DATASET_DIR):

    # Never search inside the human datasets directory
    dirs[:] = [
        d for d in dirs
        if d.lower() != "human"
    ]

    for file in files:

        if not file.lower().endswith(".csv"):
            continue

        full_path = os.path.join(
            root,
            file
        )

        # Don't use our future output
        if os.path.abspath(full_path) == os.path.abspath(
            OUTPUT_FILE
        ):
            continue

        try:

            temp_df = pd.read_csv(
                full_path,
                nrows=5
            )

            columns = set(
                temp_df.columns
            )

            # We are looking for a dataset containing
            # sentence + aspect + sentiment label.
            has_sentence = (
                "sentence" in columns
            )

            has_aspect = (
                "aspect" in columns
            )

            has_sentiment = (
                "aspect_sentiment" in columns
                or "sentiment" in columns
                or "label" in columns
            )

            if (
                has_sentence
                and has_aspect
                and has_sentiment
            ):

                candidate_files.append(
                    full_path
                )

        except Exception:
            pass


# ============================================================
# DISPLAY CANDIDATES
# ============================================================

print()
print("Candidate ABSA datasets found:")

if not candidate_files:

    raise FileNotFoundError(
        "\nNo pseudo-labeled ABSA dataset was found.\n"
        "The dataset must contain:\n"
        "sentence + aspect + sentiment/label"
    )


for file in candidate_files:

    print(
        " -",
        os.path.relpath(
            file,
            BASE_DIR
        )
    )


# ============================================================
# SELECT PSEUDO DATASET
# ============================================================

# Prefer files containing "aspect_sentiment"
# in their name.

preferred = [
    f for f in candidate_files
    if "aspect_sentiment" in
    os.path.basename(f).lower()
]


if preferred:

    pseudo_file = preferred[0]

else:

    # Otherwise select the largest candidate.
    file_sizes = [
        (
            os.path.getsize(f),
            f
        )
        for f in candidate_files
    ]

    file_sizes.sort(
        reverse=True
    )

    pseudo_file = file_sizes[0][1]


print()
print("Selected pseudo-labeled dataset:")

print(
    pseudo_file
)


# ============================================================
# LOAD PSEUDO DATA
# ============================================================

print()
print("Loading pseudo-labeled data...")

pseudo_df = pd.read_csv(
    pseudo_file
)

print(
    f"Pseudo records loaded: "
    f"{len(pseudo_df)}"
)

print(
    "Pseudo columns:"
)

print(
    list(pseudo_df.columns)
)


# ============================================================
# DETERMINE LABEL COLUMN
# ============================================================

if "aspect_sentiment" in pseudo_df.columns:

    pseudo_label_column = (
        "aspect_sentiment"
    )

elif "sentiment" in pseudo_df.columns:

    pseudo_label_column = (
        "sentiment"
    )

elif "label" in pseudo_df.columns:

    pseudo_label_column = (
        "label"
    )

else:

    raise ValueError(
        "\nCould not find sentiment column "
        "in pseudo dataset."
    )


print()
print(
    "Pseudo sentiment column:",
    pseudo_label_column
)


# ============================================================
# PREPARE PSEUDO DATA
# ============================================================

pseudo_df = pseudo_df[
    [
        "sentence",
        "aspect",
        pseudo_label_column
    ]
].copy()

pseudo_df = pseudo_df.rename(
    columns={
        pseudo_label_column: "label"
    }
)

pseudo_df["sentence"] = (
    pseudo_df["sentence"]
    .fillna("")
    .astype(str)
    .str.strip()
)

pseudo_df["aspect"] = (
    pseudo_df["aspect"]
    .fillna("")
    .astype(str)
    .str.strip()
)

pseudo_df["label"] = (
    pseudo_df["label"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)

pseudo_df = pseudo_df[
    pseudo_df["label"].isin(
        VALID_LABELS
    )
].copy()

pseudo_df = pseudo_df[
    (pseudo_df["sentence"] != "") &
    (pseudo_df["aspect"] != "")
].copy()

pseudo_df["source"] = "pseudo"

pseudo_df["sample_weight"] = PSEUDO_WEIGHT


# ============================================================
# CREATE UNIQUE PAIR KEY
# ============================================================

def make_key(df):

    return (
        df["sentence"]
        .str.lower()
        .str.strip()
        + "|||"
        +
        df["aspect"]
        .str.lower()
        .str.strip()
    )


human_df["pair_key"] = make_key(
    human_df
)

pseudo_df["pair_key"] = make_key(
    pseudo_df
)


# ============================================================
# REMOVE HUMAN PAIRS FROM PSEUDO DATA
# ============================================================

human_keys = set(
    human_df["pair_key"]
)

before = len(
    pseudo_df
)

pseudo_df = pseudo_df[
    ~pseudo_df["pair_key"].isin(
        human_keys
    )
].copy()

removed = (
    before
    - len(pseudo_df)
)


print()
print(
    "Pseudo records overlapping "
    "human training data:",
    removed
)


# ============================================================
# COMBINE
# ============================================================

hybrid_df = pd.concat(
    [
        pseudo_df,
        human_df
    ],
    ignore_index=True
)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

before_duplicates = len(
    hybrid_df
)

hybrid_df = hybrid_df.drop_duplicates(
    subset=["pair_key"],
    keep="last"
).reset_index(
    drop=True
)

duplicates_removed = (
    before_duplicates
    - len(hybrid_df)
)


print(
    "Additional duplicate pairs removed:",
    duplicates_removed
)


# ============================================================
# SHUFFLE
# ============================================================

hybrid_df = hybrid_df.sample(
    frac=1,
    random_state=42
).reset_index(
    drop=True
)


# ============================================================
# STATISTICS
# ============================================================

print()
print("=" * 70)
print("HYBRID DATASET STATISTICS")
print("=" * 70)

print()
print(
    "Total records:",
    len(hybrid_df)
)

print()
print("Label distribution:")

print(
    hybrid_df["label"].value_counts()
)

print()
print("Source distribution:")

print(
    hybrid_df["source"].value_counts()
)

print()
print("Training weight contribution:")

print(
    hybrid_df
    .groupby("source")["sample_weight"]
    .sum()
)


# ============================================================
# SAVE
# ============================================================

hybrid_df = hybrid_df[
    [
        "sentence",
        "aspect",
        "label",
        "source",
        "sample_weight"
    ]
]

hybrid_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# FINISHED
# ============================================================

print()
print("=" * 70)
print("HYBRID DATASET CREATED SUCCESSFULLY")
print("=" * 70)

print()
print(
    "Saved to:"
)

print(
    OUTPUT_FILE
)

print()
print(
    "Human sample weight :",
    HUMAN_WEIGHT
)

print(
    "Pseudo sample weight:",
    PSEUDO_WEIGHT
)

print()
print(
    "Human validation and test datasets "
    "were NOT modified."
)

print()
print(
    "Experiment 4 - Step 1 COMPLETE."
)