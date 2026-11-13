import pandas as pd
import spacy
from collections import Counter

INPUT_FILE = "ai-engine/datasets/reviews_cleaned.csv"

SAMPLE_SIZE = 10000

print("Loading dataset...")

df = pd.read_csv(INPUT_FILE)

df = df.head(SAMPLE_SIZE)

df["cleaned_text"] = (
    df["cleaned_text"]
    .fillna("")
    .astype(str)
)

df = df[df["cleaned_text"].str.strip() != ""]

print("Reviews analyzed:", len(df))

print("Loading spaCy model...")

nlp = spacy.load("en_core_web_sm")

aspect_counter = Counter()

# Generic phrases that are not useful product aspects
STOP_PHRASES = {
    "this",
    "that",
    "these",
    "those",
    "you",
    "they",
    "them",
    "we",
    "us",
    "something",
    "anything",
    "everything",
    "nothing",
    "someone",
    "thing",
    "things",
    "this one",
    "this product",
    "this review",
    "my phone",
}

print("Extracting candidate aspects...")

texts = df["cleaned_text"].tolist()

for doc in nlp.pipe(
    texts,
    batch_size=100,
    disable=["ner"]
):

    for chunk in doc.noun_chunks:

        phrase = chunk.text.strip().lower()

        # Remove punctuation around the phrase
        phrase = phrase.strip(".,!?;:\"'()[]{}")

        # Ignore short phrases
        if len(phrase) < 3:
            continue

        # Ignore very long phrases
        if len(phrase.split()) > 4:
            continue

        # Ignore generic/noise phrases
        if phrase in STOP_PHRASES:
            continue

        # Keep chunks containing actual nouns
        has_noun = any(
            token.pos_ in {"NOUN", "PROPN"}
            for token in chunk
        )

        if not has_noun:
            continue

        aspect_counter[phrase] += 1


print("\n========== TOP CANDIDATE ASPECTS ==========\n")

for aspect, count in aspect_counter.most_common(50):
    print(f"{aspect:<40} {count}")

print("\n===========================================")