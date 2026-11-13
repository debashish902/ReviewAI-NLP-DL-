import json
from collections import Counter

FILE_PATH = "ai-engine/datasets/Electronics.jsonl"

MAX_RECORDS = 100000

total_reviews = 0
missing_text = 0
verified_count = 0
rating_counts = Counter()

total_words = 0
reviews_with_text = 0


with open(FILE_PATH, "r", encoding="utf-8") as file:

    for line in file:

        if total_reviews >= MAX_RECORDS:
            break

        line = line.strip()

        if not line:
            continue

        try:
            record = json.loads(line)

            total_reviews += 1

            # Rating distribution
            rating = record.get("rating")

            if rating is not None:
                rating_counts[rating] += 1

            # Review text
            text = record.get("text")

            if not text or not text.strip():
                missing_text += 1
            else:
                total_words += len(text.split())
                reviews_with_text += 1

            # Verified purchase
            if record.get("verified_purchase") is True:
                verified_count += 1

            # Progress
            if total_reviews % 10000 == 0:
                print(f"Processed {total_reviews:,} reviews...")

        except json.JSONDecodeError:
            print("Skipped invalid JSON record.")


average_words = (
    total_words / reviews_with_text
    if reviews_with_text > 0
    else 0
)


print("\n========== DATASET PROFILE ==========\n")

print("Reviews analyzed:", total_reviews)

print("Reviews with missing text:", missing_text)

print("Verified Purchases:", verified_count)

print("\nRating Distribution:")

for rating in sorted(rating_counts):
    print(f"{rating} star: {rating_counts[rating]}")

print("\nAverage Words per Review:", round(average_words, 2))

print("\n=====================================")