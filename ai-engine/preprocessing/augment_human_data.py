import os
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# SMARTREVIEW AI
# DATA AUGMENTATION FOR HUMAN TRAINING DATA (EDA)
# ============================================================

SEED = 42

random.seed(SEED)
np.random.seed(SEED)

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "datasets" / "human" / "human_train.csv"

OUTPUT_FILE = BASE_DIR / "datasets" / "human" / "augmented_human_train.csv"

OUTPUT_DIR = OUTPUT_FILE.parent

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPER FUNCTIONS - ASPECT PROTECTION & TOKENIZATION
# ============================================================

def clean_word(token):
    """
    Strip leading and trailing punctuation from a token for matching.
    """
    return re.sub(r"^[^\w]+|[^\w]+$", "", token).lower()


def identify_aspect_indices(words, aspect):
    """
    Identify word indices in `words` that correspond to the aspect term.
    Protects multi-word aspect sequences, exact word matches,
    inflections (plurals/singulars), and hyphenated terms.
    """
    aspect_lower = str(aspect).lower().strip()
    aspect_tokens = aspect_lower.split()
    protected = set()
    cleaned_tokens = [clean_word(w) for w in words]

    # Check multi-word aspect sequence
    if len(aspect_tokens) > 1:
        n = len(aspect_tokens)
        for i in range(len(words) - n + 1):
            if cleaned_tokens[i : i + n] == aspect_tokens:
                for j in range(n):
                    protected.add(i + j)

    # Check individual token matches and inflections
    for i, w in enumerate(words):
        c = cleaned_tokens[i]

        # Exact match or token within multi-word aspect
        if c == aspect_lower or c in aspect_tokens:
            protected.add(i)

        # Plural / singular variants
        elif c == aspect_lower + "s" or c == aspect_lower + "es":
            protected.add(i)

        elif aspect_lower.endswith("s") and c == aspect_lower[:-1]:
            protected.add(i)

        elif aspect_lower.endswith("ies") and c == aspect_lower[:-3] + "y":
            protected.add(i)

        elif aspect_lower.endswith("y") and c == aspect_lower[:-1] + "ies":
            protected.add(i)

        # Hyphenated or embedded whole-word match
        elif re.search(r"\b" + re.escape(aspect_lower) + r"\b", w.lower()):
            protected.add(i)

    return protected


# ============================================================
# AUGMENTATION TECHNIQUES (ASPECT-PRESERVING)
# ============================================================

def augment_random_deletion(words, protected_indices):
    """
    Random Word Deletion:
    Remove 1 randomly chosen non-aspect word from the sentence.
    Skip if sentence has fewer than 4 words.
    """
    if len(words) < 4:
        return None

    non_aspect_indices = [
        i for i in range(len(words)) if i not in protected_indices
    ]

    if not non_aspect_indices:
        return None

    del_idx = random.choice(non_aspect_indices)

    new_words = [words[i] for i in range(len(words)) if i != del_idx]

    return " ".join(new_words)


def augment_random_swap(words, protected_indices):
    """
    Random Word Swap:
    Swap two randomly chosen adjacent non-aspect words.
    Skip if sentence has fewer than 4 words.
    """
    if len(words) < 4:
        return None

    # Find adjacent pairs where neither word is an aspect term
    candidate_pairs = [
        (i, i + 1)
        for i in range(len(words) - 1)
        if i not in protected_indices and (i + 1) not in protected_indices
    ]

    if not candidate_pairs:
        return None

    # Filter for pairs with different words if possible to avoid identical sentences
    distinct_pairs = [
        (i, j)
        for (i, j) in candidate_pairs
        if words[i].lower() != words[j].lower()
    ]

    chosen_pair = random.choice(
        distinct_pairs if distinct_pairs else candidate_pairs
    )

    new_words = list(words)
    new_words[chosen_pair[0]], new_words[chosen_pair[1]] = (
        new_words[chosen_pair[1]],
        new_words[chosen_pair[0]],
    )

    return " ".join(new_words)


def augment_random_repetition(words, protected_indices):
    """
    Random Word Repetition:
    Pick a random non-aspect word and insert a copy of it right after its position.
    """
    if not words:
        return None

    non_aspect_indices = [
        i for i in range(len(words)) if i not in protected_indices
    ]

    if not non_aspect_indices:
        return None

    rep_idx = random.choice(non_aspect_indices)

    new_words = list(words)
    new_words.insert(rep_idx + 1, words[rep_idx])

    return " ".join(new_words)


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    print("=" * 70)
    print("SMARTREVIEW AI - HUMAN DATA AUGMENTATION (EDA)")
    print("=" * 70)

    print(f"\nConfiguration:")
    print(f"  Random Seed:  {SEED}")
    print(f"  Input File:   {INPUT_FILE}")
    print(f"  Output File:  {OUTPUT_FILE}")

    # ------------------------------------------------------------
    # 1. Load input dataset
    # ------------------------------------------------------------
    print("\nLoading human training data...")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found at: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    print(f"Total original training rows loaded: {len(df)}")
    print("Columns:", list(df.columns))

    required_cols = {"sentence", "aspect", "label"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError(f"Input file must contain columns: {required_cols}")

    # ------------------------------------------------------------
    # 2. Generate augmentations
    # ------------------------------------------------------------
    print("\nApplying aspect-preserving data augmentation...")

    augmented_rows = []
    deletion_count = 0
    swap_count = 0
    repetition_count = 0
    skipped_count = 0

    for idx, row in df.iterrows():
        orig_sentence = str(row["sentence"]).strip()
        aspect = str(row["aspect"]).strip()
        label = str(row["label"]).strip()

        words = orig_sentence.split()

        if not words:
            continue

        protected_indices = identify_aspect_indices(words, aspect)

        # Technique 1: Random Deletion
        del_sentence = augment_random_deletion(words, protected_indices)
        if (
            del_sentence
            and del_sentence.strip()
            and del_sentence.strip() != orig_sentence
        ):
            augmented_rows.append(
                {
                    "sentence": del_sentence.strip(),
                    "aspect": aspect,
                    "label": label,
                }
            )
            deletion_count += 1
        else:
            skipped_count += 1

        # Technique 2: Random Swap
        swap_sentence = augment_random_swap(words, protected_indices)
        if (
            swap_sentence
            and swap_sentence.strip()
            and swap_sentence.strip() != orig_sentence
        ):
            augmented_rows.append(
                {
                    "sentence": swap_sentence.strip(),
                    "aspect": aspect,
                    "label": label,
                }
            )
            swap_count += 1
        else:
            skipped_count += 1

        # Technique 3: Random Repetition
        rep_sentence = augment_random_repetition(words, protected_indices)
        if (
            rep_sentence
            and rep_sentence.strip()
            and rep_sentence.strip() != orig_sentence
        ):
            augmented_rows.append(
                {
                    "sentence": rep_sentence.strip(),
                    "aspect": aspect,
                    "label": label,
                }
            )
            repetition_count += 1
        else:
            skipped_count += 1

    # ------------------------------------------------------------
    # 3. Create DataFrame and deduplicate
    # ------------------------------------------------------------
    aug_df = pd.DataFrame(
        augmented_rows, columns=["sentence", "aspect", "label"]
    )

    print(f"\nAugmentation generation summary:")
    print(f"  Word Deletions generated:      {deletion_count}")
    print(f"  Word Swaps generated:          {swap_count}")
    print(f"  Word Repetitions generated:    {repetition_count}")
    print(f"  Augmentation attempts skipped: {skipped_count}")
    print(f"  Total raw augmented rows:      {len(aug_df)}")

    # Remove duplicates if any
    before_dedup = len(aug_df)
    aug_df = aug_df.drop_duplicates(
        subset=["sentence", "aspect", "label"]
    ).reset_index(drop=True)
    dedup_dropped = before_dedup - len(aug_df)

    if dedup_dropped > 0:
        print(f"  Duplicate augmented rows removed: {dedup_dropped}")

    # ------------------------------------------------------------
    # 4. Save augmented dataset
    # ------------------------------------------------------------
    print(f"\nSaving augmented data to {OUTPUT_FILE}...")

    aug_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Successfully saved {len(aug_df)} augmented rows to {OUTPUT_FILE}")

    # ------------------------------------------------------------
    # 5. Final Statistics
    # ------------------------------------------------------------
    print("\n" + "=" * 70)
    print("FINAL AUGMENTATION STATISTICS")
    print("=" * 70)
    print(f"Total augmented records: {len(aug_df)}")

    print("\nPer-label distribution:")
    label_dist = aug_df["label"].value_counts()
    for lbl, cnt in label_dist.items():
        pct = (cnt / len(aug_df)) * 100 if len(aug_df) > 0 else 0
        print(f"  {lbl:<10}: {cnt:>5} ({pct:5.1f}%)")

    print("\nPer-aspect distribution (top 10):")
    aspect_dist = aug_df["aspect"].value_counts().head(10)
    for asp, cnt in aspect_dist.items():
        print(f"  {asp:<15}: {cnt:>5}")

    print("=" * 70)
    print("AUGMENTATION COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
