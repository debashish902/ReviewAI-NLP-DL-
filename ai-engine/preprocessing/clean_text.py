import pandas as pd
import re

INPUT_FILE = "ai-engine/datasets/reviews_working.csv"
OUTPUT_FILE = "ai-engine/datasets/reviews_cleaned.csv"


def clean_text(text):
    text = str(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove URLs
    text = re.sub(r"http\S+|www\S+", " ", text)

    # Remove newline and tab characters
    text = re.sub(r"[\n\r\t]", " ", text)

    # Remove control characters
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

    # Normalize multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing spaces
    text = text.strip()

    return text


print("Loading working dataset...")

df = pd.read_csv(INPUT_FILE)

print("Reviews before cleaning:", len(df))

# Clean review text
df["cleaned_text"] = df["review_text"].apply(clean_text)

# Remove reviews that became empty
df = df[df["cleaned_text"].str.len() > 0]

# Reset index
df = df.reset_index(drop=True)

# Save cleaned dataset
df.to_csv(OUTPUT_FILE, index=False)

print("\n========== TEXT CLEANING ==========\n")

print("Reviews after cleaning:", len(df))

print("\nExample:")

for i in range(min(3, len(df))):
    print("\nOriginal:")
    print(df.loc[i, "review_text"][:300])

    print("\nCleaned:")
    print(df.loc[i, "cleaned_text"][:300])

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n===================================")