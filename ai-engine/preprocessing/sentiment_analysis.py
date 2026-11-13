import pandas as pd
from transformers import pipeline

INPUT_FILE = (
    "ai-engine/datasets/aspect_sentences_sample.csv"
)

OUTPUT_FILE = (
    "ai-engine/datasets/aspect_sentiment_sample.csv"
)

print("Loading aspect-sentence dataset...")

df = pd.read_csv(INPUT_FILE)

print("Aspect-sentence pairs:", len(df))

# Make sure sentences are valid strings
df["sentence"] = (
    df["sentence"]
    .fillna("")
    .astype(str)
)

df = df[df["sentence"].str.strip() != ""]

print("Loading RoBERTa sentiment model...")

sentiment_model = pipeline(
    "sentiment-analysis",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest"
)

print("Running sentiment analysis...")

sentiments = []

# Process sentences in batches
for i in range(0, len(df), 32):

    batch = df["sentence"].iloc[i:i + 32].tolist()

    results = sentiment_model(
        batch,
        truncation=True,
        max_length=512
    )

    for result in results:

        label = result["label"].lower()

        if "positive" in label:
            sentiment = "positive"

        elif "negative" in label:
            sentiment = "negative"

        else:
            sentiment = "neutral"

        sentiments.append(sentiment)

    print(
        f"Processed {min(i + 32, len(df))}/{len(df)}"
    )


df["aspect_sentiment"] = sentiments

# Save result
df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\n========== SENTIMENT ANALYSIS ==========\n")

print("Total pairs:", len(df))

print("\nSentiment distribution:")

print(
    df["aspect_sentiment"]
    .value_counts()
)

print("\nSample results:\n")

print(
    df[
        [
            "sentence",
            "aspect",
            "aspect_sentiment"
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n========================================")