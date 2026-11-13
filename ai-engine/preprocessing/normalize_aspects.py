import pandas as pd
import re

INPUT_FILE = "ai-engine/datasets/reviews_cleaned.csv"
OUTPUT_FILE = "ai-engine/datasets/reviews_aspects.csv"


# Map different phrases to one standard aspect
ASPECT_PATTERNS = {
    "battery": [
        r"\bbattery\b",
        r"\bbattery life\b",
        r"\bbattery performance\b",
        r"\bbattery power\b"
    ],

    "display": [
        r"\bdisplay\b",
        r"\bscreen\b",
        r"\bscreen quality\b",
        r"\bdisplay quality\b"
    ],

    "camera": [
        r"\bcamera\b",
        r"\bcamera quality\b",
        r"\bcamera performance\b"
    ],

    "sound": [
        r"\bsound\b",
        r"\bsound quality\b",
        r"\baudio\b",
        r"\baudio quality\b"
    ],

    "keyboard": [
        r"\bkeyboard\b",
        r"\bkeyboards\b",
        r"\bkeys\b"
    ],

    "price": [
        r"\bprice\b",
        r"\bcost\b",
        r"\bvalue for money\b",
        r"\bvalue\b"
    ],

    "case": [
        r"\bcase\b",
        r"\bcover\b",
        r"\bprotective case\b"
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
        r"\bspeed\b",
        r"\bprocessing\b"
    ],

    "build quality": [
        r"\bbuild quality\b",
        r"\nbuild\b",
        r"\bconstruction\b"
    ],

    "design": [
        r"\bdesign\b",
        r"\blook\b",
        r"\bappearance\b"
    ],

    "durability": [
        r"\bdurability\b",
        r"\bdurable\b",
        r"\blast(?:s|ing)?\b"
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
        r"\bheavy\b",
        r"\blightweight\b"
    ]
}


def extract_aspects(text):
    """
    Find normalized aspects mentioned in a review.
    Returns a list of unique aspects.
    """

    text = str(text).lower()

    detected = []

    for aspect, patterns in ASPECT_PATTERNS.items():

        for pattern in patterns:

            if re.search(pattern, text):
                detected.append(aspect)
                break

    return detected


print("Loading cleaned dataset...")

df = pd.read_csv(INPUT_FILE)

print("Reviews loaded:", len(df))

print("Detecting normalized aspects...")

df["aspects"] = df["cleaned_text"].apply(extract_aspects)

# Keep only reviews where at least one aspect was found
df_with_aspects = df[df["aspects"].str.len() > 0].copy()

df_with_aspects.reset_index(drop=True, inplace=True)

# Convert list to readable text for CSV
df_with_aspects["aspects"] = df_with_aspects["aspects"].apply(
    lambda x: ", ".join(x)
)

df_with_aspects.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n========== ASPECT NORMALIZATION ==========\n")

print("Total reviews:", len(df))

print("Reviews with detected aspects:", len(df_with_aspects))

print("\nAspect frequency:")

aspect_counts = {}

for aspects in df_with_aspects["aspects"]:
    for aspect in aspects.split(", "):
        aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1

for aspect, count in sorted(
    aspect_counts.items(),
    key=lambda item: item[1],
    reverse=True
):
    print(f"{aspect:<20} {count}")

print("\nSaved to:")
print(OUTPUT_FILE)

print("\n==========================================")