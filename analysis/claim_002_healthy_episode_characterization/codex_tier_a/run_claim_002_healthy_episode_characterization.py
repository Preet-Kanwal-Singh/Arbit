from __future__ import annotations

import hashlib
import io
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels
from statsmodels.tsa.stattools import adfuller, coint


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

CLAIM_ID = "claim_002_healthy_episode_characterization"
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
SNAPSHOT_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
SNAPSHOT_METADATA_JSON = SNAPSHOT_DIR / "metadata.json"

WINDOWS = [60, 120, 250, 500, 730]
ROLLING_METRICS = [
    "beta",
    "half_life",
    "phi",
    "eg_p",
    "adf_p",
    "spread_std",
    "spread_daily_change_std",
]
SUBREGIME_METRICS = [
    "beta",
    "half_life",
    "spread_std",
    "spread_daily_change_std",
    "neg_log10_eg_p",
    "neg_log10_adf_p",
]

FIXED_INPUTS = {
    "500d_strict": {
        "window_length": 500,
        "start_date": pd.Timestamp("2020-01-31"),
        "end_date": pd.Timestamp("2021-12-31"),
    },
    "730d_strict": {
        "window_length": 730,
        "start_date": pd.Timestamp("2020-12-31"),
        "end_date": pd.Timestamp("2023-03-31"),
    },
}
SHOULDER = {
    "basis": "500d_post_core_shoulder",
    "window_length": 500,
    "start_after": FIXED_INPUTS["500d_strict"]["end_date"],
    "end_date": pd.Timestamp("2023-01-31"),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception as exc:  # pragma: no cover - provenance fallback only
        return f"unavailable: {exc}"


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.floating):
        return json_safe(float(value))
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
    return value


def load_snapshot() -> tuple[pd.DataFrame, dict[str, Any]]:
    if not SNAPSHOT_CLOSE_CSV.exists():
        raise FileNotFoundError(f"missing snapshot adjusted-close CSV: {SNAPSHOT_CLOSE_CSV}")
    if not SNAPSHOT_METADATA_JSON.exists():
        raise FileNotFoundError(f"missing snapshot metadata JSON: {SNAPSHOT_METADATA_JSON}")

    metadata = json.loads(SNAPSHOT_METADATA_JSON.read_text(encoding="utf-8"))
    if metadata.get("snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError(f"snapshot_id mismatch: {metadata.get('snapshot_id')} != {SNAPSHOT_ID}")

    close = pd.read_csv(SNAPSHOT_CLOSE_CSV, parse_dates=["date"]).set_index("date")
    required = ["TCS.NS", "INFY.NS"]
    missing = [column for column in required if column not in close.columns]
    if missing:
        raise RuntimeError(f"missing required snapshot columns: {missing}")
    close = close[required].dropna()
    if close.empty:
        raise RuntimeError("snapshot is empty after dropping rows missing TCS/INFY")
    return close.sort_index(), metadata


def month_end_trading_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    values = pd.Series(index=index, data=index)
    return list(values.groupby(values.index.to_period("M")).max())


def ols_with_intercept(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coeffs
    return coeffs, y - fitted


def engle_granger_p_value(y: np.ndarray, x: np.ndarray) -> float:
    try:
        _, p_value, _ = coint(y, x, trend="c", autolag="aic")
        return float(p_value)
    except Exception:
        return float("nan")


def residual_adf_p_value(resid: np.ndarray) -> float:
    values = np.asarray(resid, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 12:
        return float("nan")
    try:
        return float(adfuller(values, regression="n", autolag="aic")[1])
    except Exception:
        return float("nan")


def ar1_phi_with_intercept(resid: np.ndarray) -> float:
    values = np.asarray(resid, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return float("nan")
    coeffs, _ = ols_with_intercept(values[:-1], values[1:])
    return float(coeffs[1])


def half_life_from_phi(phi: float) -> float:
    if not math.isfinite(phi):
        return float("nan")
    if phi <= 0:
        return float("nan")
    if phi >= 1:
        return float("inf")
    return float(-math.log(2.0) / math.log(phi))


def compute_rolling_metrics(close: pd.DataFrame) -> pd.DataFrame:
    log_prices = np.log(close)
    month_ends = month_end_trading_dates(log_prices.index)
    rows: list[dict[str, Any]] = []

    for window_length in WINDOWS:
        for date in month_ends:
            trailing = log_prices.loc[:date].tail(window_length)
            if len(trailing) < window_length:
                continue

            y = trailing["TCS.NS"].to_numpy(dtype=float)
            x = trailing["INFY.NS"].to_numpy(dtype=float)
            coeffs, resid = ols_with_intercept(x, y)
            beta = float(coeffs[1])
            eg_p = engle_granger_p_value(y, x)
            adf_p = residual_adf_p_value(resid)
            phi = ar1_phi_with_intercept(resid)
            half_life = half_life_from_phi(phi)
            spread_std = float(np.std(resid, ddof=1))
            spread_daily_change_std = float(np.std(np.diff(resid), ddof=1))

            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "window_length": window_length,
                    "beta": beta,
                    "half_life": half_life,
                    "phi": phi,
                    "eg_p": eg_p,
                    "adf_p": adf_p,
                    "spread_std": spread_std,
                    "spread_daily_change_std": spread_daily_change_std,
                    "strict_pass": bool(eg_p < 0.05 and adf_p < 0.05),
                    "borderline_pass": bool(eg_p < 0.10 and adf_p < 0.05),
                }
            )

    return pd.DataFrame(rows).sort_values(["window_length", "date"]).reset_index(drop=True)


def select_latest_sustained_run(frame: pd.DataFrame, pass_column: str) -> dict[str, Any]:
    sorted_frame = frame.sort_values("date").reset_index(drop=True)
    candidates: list[dict[str, Any]] = []
    run_start: int | None = None

    for idx, passed in enumerate(sorted_frame[pass_column].astype(bool)):
        if passed and run_start is None:
            run_start = idx
        if (not passed or idx == len(sorted_frame) - 1) and run_start is not None:
            run_end = idx if passed and idx == len(sorted_frame) - 1 else idx - 1
            count = run_end - run_start + 1
            if count >= 6:
                start_row = sorted_frame.iloc[run_start]
                end_row = sorted_frame.iloc[run_end]
                candidates.append(
                    {
                        "start_date": str(start_row["date"]),
                        "end_date": str(end_row["date"]),
                        "month_end_count": int(count),
                    }
                )
            run_start = None

    if not candidates:
        return {"candidate_status": "no_sustained_run", "start_date": "", "end_date": "", "month_end_count": 0}

    candidates.sort(key=lambda row: (row["end_date"], row["month_end_count"]), reverse=True)
    selected = dict(candidates[0])
    selected["candidate_status"] = "selected_latest_ending_run"
    return selected


def fixed_input_count(rolling: pd.DataFrame, basis: str) -> int:
    spec = FIXED_INPUTS[basis]
    subset = fixed_subset(rolling, basis)
    month_ends = [
        date
        for date in pd.to_datetime(subset["date"])
        if spec["start_date"] <= date <= spec["end_date"]
    ]
    return len(month_ends)


def boundary_candidates(rolling: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    definitions = [
        ("500d_strict", 500, "strict_pass", "strict_pass"),
        ("730d_strict", 730, "strict_pass", "strict_pass"),
        ("500d_borderline_tolerant", 500, "borderline_pass", "borderline_pass"),
    ]
    for basis, window_length, pass_column, pass_definition in definitions:
        subset = rolling[rolling["window_length"] == window_length].copy()
        selected = select_latest_sustained_run(subset, pass_column)
        fixed = FIXED_INPUTS.get(basis, {})
        fixed_start = fixed.get("start_date")
        fixed_end = fixed.get("end_date")
        row = {
            "boundary_basis": basis,
            "source_window_length": window_length,
            "pass_definition": pass_definition,
            **selected,
            "fixed_input_start_date": fixed_start.strftime("%Y-%m-%d") if fixed_start is not None else "",
            "fixed_input_end_date": fixed_end.strftime("%Y-%m-%d") if fixed_end is not None else "",
            "fixed_input_month_end_count": fixed_input_count(rolling, basis) if basis in FIXED_INPUTS else "",
        }
        if basis in FIXED_INPUTS:
            row["matches_fixed_input_start"] = selected["start_date"] == row["fixed_input_start_date"]
            row["matches_fixed_input_end"] = selected["end_date"] == row["fixed_input_end_date"]
            row["matches_fixed_input_count"] = selected["month_end_count"] == row["fixed_input_month_end_count"]
        else:
            row["matches_fixed_input_start"] = ""
            row["matches_fixed_input_end"] = ""
            row["matches_fixed_input_count"] = ""
        rows.append(row)

    w500 = rolling[rolling["window_length"] == 500][["date", "strict_pass"]].rename(
        columns={"strict_pass": "strict_pass_500d"}
    )
    w730 = rolling[rolling["window_length"] == 730][["date", "strict_pass"]].rename(
        columns={"strict_pass": "strict_pass_730d"}
    )
    consensus = pd.merge(w500, w730, on="date", how="inner")
    consensus["consensus_pass"] = consensus["strict_pass_500d"].astype(bool) & consensus["strict_pass_730d"].astype(bool)
    selected = select_latest_sustained_run(consensus, "consensus_pass")
    rows.append(
        {
            "boundary_basis": "500d_730d_consensus_strict",
            "source_window_length": "500,730",
            "pass_definition": "strict_pass_500d_and_strict_pass_730d",
            **selected,
            "fixed_input_start_date": "",
            "fixed_input_end_date": "",
            "fixed_input_month_end_count": "",
            "matches_fixed_input_start": "",
            "matches_fixed_input_end": "",
            "matches_fixed_input_count": "",
        }
    )

    order = [
        "500d_strict",
        "730d_strict",
        "500d_730d_consensus_strict",
        "500d_borderline_tolerant",
    ]
    result = pd.DataFrame(rows)
    result["boundary_basis"] = pd.Categorical(result["boundary_basis"], categories=order, ordered=True)
    return result.sort_values("boundary_basis").reset_index(drop=True)


def fixed_subset(rolling: pd.DataFrame, basis: str) -> pd.DataFrame:
    spec = FIXED_INPUTS[basis]
    subset = rolling[
        (rolling["window_length"] == spec["window_length"])
        & (pd.to_datetime(rolling["date"]) >= spec["start_date"])
        & (pd.to_datetime(rolling["date"]) <= spec["end_date"])
    ].copy()
    return subset.sort_values("date").reset_index(drop=True)


def shoulder_subset(rolling: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(rolling["date"])
    subset = rolling[
        (rolling["window_length"] == SHOULDER["window_length"])
        & (dates > SHOULDER["start_after"])
        & (dates <= SHOULDER["end_date"])
    ].copy()
    return subset.sort_values("date").reset_index(drop=True)


def finite_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.replace([np.inf, -np.inf], np.nan).dropna()


def slope_per_month(values: pd.Series) -> float:
    numeric = finite_series(values)
    if len(numeric) < 2:
        return float("nan")
    x = np.arange(len(numeric), dtype=float)
    return float(np.polyfit(x, numeric.to_numpy(dtype=float), 1)[0])


def metric_summary(values: pd.Series) -> dict[str, float]:
    numeric = finite_series(values)
    if numeric.empty:
        return {
            "mean": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "q25": float("nan"),
            "median": float("nan"),
            "q75": float("nan"),
            "max": float("nan"),
            "start": float("nan"),
            "end": float("nan"),
            "end_minus_start": float("nan"),
            "slope_per_month": float("nan"),
            "median_absolute_monthly_change": float("nan"),
        }

    start = float(numeric.iloc[0])
    end = float(numeric.iloc[-1])
    return {
        "mean": float(numeric.mean()),
        "std": float(numeric.std(ddof=1)) if len(numeric) > 1 else float("nan"),
        "min": float(numeric.min()),
        "q25": float(numeric.quantile(0.25)),
        "median": float(numeric.median()),
        "q75": float(numeric.quantile(0.75)),
        "max": float(numeric.max()),
        "start": start,
        "end": end,
        "end_minus_start": float(end - start),
        "slope_per_month": slope_per_month(numeric),
        "median_absolute_monthly_change": float(numeric.diff().abs().dropna().median())
        if len(numeric) > 1
        else float("nan"),
    }


def regime_summary(rolling: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for basis in ["500d_strict", "730d_strict"]:
        subset = fixed_subset(rolling, basis)
        spec = FIXED_INPUTS[basis]
        for metric in ROLLING_METRICS:
            stats = metric_summary(subset[metric])
            rows.append(
                {
                    "basis": basis,
                    "window_length": spec["window_length"],
                    "fixed_start_date": spec["start_date"].strftime("%Y-%m-%d"),
                    "fixed_end_date": spec["end_date"].strftime("%Y-%m-%d"),
                    "observation_count": int(len(subset)),
                    "start_observation_date": str(subset.iloc[0]["date"]) if not subset.empty else "",
                    "end_observation_date": str(subset.iloc[-1]["date"]) if not subset.empty else "",
                    "metric": metric,
                    **stats,
                }
            )
    return pd.DataFrame(rows)


def transformed_subregime_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    positive_floor = np.nextafter(0.0, 1.0)
    eg_p = pd.to_numeric(frame["eg_p"], errors="coerce").where(lambda values: values > 0, np.nan)
    adf_p = pd.to_numeric(frame["adf_p"], errors="coerce").where(lambda values: values > 0, np.nan)
    transformed = pd.DataFrame(
        {
            "beta": frame["beta"].to_numpy(dtype=float),
            "half_life": frame["half_life"].to_numpy(dtype=float),
            "spread_std": frame["spread_std"].to_numpy(dtype=float),
            "spread_daily_change_std": frame["spread_daily_change_std"].to_numpy(dtype=float),
            "neg_log10_eg_p": -np.log10(eg_p.fillna(positive_floor).clip(lower=positive_floor)),
            "neg_log10_adf_p": -np.log10(adf_p.fillna(positive_floor).clip(lower=positive_floor)),
        }
    )
    interpolated = (
        transformed.replace([np.inf, -np.inf], np.nan)
        .interpolate(method="linear", limit_direction="both")
        .fillna(0.0)
    )
    means = interpolated.mean(axis=0)
    stds = interpolated.std(axis=0, ddof=0)
    standardized = (interpolated - means) / stds.replace(0.0, np.nan)
    return standardized.fillna(0.0)


def within_segment_rss(values: np.ndarray) -> float:
    if len(values) == 0:
        return 0.0
    centered = values - values.mean(axis=0, keepdims=True)
    return float(np.sum(centered * centered))


def best_split(values: np.ndarray, min_seg: int) -> tuple[int, float, float]:
    total_rss = within_segment_rss(values)
    if total_rss <= 0:
        return min_seg, 0.0, 0.0

    best_idx = min_seg
    best_rss = float("inf")
    for split_idx in range(min_seg, len(values) - min_seg + 1):
        rss = within_segment_rss(values[:split_idx]) + within_segment_rss(values[split_idx:])
        if rss < best_rss:
            best_idx = split_idx
            best_rss = rss
    improvement = 1.0 - best_rss / total_rss
    return best_idx, float(best_rss), float(improvement)


def permutation_p_value(
    values: np.ndarray,
    min_seg: int,
    observed_improvement: float,
    rng: np.random.Generator,
    permutation_count: int = 2000,
) -> float:
    count = 0
    for _ in range(permutation_count):
        order = rng.permutation(len(values))
        _, _, perm_improvement = best_split(values[order], min_seg)
        if perm_improvement >= observed_improvement:
            count += 1
    return float((count + 1) / (permutation_count + 1))


def subregime_tests(rolling: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(20260705)

    for basis in ["500d_strict", "730d_strict"]:
        subset = fixed_subset(rolling, basis)
        values = transformed_subregime_metrics(subset).to_numpy(dtype=float)
        n_obs = len(values)
        min_seg = min(6, max(3, n_obs // 4))
        split_idx, best_rss, improvement = best_split(values, min_seg)
        p_value = permutation_p_value(values, min_seg, improvement, rng, permutation_count=2000)
        total_rss = within_segment_rss(values)
        interpretation = "natural_split_supported" if p_value < 0.05 and improvement >= 0.25 else "no_clear_split"
        rows.append(
            {
                "basis": basis,
                "window_length": FIXED_INPUTS[basis]["window_length"],
                "fixed_start_date": FIXED_INPUTS[basis]["start_date"].strftime("%Y-%m-%d"),
                "fixed_end_date": FIXED_INPUTS[basis]["end_date"].strftime("%Y-%m-%d"),
                "observation_count": int(n_obs),
                "min_seg": int(min_seg),
                "best_split_index": int(split_idx),
                "left_segment_count": int(split_idx),
                "right_segment_count": int(n_obs - split_idx),
                "split_after_date": str(subset.iloc[split_idx - 1]["date"]),
                "split_before_date": str(subset.iloc[split_idx]["date"]) if split_idx < n_obs else "",
                "total_rss": float(total_rss),
                "best_rss": float(best_rss),
                "rss_improvement_ratio": float(improvement),
                "permutation_count": 2000,
                "permutation_p_value": float(p_value),
                "interpretation": interpretation,
                "rng_seed": 20260705,
                "rng_call_pattern": "single default_rng seeded once; 2000 row-level permutations for 500d_strict, then 2000 for 730d_strict; one rng.permutation call per permutation",
                "zscore_ddof": 0,
                "gap_handling": "linear interpolation with both-direction endpoint fill before z-scoring",
            }
        )
    return pd.DataFrame(rows)


def trend_stats(values: pd.Series) -> dict[str, Any]:
    numeric = finite_series(values)
    if numeric.empty:
        return {
            "start": float("nan"),
            "end": float("nan"),
            "end_minus_start": float("nan"),
            "slope_per_month": float("nan"),
            "first_half_mean": float("nan"),
            "second_half_mean": float("nan"),
            "first_half_count": 0,
            "second_half_count": 0,
        }

    midpoint = len(numeric) // 2
    first_half = numeric.iloc[:midpoint]
    second_half = numeric.iloc[midpoint:]
    start = float(numeric.iloc[0])
    end = float(numeric.iloc[-1])
    return {
        "start": start,
        "end": end,
        "end_minus_start": float(end - start),
        "slope_per_month": slope_per_month(numeric),
        "first_half_mean": float(first_half.mean()) if not first_half.empty else float("nan"),
        "second_half_mean": float(second_half.mean()) if not second_half.empty else float("nan"),
        "first_half_count": int(len(first_half)),
        "second_half_count": int(len(second_half)),
    }


def degradation_diagnostics(rolling: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    frames = [
        ("500d_strict", FIXED_INPUTS["500d_strict"]["window_length"], fixed_subset(rolling, "500d_strict")),
        ("730d_strict", FIXED_INPUTS["730d_strict"]["window_length"], fixed_subset(rolling, "730d_strict")),
        (SHOULDER["basis"], SHOULDER["window_length"], shoulder_subset(rolling)),
    ]
    metrics = ["beta", "half_life", "eg_p", "adf_p", "spread_std", "spread_daily_change_std"]
    for basis, window_length, subset in frames:
        for metric in metrics:
            stats = trend_stats(subset[metric])
            rows.append(
                {
                    "basis": basis,
                    "window_length": window_length,
                    "diagnostic_start_date": str(subset.iloc[0]["date"]) if not subset.empty else "",
                    "diagnostic_end_date": str(subset.iloc[-1]["date"]) if not subset.empty else "",
                    "observation_count": int(len(subset)),
                    "metric": metric,
                    **stats,
                }
            )
    return pd.DataFrame(rows)


def dataframe_csv_body(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False, lineterminator="\n", float_format="%.15g")
    return buffer.getvalue()


def provenance_header(
    body: str,
    script_path: Path,
    commit: str,
    timestamp_utc: str,
    output_name: str,
    style: str,
) -> tuple[str, str]:
    content_hash = sha256_bytes(body.encode("utf-8"))
    lines = [
        f"script_path: {script_path}",
        f"git_commit: {commit}",
        f"snapshot_id: {SNAPSHOT_ID}",
        f"execution_timestamp_utc: {timestamp_utc}",
        f"output_name: {output_name}",
        f"output_content_sha256: {content_hash}",
        "output_hash_scope: bytes after this provenance header",
        "final_file_sha256: recorded in provenance.json",
    ]
    if style == "csv":
        return "\n".join(f"# {line}" for line in lines) + "\n", content_hash
    if style == "markdown":
        return "<!--\n" + "\n".join(lines) + "\n-->\n", content_hash
    raise ValueError(f"unknown header style: {style}")


def write_output(
    path: Path,
    body: str,
    script_path: Path,
    commit: str,
    timestamp_utc: str,
    description: str,
    style: str,
) -> dict[str, Any]:
    header, content_hash = provenance_header(body, script_path, commit, timestamp_utc, path.name, style)
    path.write_text(header + body, encoding="utf-8", newline="\n")
    return {
        "path": str(path.relative_to(ROOT)),
        "description": description,
        "content_sha256": content_hash,
        "final_file_sha256": file_sha256(path),
        "hash_scope": "bytes after provenance header",
    }


def summary_body(
    boundaries: pd.DataFrame,
    summaries: pd.DataFrame,
    subregimes: pd.DataFrame,
    degradation: pd.DataFrame,
    outputs: list[dict[str, Any]],
) -> str:
    boundary_lines = [
        "| boundary_basis | status | start | end | count | fixed date match |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in boundaries.itertuples(index=False):
        if row.boundary_basis in {"500d_strict", "730d_strict"}:
            fixed_match = f"start={row.matches_fixed_input_start}; end={row.matches_fixed_input_end}; count={row.matches_fixed_input_count}"
        else:
            fixed_match = ""
        boundary_lines.append(
            f"| {row.boundary_basis} | {row.candidate_status} | {row.start_date} | {row.end_date} | {row.month_end_count} | {fixed_match} |"
        )

    subregime_lines = [
        "| basis | split_after | improvement | p_value | interpretation |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in subregimes.itertuples(index=False):
        subregime_lines.append(
            f"| {row.basis} | {row.split_after_date} | {row.rss_improvement_ratio:.12f} | {row.permutation_p_value:.12f} | {row.interpretation} |"
        )

    part2_counts = summaries.groupby("basis")["observation_count"].first().to_dict()
    part4_counts = degradation.groupby("basis")["observation_count"].first().to_dict()
    output_lines = [f"- `{output['path']}` final SHA256 `{output['final_file_sha256']}`" for output in outputs]

    return "\n".join(
        [
            "# Claim 002 Healthy Episode Characterization - Codex Tier A",
            "",
            "## Inputs",
            "",
            f"- Claim ID: `{CLAIM_ID}`",
            f"- Snapshot: `{SNAPSHOT_ID}`",
            "- Price file: `data/snapshots/tcs_infy_v1_2026-07-04/adjusted_close.csv`",
            "- Columns: `date`, `TCS.NS`, `INFY.NS`; rows missing either price dropped.",
            "- No live pulls and no snapshot regeneration.",
            "",
            "## Part 1 Boundary Candidates",
            "",
            *boundary_lines,
            "",
            "## Part 2 Regime Summary",
            "",
            f"- `500d_strict` observations: {part2_counts.get('500d_strict')}",
            f"- `730d_strict` observations: {part2_counts.get('730d_strict')}",
            "- Full metric statistics are in `episode_regime_summary.csv`.",
            "",
            "## Part 3 Sub-Regime Tests",
            "",
            *subregime_lines,
            "",
            "## Part 4 Degradation Diagnostics",
            "",
            f"- `500d_strict` observations: {part4_counts.get('500d_strict')}",
            f"- `730d_strict` observations: {part4_counts.get('730d_strict')}",
            f"- `500d_post_core_shoulder` observations: {part4_counts.get('500d_post_core_shoulder')}",
            "- `degradation_diagnostics.csv` contains numbers only.",
            "",
            "## Method Notes",
            "",
            "- Rolling metrics follow the Spec Block method: OLS with intercept, `statsmodels.coint(..., trend=\"c\", autolag=\"aic\")`, residual `adfuller(..., regression=\"n\", autolag=\"aic\")`, AR(1) residual phi with intercept, and sample spread standard deviations.",
            "- The shoulder window uses 500-day rolling metrics strictly after the fixed 500d core end and through `2023-01-31`.",
            "- For odd first/second-half splits, the first half is the first `n//2` observations and the second half is the remainder; the output records both counts.",
            "- Part 4 is descriptive numeric output only; this run makes no RL recommendation and no training-window selection.",
            "",
            "## Output Files",
            "",
            *output_lines,
            "",
        ]
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = Path(__file__).resolve()
    commit = git_commit()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    close, metadata = load_snapshot()

    rolling = compute_rolling_metrics(close)
    boundaries = boundary_candidates(rolling)
    summaries = regime_summary(rolling)
    subregimes = subregime_tests(rolling)
    degradation = degradation_diagnostics(rolling)

    outputs: list[dict[str, Any]] = []
    outputs.append(
        write_output(
            OUT_DIR / "rolling_metrics.csv",
            dataframe_csv_body(rolling),
            script_path,
            commit,
            timestamp_utc,
            "Audit-only rolling monthly metrics for all requested windows",
            "csv",
        )
    )
    outputs.append(
        write_output(
            OUT_DIR / "episode_boundary_candidates.csv",
            dataframe_csv_body(boundaries),
            script_path,
            commit,
            timestamp_utc,
            "Part 1 selected sustained healthy run by boundary basis",
            "csv",
        )
    )
    outputs.append(
        write_output(
            OUT_DIR / "episode_regime_summary.csv",
            dataframe_csv_body(summaries),
            script_path,
            commit,
            timestamp_utc,
            "Part 2 distributional statistics over fixed inputs",
            "csv",
        )
    )
    outputs.append(
        write_output(
            OUT_DIR / "subregime_tests.csv",
            dataframe_csv_body(subregimes),
            script_path,
            commit,
            timestamp_utc,
            "Part 3 exploratory single-change-point split tests",
            "csv",
        )
    )
    outputs.append(
        write_output(
            OUT_DIR / "degradation_diagnostics.csv",
            dataframe_csv_body(degradation),
            script_path,
            commit,
            timestamp_utc,
            "Part 4 descriptive trend statistics",
            "csv",
        )
    )

    summary = summary_body(boundaries, summaries, subregimes, degradation, outputs)
    outputs.append(
        write_output(
            OUT_DIR / "summary.md",
            summary,
            script_path,
            commit,
            timestamp_utc,
            "Narrative framing and output manifest",
            "markdown",
        )
    )

    provenance = {
        "claim_id": CLAIM_ID,
        "snapshot_id": SNAPSHOT_ID,
        "snapshot_adjusted_close_sha256": metadata["files"]["adjusted_close.csv"]["sha256"],
        "snapshot_adjusted_close_computed_sha256": file_sha256(SNAPSHOT_CLOSE_CSV),
        "snapshot_metadata": metadata,
        "script_path": str(script_path),
        "script_sha256": file_sha256(script_path),
        "git_commit": commit,
        "execution_timestamp_utc": timestamp_utc,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "statsmodels_version": statsmodels.__version__,
        "fixed_inputs": {
            "500d_strict": {
                "window_length": 500,
                "start_date": "2020-01-31",
                "end_date": "2021-12-31",
            },
            "730d_strict": {
                "window_length": 730,
                "start_date": "2020-12-31",
                "end_date": "2023-03-31",
            },
            "500d_post_core_shoulder": {
                "window_length": 500,
                "start_after": "2021-12-31",
                "end_date": "2023-01-31",
            },
        },
        "method": {
            "month_end_dates": "last trading day per calendar month present in the snapshot",
            "price_transform": "natural log adjusted close",
            "ols": "intercept included; beta is coefficient on log(INFY.NS)",
            "engle_granger": "statsmodels.tsa.stattools.coint(y, x, trend='c', autolag='aic')",
            "adf": "statsmodels.tsa.stattools.adfuller(resid, regression='n', autolag='aic')",
            "phi": "OLS AR(1) coefficient of resid[1:] on resid[:-1] with intercept",
            "spread_std": "sample standard deviation, ddof=1",
            "subregime_rng": "single numpy.random.default_rng(20260705); candidate order 500d_strict then 730d_strict; one rng.permutation call per permutation",
            "zscore_ddof": 0,
            "odd_half_split": "first half is first n//2 observations; second half is remainder",
        },
        "outputs": outputs,
    }
    provenance_path = OUT_DIR / "provenance.json"
    provenance_path.write_text(
        json.dumps(json_safe(provenance), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    provenance_hash = file_sha256(provenance_path)

    print(f"claim_id={CLAIM_ID}")
    print(f"snapshot_id={SNAPSHOT_ID}")
    for row in boundaries.itertuples(index=False):
        print(f"{row.boundary_basis} {row.candidate_status} {row.start_date} {row.end_date} count={row.month_end_count}")
    for row in subregimes.itertuples(index=False):
        print(
            f"{row.basis} split_after={row.split_after_date} improvement={row.rss_improvement_ratio:.12f} p={row.permutation_p_value:.12f} interpretation={row.interpretation}"
        )
    for output in outputs:
        print(f"{output['path']} {output['final_file_sha256']}")
    print(f"{provenance_path.relative_to(ROOT)} {provenance_hash}")


if __name__ == "__main__":
    main()
