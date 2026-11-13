import pandas as pd
import spacy
import re

INPUT_FILE = "ai-engine/datasets/reviews_cleaned.csv"

OUTPUT_FILE = (
    "ai-engine/datasets/aspect_sentences_sample.csv"
)

SAMPLE_SIZE = 5000


# -----------------------------------------
# Normalized aspect vocabulary
# -----------------------------------------

ASPECT_PATTERNS = {

    "battery": [
        r"\bbattery\b",
        r"\bbattery life\b",
        r"\bbattery performance\b"
    ],

    "display": [
        r"\bscreen\b",
        r"\bdisplay\b",
        r"\bscreen quality\b",
        r"\bdisplay quality\b"
    ],

    "camera": [
        r"\bcamera\b",
        r"\bcamera quality\b"
    ],

    "sound": [
        r"\bsound\b",
        r"\bsound quality\b",
        r"\baudio\b",
        r"\baudio quality\b"
    ],

    "keyboard": [
        r"\bkeyboard\b",
        r"\bkeys\b"
    ],

    "price": [
        r"\bprice\b",
        r"\bcost\b",
        r"\bvalue for money\b"
    ],

    "case": [
        r"\bcase\b",
        r"\bcover\b"
    ],

    "cable": [
        r"\bcable\b",
        r"\bcord\b",
        r"\bwire\b"
    ],

    "charging": [
        r"\bcharging\b",
        r"\bcharger\b",
        r"\bcharge\b"
    ],

    "bluetooth": [
        r"\bbluetooth\b"
    ],

    "performance": [
        r"\bperformance\b",
        r"\bspeed\b"
    ],

    "build quality": [
        r"\bbuild quality\b",
        r"\bconstruction\b"
    ],

    "design": [
        r"\bdesign\b",
        r"\bappearance\b"
    ],

    "durability": [
        r"\bdurability\b",
        r"\bdurable\b"
    ],

    "volume": [
        r"\bvolume\b",
        r"\bloudness\b"
    ],

    "headphones": [
        r"\bheadphones\b",
        r"\bearphones\b",
        r"\bearbuds\b"
    ],

    "microphone": [
        r"\bmicrophone\b",
        r"\bmic\b"
    ],

    "software": [
        r"\bsoftware\b",
        r"\bfirmware\b"
    ],

    "app": [
        r"\bapp\b",
        r"\bapplication\b"
    ],

    "connection": [
        r"\bconnection\b",
        r"\bconnectivity\b",
        r"\bsignal\b"
    ],

    "size": [
        r"\bsize\b",
        r"\bdimensions\b"
    ],

    "weight": [
        r"\bweight\b",
        r"\blightweight\b"
    ]
}


def detect_aspects(sentence):

    sentence = sentence.lower()

    detected = []

    for aspect, patterns in ASPECT_PATTERNS.items():

        for pattern in patterns:

            if re.search(pattern, sentence):

                detected.append(aspect)

                break

    return detected


print("Loading dataset...")

df = pd.read_csv(INPUT_FILE)

df["cleaned_text"] = (
    df["cleaned_text"]
    .fillna("")
    .astype(str)
)

df = df.head(SAMPLE_SIZE)

print("Reviews selected:", len(df))


# -----------------------------------------
# Load spaCy
# -----------------------------------------

print("Loading spaCy...")

nlp = spacy.load(
    "en_core_web_sm",
    disable=["ner"]
)


# -----------------------------------------
# Create sentence-aspect records
# -----------------------------------------

records = []

print("Splitting reviews into sentences...")

for index, doc in enumerate(
    nlp.pipe(
        df["cleaned_text"].tolist(),
        batch_size=100
    )
):

    original_rating = df.iloc[index]["rating"]

    original_sentiment = df.iloc[index]["sentiment"]

    asin = df.iloc[index]["asin"]

    for sentence in doc.sents:

        sentence_text = sentence.text.strip()

        if len(sentence_text) < 5:
            continue

        aspects = detect_aspects(sentence_text)

        for aspect in aspects:

            records.append({

                "sentence": sentence_text,

                "aspect": aspect,

                "review_rating": original_rating,

                "review_sentiment": original_sentiment,

                "asin": asin
            })


result_df = pd.DataFrame(records)


result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "\n========== ASPECT SENTENCE DATASET =========="
)

print(
    "\nAspect-sentence pairs:",
    len(result_df)
)

print("\nAspect distribution:")

if not result_df.empty:

    print(
        result_df["aspect"]
        .value_counts()
    )


print("\nSample records:\n")

if not result_df.empty:

    print(
        result_df[
            [
                "sentence",
                "aspect"
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


print("\nSaved to:")

print(OUTPUT_FILE)

print(
    "\n============================================="
)