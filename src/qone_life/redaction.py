"""Explicit export modes for personal observations."""

from __future__ import annotations

import hashlib
from typing import Any

from .models import Observation


def _public_id(value: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:16]


def export_observations(
    observations: list[Observation],
    *,
    redacted: bool = True,
    salt: str = "q-one-public-export",
) -> dict[str, Any]:
    if not redacted:
        rows = [observation.to_dict() for observation in observations]
    else:
        rows = [
            {
                "observation_id": _public_id(observation.observation_id, salt),
                "domain": observation.domain,
                "metric": observation.metric,
                "value": observation.value,
                "minimum": observation.minimum,
                "maximum": observation.maximum,
                "observed_at": observation.observed_at,
                "source_class": "user_recorded",
            }
            for observation in observations
        ]
    return {
        "export_mode": "redacted" if redacted else "full",
        "observations": rows,
        "limitations": [
            "redaction removes notes, decision links, and raw source strings but values may remain sensitive",
            "review the export manually before sharing",
        ],
    }
