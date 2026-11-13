# ============================================================
# SMARTREVIEW AI
# EXPERIMENT 4 - IMPROVED HYBRID DATASET
# COMBINING HUMAN, AUGMENTED, AND PSEUDO DATA
# WITH SOURCE AND BALANCED CLASS WEIGHTING
# ============================================================

import os
import random
import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)

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

HUMAN_TRAIN = os.path.join(
    HUMAN_DIR,
    "human_train.csv"
)

AUGMENTED_FILE = os.path.join(
    HUMAN_DIR,
    "augmented_human_train.csv"
)

HUMAN_VAL = os.path.join(
    HUMAN_DIR,
    "human_validation.csv"
)

HUMAN_TEST = os.path.join(
    HUMAN_DIR,
    "human_test.csv"
)

OUTPUT_FILE = os.path.join(
    DATASET_DIR,
    "improved_hybrid_train.csv"
)

VALID_LABELS = {
    "positive",
    "negative",
    "neutral"
}

HUMAN_WEIGHT = 5.0
AUGMENTED_WEIGHT = 4.0
PSEUDO_WEIGHT = 1.0


# ============================================================
# HEADER
# ============================================================

print()
print("=" * 70)
print("SMARTREVIEW AI - EXPERIMENT 4")
print("CREATE IMPROVED HYBRID DATASET (HUMAN + AUGMENTED + PSEUDO)")
print("=" * 70)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def make_pair_key(df):
    """
    Generate normalized pair key from sentence and aspect.
    """
    return (
        df["sentence"]
        .astype(str)
        .str.lower()
        .str.strip()
        + "|||"
        + df["aspect"]
        .astype(str)
        .str.lower()
        .str.strip()
    )


# ============================================================
# STEP 1: LOAD HUMAN TRAINING DATA
# ============================================================

print()
print("-" * 70)
print("STEP 1: LOADING HUMAN TRAINING DATA")
print("-" * 70)

if not os.path.exists(HUMAN_TRAIN):

    raise FileNotFoundError(
        f"\nHuman training file not found:\n{HUMAN_TRAIN}"
    )

print(f"Reading: {HUMAN_TRAIN}")

human_df = pd.read_csv(HUMAN_TRAIN)

print(f"Human records loaded: {len(human_df)}")

required_columns = ["sentence", "aspect", "label"]

for col in required_columns:

    if col not in human_df.columns:

        raise ValueError(
            f"Missing required column '{col}' in human training file: {HUMAN_TRAIN}"
        )

human_df = human_df[required_columns].copy()

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

human_df["source_weight"] = HUMAN_WEIGHT

human_df["pair_key"] = make_pair_key(human_df)

print(f"Valid human training records: {len(human_df)}")
print(f"Human label distribution:\n{human_df['label'].value_counts()}")


# ============================================================
# STEP 2: CHECK AND LOAD AUGMENTED HUMAN DATA
# ============================================================

print()
print("-" * 70)
print("STEP 2: CHECKING FOR AUGMENTED HUMAN TRAINING DATA")
print("-" * 70)

if os.path.exists(AUGMENTED_FILE):

    print(f"Augmented human training file found: {AUGMENTED_FILE}")

    augmented_df = pd.read_csv(AUGMENTED_FILE)

    print(f"Augmented records loaded: {len(augmented_df)}")

    for col in required_columns:

        if col not in augmented_df.columns:

            raise ValueError(
                f"Missing required column '{col}' in augmented file: {AUGMENTED_FILE}"
            )

    augmented_df = augmented_df[required_columns].copy()

    augmented_df["sentence"] = (
        augmented_df["sentence"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    augmented_df["aspect"] = (
        augmented_df["aspect"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    augmented_df["label"] = (
        augmented_df["label"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    augmented_df = augmented_df[
        augmented_df["label"].isin(VALID_LABELS)
    ].copy()

    augmented_df = augmented_df[
        (augmented_df["sentence"] != "") &
        (augmented_df["aspect"] != "")
    ].copy()

    augmented_df["source"] = "augmented"

    augmented_df["source_weight"] = AUGMENTED_WEIGHT

    augmented_df["pair_key"] = make_pair_key(augmented_df)

    print(f"Valid augmented records: {len(augmented_df)}")
    print(f"Augmented label distribution:\n{augmented_df['label'].value_counts()}")

else:

    print("WARNING: Augmented human training file not found:")
    print(f"  {AUGMENTED_FILE}")
    print("Continuing pipeline without augmented data.")

    augmented_df = pd.DataFrame(
        columns=[
            "sentence",
            "aspect",
            "label",
            "source",
            "source_weight",
            "pair_key"
        ]
    )


# ============================================================
# STEP 3: FIND PSEUDO-LABELED DATASET
# ============================================================

print()
print("-" * 70)
print("STEP 3: SEARCHING FOR PSEUDO-LABELED DATASET")
print("-" * 70)

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

        # Skip hybrid output files and augmented files to prevent leakage
        abs_path = os.path.abspath(full_path)

        if abs_path in (
            os.path.abspath(OUTPUT_FILE),
            os.path.abspath(os.path.join(DATASET_DIR, "hybrid_train.csv"))
        ):
            continue

        if file.lower() in (
            "hybrid_train.csv",
            "improved_hybrid_train.csv",
            "augmented_human_train.csv",
            "human_train.csv",
            "human_validation.csv",
            "human_test.csv"
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

print(f"Found {len(candidate_files)} candidate dataset(s):")

for cf in candidate_files:

    print(f"  - {os.path.relpath(cf, BASE_DIR)}")

if not candidate_files:

    raise FileNotFoundError(
        "\nNo pseudo-labeled ABSA dataset was found.\n"
        "The dataset must contain: sentence + aspect + sentiment/label"
    )

preferred = [
    f for f in candidate_files
    if "aspect_sentiment" in os.path.basename(f).lower()
]

if preferred:

    pseudo_file = preferred[0]

else:

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
print(f"Selected pseudo dataset: {pseudo_file}")


# ============================================================
# STEP 4: LOAD PSEUDO-LABELED DATA
# ============================================================

print()
print("-" * 70)
print("STEP 4: LOADING PSEUDO-LABELED DATA")
print("-" * 70)

pseudo_df = pd.read_csv(pseudo_file)

print(f"Raw pseudo records loaded: {len(pseudo_df)}")

if "aspect_sentiment" in pseudo_df.columns:
    pseudo_label_col = "aspect_sentiment"
elif "sentiment" in pseudo_df.columns:
    pseudo_label_col = "sentiment"
elif "label" in pseudo_df.columns:
    pseudo_label_col = "label"
else:
    raise ValueError(
        f"Could not find sentiment column in pseudo dataset: {pseudo_file}"
    )

print(f"Identified sentiment column: '{pseudo_label_col}'")

pseudo_df = pseudo_df[
    [
        "sentence",
        "aspect",
        pseudo_label_col
    ]
].copy()

pseudo_df = pseudo_df.rename(
    columns={
        pseudo_label_col: "label"
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
    pseudo_df["label"].isin(VALID_LABELS)
].copy()

pseudo_df = pseudo_df[
    (pseudo_df["sentence"] != "") &
    (pseudo_df["aspect"] != "")
].copy()

pseudo_df["source"] = "pseudo"

pseudo_df["source_weight"] = PSEUDO_WEIGHT

pseudo_df["pair_key"] = make_pair_key(pseudo_df)

print(f"Valid pseudo records: {len(pseudo_df)}")
print(f"Pseudo label distribution:\n{pseudo_df['label'].value_counts()}")


# ============================================================
# STEP 5 & 6: PREVENT DATA LEAKAGE (EXCLUDE HUMAN PAIRS)
# ============================================================

print()
print("-" * 70)
print("STEP 5 & 6: DATA LEAKAGE PREVENTION")
print("-" * 70)

human_leakage_keys = set(human_df["pair_key"])

print(f"Human train unique keys: {len(human_leakage_keys)}")

if not augmented_df.empty:

    augmented_keys = set(augmented_df["pair_key"])

    human_leakage_keys.update(augmented_keys)

    print(f"Augmented human unique keys: {len(augmented_keys)}")

if os.path.exists(HUMAN_VAL):

    val_df = pd.read_csv(HUMAN_VAL)

    val_keys = set(make_pair_key(val_df))

    human_leakage_keys.update(val_keys)

    print(f"Human validation unique keys added: {len(val_keys)}")

else:

    print(f"WARNING: Human validation file not found at: {HUMAN_VAL}")

if os.path.exists(HUMAN_TEST):

    test_df = pd.read_csv(HUMAN_TEST)

    test_keys = set(make_pair_key(test_df))

    human_leakage_keys.update(test_keys)

    print(f"Human test unique keys added: {len(test_keys)}")

else:

    print(f"WARNING: Human test file not found at: {HUMAN_TEST}")

print(f"Total human keys to exclude from pseudo data: {len(human_leakage_keys)}")

pseudo_before_leakage = len(pseudo_df)

pseudo_df = pseudo_df[
    ~pseudo_df["pair_key"].isin(human_leakage_keys)
].copy()

leakage_removed = pseudo_before_leakage - len(pseudo_df)

print(f"Pseudo records removed to prevent leakage: {leakage_removed}")
print(f"Remaining pseudo records: {len(pseudo_df)}")


# ============================================================
# STEP 7 & 8: COMBINE DATAFRAMES AND DEDUPLICATE
# ============================================================

print()
print("-" * 70)
print("STEP 7 & 8: COMBINING DATAFRAMES AND DEDUPLICATING")
print("-" * 70)

# Ordering: pseudo first, then augmented, then human last.
# With keep='last', human data takes highest precedence, followed by augmented.
dfs_to_combine = [
    df for df in [pseudo_df, augmented_df, human_df]
    if not df.empty
]

combined_df = pd.concat(
    dfs_to_combine,
    ignore_index=True
)

before_dedup = len(combined_df)

combined_df = combined_df.drop_duplicates(
    subset=["pair_key"],
    keep="last"
).reset_index(
    drop=True
)

dedup_removed = before_dedup - len(combined_df)

print(f"Total records before deduplication: {before_dedup}")
print(f"Duplicate pairs removed (human/augmented preserved): {dedup_removed}")
print(f"Total records after deduplication: {len(combined_df)}")


# ============================================================
# STEP 9: COMPUTE BALANCED CLASS WEIGHTS
# ============================================================

print()
print("-" * 70)
print("STEP 9: COMPUTING BALANCED CLASS WEIGHTS")
print("-" * 70)

total_records = len(combined_df)

num_classes = len(VALID_LABELS)

class_weight_dict = {}

print(f"Total records (N): {total_records}")
print(f"Number of classes (K): {num_classes}")

for label in sorted(list(VALID_LABELS)):

    count_c = (combined_df["label"] == label).sum()

    if count_c > 0:

        weight_c = float(total_records) / (num_classes * count_c)

    else:

        weight_c = 1.0

    class_weight_dict[label] = weight_c

    print(
        f"  Class '{label}': count = {count_c}, "
        f"weight = {weight_c:.4f}"
    )

combined_df["class_weight"] = combined_df["label"].map(
    class_weight_dict
)


# ============================================================
# STEP 10: COMPUTE FINAL WEIGHTS
# ============================================================

print()
print("-" * 70)
print("STEP 10: COMPUTING FINAL SAMPLE WEIGHTS")
print("-" * 70)

combined_df["final_weight"] = (
    combined_df["source_weight"] * combined_df["class_weight"]
)

print("Sample weights computed: final_weight = source_weight * class_weight")


# ============================================================
# STEP 11: CLEAN TEXT FIELDS
# ============================================================

print()
print("-" * 70)
print("STEP 11: FINAL TEXT CLEANING AND VALIDATION")
print("-" * 70)

combined_df["sentence"] = (
    combined_df["sentence"]
    .fillna("")
    .astype(str)
    .str.strip()
)

combined_df["aspect"] = (
    combined_df["aspect"]
    .fillna("")
    .astype(str)
    .str.strip()
)

combined_df["label"] = (
    combined_df["label"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.strip()
)

before_clean = len(combined_df)

combined_df = combined_df[
    (combined_df["sentence"] != "") &
    (combined_df["aspect"] != "") &
    (combined_df["label"].isin(VALID_LABELS))
].copy()

cleaned_out = before_clean - len(combined_df)

print(f"Records cleaned/dropped: {cleaned_out}")
print(f"Valid records remaining: {len(combined_df)}")


# ============================================================
# STEP 12: SHUFFLE DATASET
# ============================================================

print()
print("-" * 70)
print("STEP 12: SHUFFLING DATASET")
print("-" * 70)

combined_df = combined_df.sample(
    frac=1.0,
    random_state=SEED
).reset_index(
    drop=True
)

print(f"Dataset shuffled reproducibly with SEED={SEED}")


# ============================================================
# STEP 13: SAVE TO OUTPUT FILE
# ============================================================

print()
print("-" * 70)
print("STEP 13: SAVING OUTPUT FILE")
print("-" * 70)

output_columns = [
    "sentence",
    "aspect",
    "label",
    "source",
    "source_weight",
    "class_weight",
    "final_weight"
]

combined_df = combined_df[output_columns]

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

combined_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print(f"Saved {len(combined_df)} records to:\n  {OUTPUT_FILE}")


# ============================================================
# STEP 14: DETAILED DATASET STATISTICS
# ============================================================

print()
print("=" * 70)
print("IMPROVED HYBRID DATASET DETAILED STATISTICS")
print("=" * 70)

print()
print(f"Total Records: {len(combined_df):,}")

print()
print("Records Per Source:")
source_counts = combined_df["source"].value_counts()
for src, count in source_counts.items():
    pct = (count / len(combined_df)) * 100
    print(f"  {src:<12}: {count:6d} ({pct:5.1f}%)")

print()
print("Records Per Label:")
label_counts = combined_df["label"].value_counts()
for lbl, count in label_counts.items():
    pct = (count / len(combined_df)) * 100
    print(f"  {lbl:<12}: {count:6d} ({pct:5.1f}%)")

print()
print("Source x Label Cross-Tabulation:")
print(pd.crosstab(combined_df["source"], combined_df["label"], margins=True))

print()
print("Source Weights:")
print(f"  Human     : {HUMAN_WEIGHT}")
print(f"  Augmented : {AUGMENTED_WEIGHT}")
print(f"  Pseudo    : {PSEUDO_WEIGHT}")

print()
print("Balanced Class Weights:")
for lbl, w in sorted(class_weight_dict.items()):
    print(f"  {lbl:<12}: {w:.4f}")

print()
print("Final Weight Distribution by Source:")
weight_summary = (
    combined_df.groupby("source")["final_weight"]
    .agg(["count", "mean", "std", "min", "median", "max", "sum"])
    .round(4)
)
print(weight_summary)

print()
print("Effective Training Contribution per Source (by final_weight sum):")
total_final_weight = combined_df["final_weight"].sum()
for src, group in combined_df.groupby("source"):
    src_weight_sum = group["final_weight"].sum()
    src_count = len(group)
    raw_pct = (src_count / len(combined_df)) * 100
    effective_pct = (src_weight_sum / total_final_weight) * 100
    multiplier = (effective_pct / raw_pct) if raw_pct > 0 else 1.0
    print(
        f"  {src:<12}: "
        f"count = {src_count:6d} ({raw_pct:5.1f}%) | "
        f"weight sum = {src_weight_sum:10.2f} ({effective_pct:5.1f}%) | "
        f"boost = {multiplier:.2f}x"
    )

print()
print("=" * 70)
print("IMPROVED HYBRID DATASET CREATED SUCCESSFULLY")
print("=" * 70)
print(f"Output File: {OUTPUT_FILE}")
print()
