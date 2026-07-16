"""Phase I admitted episode-core boundaries (calendar timestamps)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# Loaded from Phase I claim_002 strict healthy cores — not recomputed here.
EPISODE_CORES: dict[str, dict[str, object]] = {
    "500d_core": {
        "start": pd.Timestamp("2020-01-31"),
        "end": pd.Timestamp("2021-12-31"),
        "beta_lookback_span": "500d",
        "eg_lookback_span": "500d",
    },
    "730d_core": {
        "start": pd.Timestamp("2020-12-31"),
        "end": pd.Timestamp("2023-03-31"),
        "beta_lookback_span": "730d",
        "eg_lookback_span": "730d",
    },
}


@dataclass(frozen=True)
class EpisodeCoreConfig:
    core_id: str
    start: pd.Timestamp
    end: pd.Timestamp
    beta_lookback_span: str
    eg_lookback_span: str

    @classmethod
    def from_core_id(cls, core_id: str) -> "EpisodeCoreConfig":
        if core_id not in EPISODE_CORES:
            raise KeyError(f"unknown episode core: {core_id}")
        spec = EPISODE_CORES[core_id]
        return cls(
            core_id=core_id,
            start=pd.Timestamp(spec["start"]),
            end=pd.Timestamp(spec["end"]),
            beta_lookback_span=str(spec["beta_lookback_span"]),
            eg_lookback_span=str(spec["eg_lookback_span"]),
        )
