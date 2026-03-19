from __future__ import annotations

import os

from .simulation_engines import EngineName


def get_simulation_engine() -> EngineName:
    engine = os.getenv("SIMULATION_ENGINE", "tusx").lower()
    if engine in {"baseline", "tusx", "babelbrain"}:
        return engine  # type: ignore[return-value]
    return "tusx"

