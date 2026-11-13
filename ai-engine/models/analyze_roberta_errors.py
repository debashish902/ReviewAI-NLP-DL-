import pandas as pd
from pathlib import Path


# ============================================================
# SMARTREVIEW AI
# RoBERTa Error Analysis
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "ai-engine" / "datasets" / "roberta_human_predictions.csv"
OUTPUT_FILE = BASE_DIR / "ai-engine" / "datasets" / "roberta_error_analysis.csv"


print("=" * 70)
print("SMARTREVIEW AI - RoBERTa ERROR ANALYSIS")
print("=" * 70)


# ------------------------------------------------------------
# 1. Load predictions
# ------------------------------------------------------------

print("\nLoading predictions...")

df = pd.read_csv(INPUT_FILE)

print(f"Total records loaded: {len(df)}")


# ------------------------------------------------------------
# 2. Keep only valid human labels
# ------------------------------------------------------------

valid_labels = ["positive", "neutral", "negative"]

df = df[
    df["validated_sentiment"].isin(valid_labels)
    & df["predicted_sentiment"].isin(valid_labels)
].copy()

print(f"Valid evaluation records: {len(df)}")


# ------------------------------------------------------------
# 3. Identify errors
# ------------------------------------------------------------

errors = df[
    df["validated_sentiment"] != df["predicted_sentiment"]
].copy()

correct = df[
    df["validated_sentiment"] == df["predicted_sentiment"]
].copy()


print(f"Correct predictions: {len(correct)}")
print(f"Incorrect predictions: {len(errors)}")


# ------------------------------------------------------------
# 4. Create error type
# ------------------------------------------------------------

errors["error_type"] = (
    errors["validated_sentiment"]
    + " -> "
    + errors["predicted_sentiment"]
)


# ------------------------------------------------------------
# 5. Error distribution
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("ERROR DISTRIBUTION")
print("=" * 70)

error_counts = errors["error_type"].value_counts()

print(error_counts.to_string())


# ------------------------------------------------------------
# 6. Errors by actual class
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("ERRORS BY ACTUAL SENTIMENT")
print("=" * 70)

actual_errors = errors["validated_sentiment"].value_counts()

print(actual_errors.to_string())


# ------------------------------------------------------------
# 7. Errors by predicted class
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("ERRORS BY PREDICTED SENTIMENT")
print("=" * 70)

predicted_errors = errors["predicted_sentiment"].value_counts()

print(predicted_errors.to_string())


# ------------------------------------------------------------
# 8. Aspect-level error analysis
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("TOP ASPECTS WITH ERRORS")
print("=" * 70)

aspect_errors = errors["aspect"].value_counts().head(30)

print(aspect_errors.to_string())


# ------------------------------------------------------------
# 9. Error rate by aspect
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("ASPECT ERROR RATES")
print("=" * 70)

aspect_total = df["aspect"].value_counts()

aspect_wrong = errors["aspect"].value_counts()

aspect_analysis = pd.DataFrame({
    "total": aspect_total,
    "errors": aspect_wrong
}).fillna(0)

aspect_analysis["errors"] = aspect_analysis["errors"].astype(int)

aspect_analysis["error_rate"] = (
    aspect_analysis["errors"] / aspect_analysis["total"]
)

aspect_analysis = aspect_analysis.sort_values(
    "error_rate",
    ascending=False
)

print(
    aspect_analysis.head(30).to_string()
)


# ------------------------------------------------------------
# 10. Confidence analysis
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("CONFIDENCE ANALYSIS")
print("=" * 70)

if "confidence" in errors.columns:

    errors["confidence"] = pd.to_numeric(
        errors["confidence"],
        errors="coerce"
    )

    print(
        f"Average confidence on wrong predictions: "
        f"{errors['confidence'].mean():.4f}"
    )

    print(
        f"Minimum confidence on wrong predictions: "
        f"{errors['confidence'].min():.4f}"
    )

    print(
        f"Maximum confidence on wrong predictions: "
        f"{errors['confidence'].max():.4f}"
    )

    high_confidence_errors = errors[
        errors["confidence"] >= 0.90
    ]

    print(
        f"\nHigh-confidence errors (>= 90%): "
        f"{len(high_confidence_errors)}"
    )

    print(
        f"Percentage of errors that are high-confidence: "
        f"{len(high_confidence_errors) / len(errors) * 100:.2f}%"
    )


# ------------------------------------------------------------
# 11. Save error dataset
# ------------------------------------------------------------

columns_to_save = [
    "sentence",
    "aspect",
    "validated_sentiment",
    "predicted_sentiment",
    "confidence",
    "error_type"
]

columns_to_save = [
    column
    for column in columns_to_save
    if column in errors.columns
]

errors[columns_to_save].to_csv(
    OUTPUT_FILE,
    index=False
)


# ------------------------------------------------------------
# 12. Summary
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("ERROR ANALYSIS COMPLETE")
print("=" * 70)

print(f"\nError analysis saved to:")
print(OUTPUT_FILE)

print("\nThe file contains:")
print("- Sentence")
print("- Aspect")
print("- Human validated sentiment")
print("- RoBERTa prediction")
print("- Confidence")
print("- Error type")

print("\n" + "=" * 70)