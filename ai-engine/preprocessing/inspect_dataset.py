import json

FILE_PATH = "ai-engine/datasets/Electronics.jsonl"

with open(FILE_PATH, "r", encoding="utf-8") as file:
    for i in range(5):
        line = file.readline()

        if not line:
            break

        record = json.loads(line)

        print(f"\n--- Record {i + 1} ---")
        print(record)