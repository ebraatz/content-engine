#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path

LIBRARY_PATH = Path(__file__).parent / "patterns.json"
VALID_TYPES = ["pattern", "story", "identity"]
TYPE_KEYS = {"pattern": "patterns", "story": "stories", "identity": "identity"}


def load_library():
    with open(LIBRARY_PATH) as f:
        data = json.load(f)
    for key in ("patterns", "stories", "identity", "log"):
        data.setdefault(key, [])
    return data


def save_library(library):
    with open(LIBRARY_PATH, "w") as f:
        json.dump(library, f, indent=2)
        f.write("\n")


def ask(label, required=True):
    value = input(f"{label}: ").strip()
    if required and not value:
        print("Cannot be empty. Aborting.")
        sys.exit(1)
    return value


def main():
    print("\n--- Add to Pattern Library ---\n")

    entry_type = ""
    while entry_type not in VALID_TYPES:
        entry_type = input("Type (pattern / story / identity): ").strip().lower()
        if entry_type not in VALID_TYPES:
            print(f"  Must be one of: {', '.join(VALID_TYPES)}")

    name = ask("Name")
    description = ask("Description")

    library = load_library()
    key = TYPE_KEYS[entry_type]

    existing_names = [e["name"].lower() for e in library[key]]
    if name.lower() in existing_names:
        print(f"\nWarning: a {entry_type} named \"{name}\" already exists.")
        confirm = input("Add anyway? (y/n): ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

    library[key].append({"name": name, "description": description})
    library["log"].append({
        "timestamp": datetime.now().isoformat(),
        "type": entry_type,
        "name": name,
        "description": description,
    })

    save_library(library)

    print(f"\nAdded {entry_type}: \"{name}\"")
    print(f"  {description}")
    print(f"  Logged at {library['log'][-1]['timestamp']}\n")


if __name__ == "__main__":
    main()
