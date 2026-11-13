import json
import pandas as pd

INPUT_FILE = "ai-engine/datasets/Electronics.jsonl"
OUTPUT_FILE = "ai-engine/datasets/reviews_working.csv"

MAX_RECORDS = 100000

records = []

with open(INPUT_FILE, "r", encoding="utf-8") as file:

    for line in file:

        if len(records) >= MAX_RECORDS:
            break

        line = line.strip()

        if not line:
            continue

        try:
            record = json.loads(line)

            text = record.get("text")
            rating = record.get("rating")

            # Skip records without review text or rating
            if not text or not text.strip():
                continue

            if rating is None:
                continue

            # Create sentiment label
            if rating <= 2:
                sentiment = "negative"
            elif rating == 3:
                sentiment = "neutral"
            else:
                sentiment = "positive"

            records.append({
                "review_text": text.strip(),
                "rating": rating,
                "verified_purchase": record.get("verified_purchase", False),
                "helpful_vote": record.get("helpful_vote", 0),
                "asin": record.get("asin"),
                "sentiment": sentiment
            })

        except json.JSONDecodeError:
            continue


df = pd.DataFrame(records)

# Remove duplicate review texts
df = df.drop_duplicates(subset=["review_text"])

# Reset index
df = df.reset_index(drop=True)

# Save working dataset
df.to_csv(OUTPUT_FILE, index=False)

print("\n========== WORKING DATASET ==========\n")

print("Total records:", len(df))

print("\nSentiment distribution:")
print(df["sentiment"].value_counts())

print("\nMissing values:")
print(df.isnull().sum())

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n=====================================")