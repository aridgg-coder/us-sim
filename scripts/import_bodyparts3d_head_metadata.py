#!/usr/bin/env python3

from __future__ import annotations

import json
import urllib.request
from pathlib import Path


SOURCE_URL = (
    "https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/isa_parts_list_e.txt"
)
OUTPUT_PATH = Path("frontend/public/anatomy/bodyparts3d-head-metadata.json")

HEAD_TERMS = (
    "brain",
    "cerebral",
    "cerebell",
    "cran",
    "skull",
    "head",
    "temporal",
    "parietal",
    "frontal",
    "occipital",
    "ventricle",
    "carotid",
    "basilar",
    "thalam",
    "hypothalam",
    "pituitary",
)


def main() -> None:
    with urllib.request.urlopen(SOURCE_URL) as response:
        content = response.read().decode("utf-8")

    rows = []
    for line in content.splitlines()[1:]:
        if not line.strip():
            continue

        parts = line.split("\t")
        if len(parts) != 3:
            continue

        concept_id, representation_id, label = parts
        lower_label = label.lower()
        if any(term in lower_label for term in HEAD_TERMS):
            rows.append(
                {
                    "conceptId": concept_id,
                    "representationId": representation_id,
                    "label": label,
                }
            )

    payload = {
        "source": "BodyParts3D IS-A Tree metadata",
        "sourceUrl": SOURCE_URL,
        "license": "CC BY-SA 2.1 JP",
        "entryCount": len(rows),
        "entries": rows,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
