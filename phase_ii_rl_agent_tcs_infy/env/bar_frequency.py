"""Calendar-time span helpers converted to bar counts for a given frequency."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

_SPAN_PATTERN = re.compile(r"^(\d+)([dhms])$")

_UNIT_TO_TIMEDELTA: dict[str, timedelta] = {
    "d": timedelta(days=1),
    "h": timedelta(hours=1),
    "m": timedelta(minutes=1),
    "s": timedelta(seconds=1),
}

# Bars per calendar unit at each supported frequency tag.
_BARS_PER_UNIT: dict[str, dict[str, int]] = {
    "1d": {"d": 1, "h": 0, "m": 0, "s": 0},
    # Future intraday tags can extend this table without changing call sites.
    "1h": {"d": 24, "h": 1, "m": 0, "s": 0},
}


@dataclass(frozen=True)
class CalendarSpan:
    """A duration expressed as count + unit, e.g. 500d."""

    count: int
    unit: str

    @classmethod
    def parse(cls, spec: str) -> "CalendarSpan":
        match = _SPAN_PATTERN.fullmatch(spec.strip())
        if not match:
            raise ValueError(f"invalid calendar span spec: {spec!r}")
        count = int(match.group(1))
        unit = match.group(2)
        if unit not in _UNIT_TO_TIMEDELTA:
            raise ValueError(f"unsupported span unit: {unit}")
        if count <= 0:
            raise ValueError(f"span count must be positive, got {count}")
        return cls(count=count, unit=unit)

    def to_timedelta(self) -> timedelta:
        return self.count * _UNIT_TO_TIMEDELTA[self.unit]


def span_to_bar_count(span: CalendarSpan | str, bar_frequency: str = "1d") -> int:
    """Convert a calendar span to a bar count for the active frequency tag."""
    if isinstance(span, str):
        span = CalendarSpan.parse(span)
    if bar_frequency not in _BARS_PER_UNIT:
        raise ValueError(f"unsupported bar_frequency: {bar_frequency!r}")
    bars_per_unit = _BARS_PER_UNIT[bar_frequency].get(span.unit)
    if not bars_per_unit:
        raise ValueError(
            f"cannot convert {span.count}{span.unit} to bars at frequency {bar_frequency!r}"
        )
    return span.count * bars_per_unit


def slice_trailing_bars(
    index: pd.DatetimeIndex,
    end_timestamp: pd.Timestamp,
    span: CalendarSpan | str,
    bar_frequency: str = "1d",
) -> pd.DatetimeIndex:
    """Return timestamps for the trailing window ending at end_timestamp."""
    if isinstance(span, str):
        span = CalendarSpan.parse(span)

    end_timestamp = pd.Timestamp(end_timestamp)
    if bar_frequency == "1d":
        # Daily bars: use explicit bar-count derived from the span spec.
        bar_count = span_to_bar_count(span, bar_frequency)
        eligible = index[index <= end_timestamp]
        if len(eligible) < bar_count:
            raise ValueError(
                f"insufficient history for {span.count}{span.unit} lookback at {end_timestamp.date()}"
            )
        return eligible[-bar_count:]

    start_timestamp = end_timestamp - span.to_timedelta()
    mask = (index > start_timestamp) & (index <= end_timestamp)
    selected = index[mask]
    if len(selected) == 0:
        raise ValueError(
            f"no bars in ({start_timestamp}, {end_timestamp}] for span {span.count}{span.unit}"
        )
    return selected
