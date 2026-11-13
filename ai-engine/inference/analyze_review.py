import json
import re
from pathlib import Path

import torch
import spacy

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)


# ============================================================
# SMARTREVIEW AI - CALIBRATED ABSA INFERENCE
# ============================================================

print("=" * 70)
print("SMARTREVIEW AI - CALIBRATED ASPECT-BASED SENTIMENT")
print("=" * 70)


# ============================================================
# PATH CONFIGURATION
# ============================================================

AI_ENGINE_DIR = Path(__file__).resolve().parents[1]

# Previous model (Experiment 4):
# MODEL_DIR = AI_ENGINE_DIR / "models" / "roberta_absa_hybrid"

MODEL_DIR = (
    AI_ENGINE_DIR
    / "models"
    / "roberta_absa_improved"
)

CALIBRATION_FILE = (
    AI_ENGINE_DIR
    / "datasets"
    / "calibration_config.json"
)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("\nDevice:", DEVICE)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))


# ============================================================
# VALIDATE REQUIRED FILES
# ============================================================

if not MODEL_DIR.is_dir():
    raise FileNotFoundError(
        f"Trained model directory not found:\n{MODEL_DIR}"
    )

if not CALIBRATION_FILE.is_file():
    raise FileNotFoundError(
        f"Calibration configuration not found:\n"
        f"{CALIBRATION_FILE}\n"
        "Run calibrate_confidence.py first."
    )


# ============================================================
# LOAD CALIBRATION CONFIGURATION
# ============================================================

print("\nLoading calibration configuration...")

with open(
    CALIBRATION_FILE,
    "r",
    encoding="utf-8"
) as file:

    calibration_config = json.load(file)


TEMPERATURE = float(
    calibration_config["temperature"]
)

if TEMPERATURE <= 0:
    raise ValueError(
        "Calibration temperature must be greater than zero."
    )

print(f"Calibration temperature: {TEMPERATURE:.4f}")


# ============================================================
# LOAD SPACY
# ============================================================

print("\nLoading spaCy...")

try:
    NLP = spacy.load("en_core_web_sm")

except OSError as error:
    raise RuntimeError(
        "spaCy English model is missing.\n"
        "Run: python -m spacy download en_core_web_sm"
    ) from error

print("spaCy loaded successfully.")


# ============================================================
# LOAD TRAINED MODEL AND TOKENIZER
# ============================================================

print("\nLoading trained RoBERTa model...")
print("Model:", MODEL_DIR)

TOKENIZER = AutoTokenizer.from_pretrained(
    str(MODEL_DIR)
)

MODEL = AutoModelForSequenceClassification.from_pretrained(
    str(MODEL_DIR)
)

MODEL.to(DEVICE)
MODEL.eval()

print("RoBERTa loaded successfully.")


# ============================================================
# LABEL MAPPING
# Must match the class-ID mapping used during training.
# ============================================================

ID_TO_LABEL = {
    0: "negative",
    1: "neutral",
    2: "positive"
}

if MODEL.config.num_labels != len(ID_TO_LABEL):
    raise ValueError(
        f"Expected 3 sentiment classes, but the model has "
        f"{MODEL.config.num_labels}."
    )


# ============================================================
# ASPECT VOCABULARY AND NORMALIZATION
# ============================================================

ASPECT_TERMS = {
    "battery life": "battery",
    "battery": "battery",

    "sound quality": "sound",
    "audio quality": "sound",
    "speakers": "sound",
    "speaker": "sound",
    "audio": "sound",
    "sound": "sound",

    "display": "display",
    "screen": "display",

    "build quality": "build quality",
    "build": "build quality",

    "bluetooth": "bluetooth",

    "charging": "charging",
    "charger": "charging",

    "connection": "connection",
    "connectivity": "connection",

    "camera": "camera",
    "keyboard": "keyboard",
    "mouse": "mouse",
    "cable": "cable",

    "software": "software",
    "application": "app",
    "app": "app",

    "performance": "performance",
    "speed": "performance",

    "value for money": "value for money",
    "value-for-money": "value for money",
    "price": "price",
    "cost": "price",

    "weight": "weight",
    "size": "size",
    "design": "design",
    "durability": "durability",

    "microphone": "microphone",
    "mic": "microphone",

    "volume": "volume",
    "headphones": "headphones",
    "earphones": "headphones",
    "comfort": "comfort",
    "case": "case",

    "quality": "quality",
    "purchase": "overall value",
    "value": "value for money",
    "worth": "value for money",
    "delivery": "delivery",
    "shipping": "delivery",
    "packaging": "packaging"
}


# Longer phrases are checked first.
SORTED_ASPECT_TERMS = sorted(
    ASPECT_TERMS.items(),
    key=lambda item: len(item[0]),
    reverse=True
)


def get_aspect_variants(aspect):
    """Return known words and phrases for a normalized aspect."""

    variants = [
        term
        for term, normalized in ASPECT_TERMS.items()
        if normalized == aspect
    ]

    if aspect not in variants:
        variants.append(aspect)

    return sorted(
        set(variants),
        key=len,
        reverse=True
    )


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    """Remove URLs, HTML fragments, and repeated whitespace."""

    if not isinstance(text, str):
        raise TypeError("Review must be a string.")

    text = re.sub(
        r"https?://\S+|www\.\S+",
        "",
        text
    )

    text = re.sub(
        r"<[^>]*>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# SENTENCE SPLITTING
# ============================================================

def split_sentences(review):
    """Split a review into sentences using spaCy."""

    doc = NLP(review)

    return [
        sentence.text.strip()
        for sentence in doc.sents
        if sentence.text.strip()
    ]


# ============================================================
# ASPECT DETECTION
# ============================================================

def detect_aspects(sentence):
    """Detect known aspects mentioned explicitly in a sentence."""

    detected = []

    lower_sentence = sentence.lower()

    for term, normalized in SORTED_ASPECT_TERMS:

        pattern = (
            r"\b"
            + re.escape(term)
            + r"\b"
        )

        if re.search(pattern, lower_sentence):

            if normalized not in detected:
                detected.append(normalized)

    return detected


# ============================================================
# ASPECT CONTEXT EXTRACTION
# ============================================================

def extract_aspect_context(sentence, aspect):
    """
    Extract a focused clause for the requested aspect.

    Example:
        Review:
        "Build Quality is Okay. Go for Samsung S25 because
         it is not value for money."

        Build quality context:
        "Build Quality is Okay"

        Value-for-money context:
        "it is not value for money"

    This prevents unrelated recommendation language or sentiment
    about another aspect from dominating the prediction.
    """

    variants = get_aspect_variants(aspect)

    # Split contrasting and causal clauses so each aspect is
    # evaluated using the text most directly associated with it.
    clauses = re.split(
        r"\s+(?:but|however|although|though|whereas|because|since|while)\s+",
        sentence,
        flags=re.IGNORECASE
    )

    # Split coordinated clauses such as:
    # "The display is excellent and the design is beautiful."
    focused_clauses = []

    for clause in clauses:
        focused_clauses.extend(
            re.split(
                r"\s+\band\s+",
                clause,
                flags=re.IGNORECASE
            )
        )

    # Find the smallest clause that explicitly mentions this aspect.
    for clause in focused_clauses:
        clause = clause.strip(" ,;:")
        if not clause:
            continue

        for variant in variants:
            pattern = r"\b" + re.escape(variant) + r"\b"

            if re.search(pattern, clause, flags=re.IGNORECASE):
                context = clause

                # Remove trailing recommendation/explanation text
                # that often introduces a different opinion.
                context = re.split(
                    r"\s+(?:go\s+for|because|since|therefore|"
                    r"so\s+that|which\s+is\s+why)\b",
                    context,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0]

                context = context.strip(" ,;:")
                if context:
                    return context

    # Fallback: use the complete sentence if no focused clause
    # explicitly contains the requested aspect.
    return sentence.strip()


# ============================================================
# CALIBRATED SENTIMENT PREDICTION
# ============================================================

def predict_sentiment(context, aspect):
    """
    Predict aspect sentiment using the same paired-tokenizer
    structure used during training.

    Temperature scaling adjusts probabilities, not the
    underlying model weights.
    """

    inputs = TOKENIZER(
        context,
        aspect,
        truncation=True,
        padding="max_length",
        max_length=128,
        return_tensors="pt"
    )

    inputs = {
        key: value.to(DEVICE)
        for key, value in inputs.items()
    }

    with torch.inference_mode():

        outputs = MODEL(
            **inputs
        )

        raw_logits = outputs.logits

        calibrated_probabilities = torch.softmax(
            raw_logits / TEMPERATURE,
            dim=-1
        )[0]

    predicted_id = int(
        calibrated_probabilities.argmax().item()
    )

    sentiment = ID_TO_LABEL[predicted_id]

    confidence = float(
        calibrated_probabilities[predicted_id].item()
    )

    probabilities = {
        ID_TO_LABEL[index]: round(
            float(probability.item()),
            6
        )
        for index, probability in enumerate(
            calibrated_probabilities
        )
    }

    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 4),
        "probabilities": probabilities
    }


# ============================================================
# OVERALL SENTIMENT
# ============================================================

def calculate_overall_sentiment(results):
    """Determine a simple review-level sentiment summary."""

    sentiments = [
        item["sentiment"]
        for item in results
    ]

    if not sentiments:
        return "unknown"

    has_positive = "positive" in sentiments
    has_negative = "negative" in sentiments

    if has_positive and has_negative:
        return "mixed"

    counts = {
        "positive": sentiments.count("positive"),
        "negative": sentiments.count("negative"),
        "neutral": sentiments.count("neutral")
    }

    return max(
        counts,
        key=counts.get
    )


# ============================================================
# REVIEW ANALYSIS
# ============================================================

def analyze_review(review):
    """Analyze the aspects and sentiment of a product review."""

    cleaned_review = clean_text(review)

    if not cleaned_review:
        raise ValueError(
            "Review text cannot be empty."
        )

    sentences = split_sentences(
        cleaned_review
    )

    aspect_results = []

    # Process each sentence independently.
    for sentence in sentences:

        aspects = detect_aspects(
            sentence
        )

        for aspect in aspects:

            context = extract_aspect_context(
                sentence,
                aspect
            )

            prediction = predict_sentiment(
                context,
                aspect
            )

            aspect_results.append({
                "aspect": aspect,
                "sentence": sentence,
                "context": context,
                "sentiment": prediction["sentiment"],
                "confidence": prediction["confidence"],
                "probabilities": prediction["probabilities"]
            })

    # Fallback: if no explicit aspect keywords were detected across the entire review
    # (e.g. concise external reviews like "Very satisfied! Would buy again!"),
    # evaluate each sentence under "overall experience".
    if not aspect_results:
        for sentence in sentences:
            if not sentence.strip():
                continue
            prediction = predict_sentiment(sentence, "overall experience")
            aspect_results.append({
                "aspect": "overall experience",
                "sentence": sentence,
                "context": sentence,
                "sentiment": prediction["sentiment"],
                "confidence": prediction["confidence"],
                "probabilities": prediction["probabilities"]
            })

    overall_sentiment = calculate_overall_sentiment(
        aspect_results
    )

    return {
        "review": review,
        "overall_sentiment": overall_sentiment,
        "aspects": aspect_results,
        "metadata": {
            "model": "roberta_absa_improved",
            "temperature": TEMPERATURE,
            "confidence_method": "temperature_scaled_softmax"
        }
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    test_review = (
        "Build Quality is Okay. Go for Samsung S25 because "
        "it is not value for money. "
        "The camera is good."
    )

    result = analyze_review(
        test_review
    )

    print()
    print("=" * 70)
    print("CALIBRATED REVIEW ANALYSIS")
    print("=" * 70)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )

    print()
    print("=" * 70)
    print("CALIBRATED INFERENCE COMPLETE")
    print("=" * 70)