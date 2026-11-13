# ============================================================
# SMARTREVIEW AI - EXPERIMENT 6 PIPELINE
# ============================================================
#
# Master script to run the complete improved training pipeline.
#
# Steps:
#   1. Augment human training data (EDA techniques)
#   2. Create improved hybrid dataset (class-balanced weights)
#   3. Train improved RoBERTa model (all 6 optimizations)
#   4. Re-calibrate confidence (Temperature Scaling)
#
# Usage:
#   cd ai-engine
#   python run_improved_training.py
#
# ============================================================

import subprocess
import sys
import os
import time


# ============================================================
# PATHS
# ============================================================

AI_ENGINE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SCRIPTS = [

    {
        "name": "Step 1: Data Augmentation",
        "script": os.path.join(
            AI_ENGINE_DIR,
            "preprocessing",
            "augment_human_data.py"
        ),
        "description":
            "Augmenting human training data with EDA techniques "
            "(word deletion, swap, repetition)"
    },

    {
        "name": "Step 2: Improved Hybrid Dataset",
        "script": os.path.join(
            AI_ENGINE_DIR,
            "preprocessing",
            "create_improved_hybrid.py"
        ),
        "description":
            "Creating class-balanced hybrid dataset "
            "(human + augmented + pseudo-labeled)"
    },

    {
        "name": "Step 3: Improved RoBERTa Training",
        "script": os.path.join(
            AI_ENGINE_DIR,
            "models",
            "train_roberta_improved.py"
        ),
        "description":
            "Training with sentiment-pretrained model, "
            "curriculum learning, label smoothing, "
            "cosine warmup, and weighted sampling"
    },

    {
        "name": "Step 4: Confidence Calibration",
        "script": os.path.join(
            AI_ENGINE_DIR,
            "models",
            "calibrate_confidence.py"
        ),
        "description":
            "Re-calibrating confidence with "
            "Temperature Scaling on the new model"
    }
]


# ============================================================
# RUN PIPELINE
# ============================================================

def main():

    print()
    print("=" * 70)
    print("SMARTREVIEW AI - EXPERIMENT 6 PIPELINE")
    print("=" * 70)

    print()
    print("This pipeline will run 4 steps:")

    for i, step in enumerate(SCRIPTS):

        print(
            f"  {i + 1}. {step['name']}"
        )

    print()
    print("=" * 70)

    start_time = time.time()

    for i, step in enumerate(SCRIPTS):

        print()
        print("=" * 70)
        print(f"RUNNING: {step['name']}")
        print("-" * 70)
        print(step["description"])
        print("=" * 70)
        print()

        script_path = step["script"]

        if not os.path.exists(script_path):

            print(
                f"ERROR: Script not found: {script_path}"
            )

            sys.exit(1)

        step_start = time.time()

        result = subprocess.run(
            [sys.executable, script_path],
            cwd=AI_ENGINE_DIR
        )

        step_duration = time.time() - step_start

        if result.returncode != 0:

            print()
            print("=" * 70)
            print(
                f"PIPELINE FAILED at: {step['name']}"
            )
            print(
                f"Exit code: {result.returncode}"
            )
            print("=" * 70)

            sys.exit(result.returncode)

        print()
        print(
            f"COMPLETED: {step['name']} "
            f"({step_duration:.1f}s)"
        )

    total_duration = time.time() - start_time

    print()
    print("=" * 70)
    print("EXPERIMENT 6 PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print()
    print(f"Total time: {total_duration:.1f}s")

    print()
    print("Improvements applied:")
    print("  1. Sentiment-pretrained base model")
    print("  2. Data augmentation (EDA)")
    print("  3. Class-balanced weighted sampling")
    print("  4. Cosine LR schedule with warmup")
    print("  5. Label smoothing (0.1)")
    print("  6. Curriculum learning (2-phase)")
    print("  7. Re-calibrated confidence")

    print()
    print(
        "The improved model is saved at:"
    )
    print(
        "  ai-engine/models/roberta_absa_improved/"
    )

    print()
    print(
        "The inference pipeline (analyze_review.py) "
        "has been updated to use the new model."
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
