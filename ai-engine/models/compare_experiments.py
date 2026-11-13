import os
import pandas as pd


print("=" * 70)
print("SMARTREVIEW AI - EXPERIMENT COMPARISON")
print("=" * 70)


# ------------------------------------------------------------
# PROJECT PATH
# ------------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

DATASET_DIR = os.path.join(
    BASE_DIR,
    "ai-engine",
    "datasets"
)


# ------------------------------------------------------------
# EXPERIMENT RESULTS
# ------------------------------------------------------------

experiments = [

    {
        "experiment": "Baseline RoBERTa",
        "accuracy": 0.4800,
        "macro_f1": 0.5279,
        "description":
            "Pretrained sentiment model evaluated on human-validated data"
    },

    {
        "experiment": "Human-only RoBERTa",
        "accuracy": 0.6889,
        "macro_f1": 0.2771,
        "description":
            "RoBERTa fine-tuned using manually labeled training data"
    },

    {
        "experiment": "Class-weighted RoBERTa",
        "accuracy": 0.6889,
        "macro_f1": 0.3714,
        "description":
            "Human-supervised RoBERTa with class-weighted training"
    },

    {
        "experiment": "Hybrid Human + Pseudo RoBERTa",
        "accuracy": 0.5778,
        "macro_f1": 0.5163,
        "description":
            "Human + pseudo-labeled training with higher human sample weight"
    }
]


# ------------------------------------------------------------
# CREATE DATAFRAME
# ------------------------------------------------------------

df = pd.DataFrame(experiments)


# Convert metrics to percentages

df["accuracy_percent"] = (
    df["accuracy"] * 100
)

df["macro_f1_percent"] = (
    df["macro_f1"] * 100
)


# ------------------------------------------------------------
# DISPLAY RESULTS
# ------------------------------------------------------------

print()
print("EXPERIMENT RESULTS")
print("-" * 70)

for _, row in df.iterrows():

    print(
        f"{row['experiment']:<35}"
        f"Accuracy: {row['accuracy_percent']:>6.2f}%   "
        f"Macro F1: {row['macro_f1_percent']:>6.2f}%"
    )


# ------------------------------------------------------------
# BEST ACCURACY
# ------------------------------------------------------------

best_accuracy = df.loc[
    df["accuracy"].idxmax()
]

print()
print("=" * 70)
print("HIGHEST TEST ACCURACY")
print("=" * 70)

print(
    best_accuracy["experiment"]
)

print(
    f"Accuracy: "
    f"{best_accuracy['accuracy_percent']:.2f}%"
)


# ------------------------------------------------------------
# BEST MACRO F1
# ------------------------------------------------------------

best_f1 = df.loc[
    df["macro_f1"].idxmax()
]

print()
print("=" * 70)
print("HIGHEST TEST MACRO F1")
print("=" * 70)

print(
    best_f1["experiment"]
)

print(
    f"Macro F1: "
    f"{best_f1['macro_f1_percent']:.2f}%"
)


# ------------------------------------------------------------
# SAVE RESULTS
# ------------------------------------------------------------

output_file = os.path.join(
    DATASET_DIR,
    "experiment_comparison.csv"
)

df.to_csv(
    output_file,
    index=False
)


# ------------------------------------------------------------
# RESEARCH SUMMARY
# ------------------------------------------------------------

summary_file = os.path.join(
    DATASET_DIR,
    "experiment_comparison.txt"
)

with open(
    summary_file,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "SMARTREVIEW AI - EXPERIMENT COMPARISON\n"
    )

    f.write(
        "=" * 60 + "\n\n"
    )

    for _, row in df.iterrows():

        f.write(
            f"Experiment: {row['experiment']}\n"
        )

        f.write(
            f"Accuracy: "
            f"{row['accuracy_percent']:.2f}%\n"
        )

        f.write(
            f"Macro F1: "
            f"{row['macro_f1_percent']:.2f}%\n"
        )

        f.write(
            f"Description: "
            f"{row['description']}\n\n"
        )


    f.write(
        "=" * 60 + "\n"
    )

    f.write(
        "HIGHEST TEST ACCURACY\n"
    )

    f.write(
        f"{best_accuracy['experiment']} - "
        f"{best_accuracy['accuracy_percent']:.2f}%\n\n"
    )

    f.write(
        "HIGHEST TEST MACRO F1\n"
    )

    f.write(
        f"{best_f1['experiment']} - "
        f"{best_f1['macro_f1_percent']:.2f}%\n"
    )


# ------------------------------------------------------------
# COMPLETE
# ------------------------------------------------------------

print()
print("=" * 70)
print("COMPARISON COMPLETE")
print("=" * 70)

print()
print("Results saved to:")

print(output_file)

print()
print("Summary saved to:")

print(summary_file)