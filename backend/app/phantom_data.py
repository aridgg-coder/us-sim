from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ANATOMY_DIR = ROOT / "frontend" / "public" / "anatomy"


def _load_json(name: str) -> dict[str, Any]:
    with (ANATOMY_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_phantom_manifest() -> dict[str, Any]:
    return _load_json("phantom.manifest.json")


@lru_cache(maxsize=1)
def load_tissue_properties() -> dict[str, Any]:
    return _load_json("tissue-properties.json")


def get_tissue_by_id(tissue_id: str) -> dict[str, Any] | None:
    table = load_tissue_properties()
    for tissue in table.get("tissues", []):
        if tissue.get("id") == tissue_id:
            return tissue
    return None
