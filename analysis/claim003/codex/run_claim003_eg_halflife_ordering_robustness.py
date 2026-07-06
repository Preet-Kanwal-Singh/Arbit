from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels
from scipy.stats import beta as beta_dist
from statsmodels.tsa.stattools import adfuller, coint


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

CLAIM_ID = "claim_003_eg_halflife_ordering_robustness"
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
SNAPSHOT_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
SNAPSHOT_METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
DEGRADATION_END = pd.Timestamp("2023-12-31")

WINDOW_SPECS = {
    500: {
        "core_start": pd.Timestamp("2020-01-31"),
        "core_end": pd.Timestamp("2021-12-31"),
    },
    730: {
        "core_start": pd.Timestamp("2020-12-31"),
        "core_end": pd.Timestamp("2023-03-31"),
    },
}

THRESHOLD_CONFIGS = [
    {"config_id": "C1", "description": "baseline", "eg_p_threshold": 0.05, "half_life_threshold": 20.0},
    {"config_id": "C2", "description": "EG p >= 0.03", "eg_p_threshold": 0.03, "half_life_threshold": 20.0},
    {"config_id": "C3", "description": "EG p >= 0.10", "eg_p_threshold": 0.10, "half_life_threshold": 20.0},
    {"config_id": "C4", "description": "HL > 15d", "eg_p_threshold": 0.05, "half_life_threshold": 15.0},
    {"config_id": "C5", "description": "HL > 25d", "eg_p_threshold": 0.05, "half_life_threshold": 25.0},
]


@dataclass(frozen=True)
class Ar1Fit:
    intercept: float
    phi: float
    phi_se: float
    phi_ci_low: float
    phi_ci_high: float
    residuals: np.ndarray
    residual_std: float
    n_obs: int


@dataclass(frozen=True)
class ReturnAr1Fit:
    mean: float
    phi: float
    phi_se: float
    residuals: np.ndarray
    residual_std: float
    n_obs: int


@dataclass(frozen=True)
class RegimeModel:
    window_length: int
    regime: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    n_days: int
    alpha: float
    beta: float
    spread_ar: Ar1Fit
    return_ar: ReturnAr1Fit


@dataclass(frozen=True)
class WindowModel:
    window_length: int
    core_start: pd.Timestamp
    core_end: pd.Timestamp
    degradation_start: pd.Timestamp
    degradation_end: pd.Timestamp
    pre: RegimeModel
    post: RegimeModel
    parameter_unstable: bool


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


def git_status_short() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception as exc:  # pragma: no cover - provenance fallback only
        return f"unavailable: {exc}"


def script_sha256() -> str:
    return file_sha256(Path(__file__).resolve())


def load_snapshot_prices() -> tuple[pd.DataFrame, dict[str, Any]]:
    if not SNAPSHOT_CLOSE_CSV.exists():
        raise FileNotFoundError(f"missing snapshot adjusted close data: {SNAPSHOT_CLOSE_CSV}")
    if not SNAPSHOT_METADATA_JSON.exists():
        raise FileNotFoundError(f"missing snapshot metadata: {SNAPSHOT_METADATA_JSON}")

    metadata = json.loads(SNAPSHOT_METADATA_JSON.read_text(encoding="utf-8"))
    if metadata.get("snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError(f"metadata snapshot_id mismatch: {metadata.get('snapshot_id')} != {SNAPSHOT_ID}")

    close = pd.read_csv(SNAPSHOT_CLOSE_CSV, parse_dates=["date"]).set_index("date")
    expected_columns = ["TCS.NS", "INFY.NS"]
    missing = [col for col in expected_columns if col not in close.columns]
    if missing:
        raise RuntimeError(f"missing adjusted-close columns in snapshot: {missing}")

    close = close[expected_columns].dropna()
    close = close.loc[:DEGRADATION_END]
    if close.empty:
        raise RuntimeError("snapshot adjusted-close dataframe is empty after filtering")
    return close, metadata


def ols_alpha_beta(x: np.ndarray, y: np.ndarray) -> tuple[float, float, np.ndarray]:
    design = np.column_stack([np.ones(len(x)), x])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    alpha = float(coeffs[0])
    beta = float(coeffs[1])
    residuals = y - (alpha + beta * x)
    return alpha, beta, residuals


def fit_ar1(values: np.ndarray) -> Ar1Fit:
    values = np.asarray(values, dtype=float)
    x = values[:-1]
    y = values[1:]
    design = np.column_stack([np.ones(len(x)), x])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coeffs
    residuals = y - fitted
    dof = max(len(y) - 2, 1)
    sigma2 = float(np.sum(residuals**2) / dof)
    xtx_inv = np.linalg.pinv(design.T @ design)
    se = np.sqrt(np.diag(xtx_inv) * sigma2)
    phi = float(coeffs[1])
    phi_se = float(se[1])
    return Ar1Fit(
        intercept=float(coeffs[0]),
        phi=phi,
        phi_se=phi_se,
        phi_ci_low=phi - 1.96 * phi_se,
        phi_ci_high=phi + 1.96 * phi_se,
        residuals=residuals.astype(float),
        residual_std=float(np.std(residuals, ddof=1)),
        n_obs=int(len(y)),
    )


def fit_return_ar1(returns: np.ndarray) -> ReturnAr1Fit:
    returns = np.asarray(returns, dtype=float)
    mean = float(np.mean(returns))
    x = returns[:-1] - mean
    y = returns[1:] - mean
    denom = float(x @ x)
    phi = float((x @ y) / denom) if denom > 0 else 0.0
    residuals = y - phi * x
    dof = max(len(y) - 1, 1)
    sigma2 = float(np.sum(residuals**2) / dof)
    phi_se = float(math.sqrt(sigma2 / denom)) if denom > 0 else float("nan")
    return ReturnAr1Fit(
        mean=mean,
        phi=phi,
        phi_se=phi_se,
        residuals=residuals.astype(float),
        residual_std=float(np.std(residuals, ddof=1)),
        n_obs=int(len(y)),
    )


def half_life_from_residuals(residuals: np.ndarray) -> tuple[float, float]:
    ar = fit_ar1(residuals)
    phi = ar.phi
    if phi <= 0:
        return phi, float("nan")
    if phi >= 1:
        return phi, float("inf")
    return phi, float(-math.log(2.0) / math.log(phi))


def safe_coint_p_value(y: np.ndarray, x: np.ndarray) -> float:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return float(coint(y, x, trend="c", autolag="aic")[1])
    except Exception:
        return float("nan")


def safe_adf_p_value(values: np.ndarray) -> float:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return float(adfuller(values, regression="n", autolag="aic")[1])
    except Exception:
        return float("nan")


def month_end_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    series = pd.Series(index=index, data=index)
    return list(series.groupby(series.index.to_period("M")).max())


def first_trading_day_after(index: pd.DatetimeIndex, date: pd.Timestamp) -> pd.Timestamp:
    later = index[index > date]
    if later.empty:
        raise RuntimeError(f"no trading day after {date.date()}")
    return pd.Timestamp(later[0])


def fit_regime_model(
    logs: pd.DataFrame,
    window_length: int,
    regime: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> RegimeModel:
    subset = logs.loc[start_date:end_date]
    if len(subset) < 30:
        raise RuntimeError(f"{window_length}d {regime} regime has too few rows: {len(subset)}")

    x = subset["INFY.NS"].to_numpy(dtype=float)
    y = subset["TCS.NS"].to_numpy(dtype=float)
    alpha, beta, spread = ols_alpha_beta(x, y)
    returns = np.diff(x)
    return RegimeModel(
        window_length=window_length,
        regime=regime,
        start_date=pd.Timestamp(subset.index[0]),
        end_date=pd.Timestamp(subset.index[-1]),
        n_days=int(len(subset)),
        alpha=alpha,
        beta=beta,
        spread_ar=fit_ar1(spread),
        return_ar=fit_return_ar1(returns),
    )


def build_window_model(logs: pd.DataFrame, window_length: int) -> WindowModel:
    spec = WINDOW_SPECS[window_length]
    core_start = spec["core_start"]
    core_end = spec["core_end"]
    degradation_start = first_trading_day_after(logs.index, core_end)
    pre = fit_regime_model(logs, window_length, "pre_core", core_start, core_end)
    post = fit_regime_model(logs, window_length, "degradation", degradation_start, DEGRADATION_END)
    return WindowModel(
        window_length=window_length,
        core_start=core_start,
        core_end=core_end,
        degradation_start=degradation_start,
        degradation_end=pd.Timestamp(logs.loc[:DEGRADATION_END].index[-1]),
        pre=pre,
        post=post,
        parameter_unstable=bool(post.spread_ar.phi_ci_high >= 0.98),
    )


def rolling_metrics_for_eval_dates(
    log_tcs: np.ndarray,
    log_infy: np.ndarray,
    dates: pd.DatetimeIndex,
    eval_dates: list[pd.Timestamp],
    window_length: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    date_to_pos = {pd.Timestamp(date): i for i, date in enumerate(dates)}
    for eval_date in eval_dates:
        end_pos = date_to_pos[pd.Timestamp(eval_date)]
        start_pos = end_pos - window_length + 1
        if start_pos < 0:
            continue
        y = log_tcs[start_pos : end_pos + 1]
        x = log_infy[start_pos : end_pos + 1]
        alpha, beta, residuals = ols_alpha_beta(x, y)
        spread_phi, half_life = half_life_from_residuals(residuals)
        rows.append(
            {
                "date": pd.Timestamp(eval_date),
                "window_start_date": pd.Timestamp(dates[start_pos]),
                "window_length": window_length,
                "beta": beta,
                "alpha": alpha,
                "engle_granger_p_value": safe_coint_p_value(y, x),
                "adf_p_value": safe_adf_p_value(residuals),
                "spread_phi": spread_phi,
                "half_life": half_life,
            }
        )
    return rows


def crossing_indices(metrics: list[dict[str, Any]], eg_threshold: float, half_life_threshold: float) -> tuple[int | None, int | None]:
    eg_idx: int | None = None
    hl_idx: int | None = None
    for i, row in enumerate(metrics):
        eg_p = float(row["engle_granger_p_value"])
        half_life = float(row["half_life"])
        if eg_idx is None and math.isfinite(eg_p) and eg_p >= eg_threshold:
            eg_idx = i
        if hl_idx is None and not math.isnan(half_life) and half_life > half_life_threshold:
            hl_idx = i
    return eg_idx, hl_idx


def order_label(eg_idx: int | None, hl_idx: int | None) -> str:
    if eg_idx is None and hl_idx is None:
        return "NEITHER"
    if eg_idx is not None and hl_idx is None:
        return "EG_ONLY"
    if eg_idx is None and hl_idx is not None:
        return "HL_ONLY"
    if eg_idx == hl_idx:
        return "SIMULTANEOUS"
    if eg_idx is not None and hl_idx is not None and eg_idx < hl_idx:
        return "EG_FIRST"
    return "HL_FIRST"


def empty_counts() -> dict[str, dict[str, int]]:
    return {
        config["config_id"]: {"EG_FIRST": 0, "HL_FIRST": 0, "EG_ONLY": 0, "HL_ONLY": 0, "NEITHER": 0, "SIMULTANEOUS": 0}
        for config in THRESHOLD_CONFIGS
    }


def merge_counts(target: dict[str, dict[str, int]], source: dict[str, dict[str, int]]) -> None:
    for config_id, labels in source.items():
        for label, value in labels.items():
            target[config_id][label] += int(value)


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    low = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
    high = 1.0 if k == n else float(beta_dist.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return low, high


def classify_cell(eg_first: int, hl_first: int) -> tuple[str, float, float, float, int, bool]:
    effective_n = eg_first + hl_first
    if effective_n == 0:
        return "INCONCLUSIVE", float("nan"), float("nan"), float("nan"), 0, False
    p_hat = eg_first / effective_n
    ci_low, ci_high = clopper_pearson(eg_first, effective_n)
    adequate = effective_n >= 100
    if ci_low > 0.5:
        classification = "ROBUST"
    elif ci_high < 0.5:
        classification = "CONTRADICTED"
    else:
        classification = "INCONCLUSIVE"
    return classification, p_hat, ci_low, ci_high, effective_n, adequate


def simulate_log_paths(
    actual_logs: pd.DataFrame,
    model: WindowModel,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    dates = actual_logs.index
    n = len(dates)
    log_infy = np.empty(n, dtype=float)
    spread = np.empty(n, dtype=float)
    log_tcs = np.empty(n, dtype=float)

    pre = model.pre
    log_infy[0] = float(actual_logs["INFY.NS"].iloc[0])
    spread[0] = float(actual_logs["TCS.NS"].iloc[0] - (pre.alpha + pre.beta * log_infy[0]))
    log_tcs[0] = pre.alpha + pre.beta * log_infy[0] + spread[0]
    previous_return = pre.return_ar.mean

    for i in range(1, n):
        regime = model.pre if dates[i] <= model.core_end else model.post

        return_eps = float(rng.choice(regime.return_ar.residuals))
        current_return = regime.return_ar.mean + regime.return_ar.phi * (previous_return - regime.return_ar.mean) + return_eps
        log_infy[i] = log_infy[i - 1] + current_return

        spread_eps = float(rng.choice(regime.spread_ar.residuals))
        spread[i] = regime.spread_ar.intercept + regime.spread_ar.phi * spread[i - 1] + spread_eps
        log_tcs[i] = regime.alpha + regime.beta * log_infy[i] + spread[i]
        previous_return = current_return

    return log_tcs, log_infy


def degradation_eval_dates(index: pd.DatetimeIndex, core_end: pd.Timestamp) -> list[pd.Timestamp]:
    return [
        date
        for date in month_end_dates(index)
        if pd.Timestamp(date) > core_end and pd.Timestamp(date) <= DEGRADATION_END
    ]


def simulate_counts_chunk(
    logs: pd.DataFrame,
    model: WindowModel,
    replicate_seeds: np.ndarray,
) -> tuple[dict[str, dict[str, int]], int]:
    window_length = model.window_length
    eval_dates = degradation_eval_dates(logs.index, model.core_end)
    counts = empty_counts()
    for seed in replicate_seeds:
        rng = np.random.default_rng(int(seed))
        sim_tcs, sim_infy = simulate_log_paths(logs, model, rng)
        sim_metrics = rolling_metrics_for_eval_dates(sim_tcs, sim_infy, logs.index, eval_dates, window_length)
        for config in THRESHOLD_CONFIGS:
            eg_idx, hl_idx = crossing_indices(sim_metrics, config["eg_p_threshold"], config["half_life_threshold"])
            counts[config["config_id"]][order_label(eg_idx, hl_idx)] += 1
    return counts, int(len(replicate_seeds))


def run_window_simulation(
    logs: pd.DataFrame,
    model: WindowModel,
    replicate_seeds: np.ndarray,
    progress_every: int,
    workers: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    window_length = model.window_length
    eval_dates = degradation_eval_dates(logs.index, model.core_end)
    real_metrics = rolling_metrics_for_eval_dates(
        logs["TCS.NS"].to_numpy(dtype=float),
        logs["INFY.NS"].to_numpy(dtype=float),
        logs.index,
        eval_dates,
        window_length,
    )

    counts = empty_counts()
    if workers > 1 and len(replicate_seeds) > 1:
        chunk_count = min(workers, len(replicate_seeds))
        chunks = [chunk for chunk in np.array_split(replicate_seeds, chunk_count) if len(chunk) > 0]
        completed = 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=chunk_count) as executor:
            futures = [executor.submit(simulate_counts_chunk, logs, model, chunk) for chunk in chunks]
            for future in concurrent.futures.as_completed(futures):
                partial_counts, partial_n = future.result()
                merge_counts(counts, partial_counts)
                completed += partial_n
                if progress_every > 0:
                    print(f"{window_length}d simulation {completed}/{len(replicate_seeds)}", flush=True)
    else:
        for rep_idx, seed in enumerate(replicate_seeds, start=1):
            partial_counts, _ = simulate_counts_chunk(logs, model, np.asarray([seed], dtype=np.int64))
            merge_counts(counts, partial_counts)
            if progress_every > 0 and rep_idx % progress_every == 0:
                print(f"{window_length}d simulation {rep_idx}/{len(replicate_seeds)}", flush=True)

    cell_rows: list[dict[str, Any]] = []
    anchor_rows: list[dict[str, Any]] = []
    b = int(len(replicate_seeds))

    for config in THRESHOLD_CONFIGS:
        config_id = config["config_id"]
        config_counts = counts[config_id]
        classification, p_hat, ci_low, ci_high, effective_n, adequate_n = classify_cell(
            config_counts["EG_FIRST"],
            config_counts["HL_FIRST"],
        )
        parameter_flag = bool(model.parameter_unstable)

        real_eg_idx, real_hl_idx = crossing_indices(real_metrics, config["eg_p_threshold"], config["half_life_threshold"])
        real_order = order_label(real_eg_idx, real_hl_idx)
        real_eg_row = real_metrics[real_eg_idx] if real_eg_idx is not None else None
        real_hl_row = real_metrics[real_hl_idx] if real_hl_idx is not None else None

        cell_rows.append(
            {
                "claim_id": CLAIM_ID,
                "window_length": window_length,
                "config_id": config_id,
                "config_description": config["description"],
                "eg_p_threshold": config["eg_p_threshold"],
                "half_life_threshold": config["half_life_threshold"],
                "replicates": b,
                "count_EG_first": config_counts["EG_FIRST"],
                "count_HL_first": config_counts["HL_FIRST"],
                "count_EG_only": config_counts["EG_ONLY"],
                "count_HL_only": config_counts["HL_ONLY"],
                "count_neither": config_counts["NEITHER"],
                "count_simultaneous": config_counts["SIMULTANEOUS"],
                "effective_N": effective_n,
                "p_hat_EG_first_given_ordered": p_hat,
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "adequate_N": adequate_n,
                "rate_EG_first": config_counts["EG_FIRST"] / b,
                "rate_HL_first": config_counts["HL_FIRST"] / b,
                "rate_EG_only": config_counts["EG_ONLY"] / b,
                "rate_HL_only": config_counts["HL_ONLY"] / b,
                "rate_neither": config_counts["NEITHER"] / b,
                "rate_simultaneous": config_counts["SIMULTANEOUS"] / b,
                "classification": classification,
                "classification_with_parameter_flag": f"{classification} - PARAMETER-UNSTABLE" if parameter_flag else classification,
                "parameter_unstable": parameter_flag,
                "phi_pre": model.pre.spread_ar.phi,
                "phi_pre_se": model.pre.spread_ar.phi_se,
                "phi_post": model.post.spread_ar.phi,
                "phi_post_se": model.post.spread_ar.phi_se,
                "phi_post_ci_low": model.post.spread_ar.phi_ci_low,
                "phi_post_ci_high": model.post.spread_ar.phi_ci_high,
                "real_eg_cross_date": real_eg_row["date"].strftime("%Y-%m-%d") if real_eg_row else "",
                "real_eg_cross_p_value": real_eg_row["engle_granger_p_value"] if real_eg_row else np.nan,
                "real_hl_cross_date": real_hl_row["date"].strftime("%Y-%m-%d") if real_hl_row else "",
                "real_hl_cross_half_life": real_hl_row["half_life"] if real_hl_row else np.nan,
                "real_actual_order": real_order,
            }
        )

        anchor_rows.append(
            {
                "window_length": window_length,
                "config_id": config_id,
                "eg_p_threshold": config["eg_p_threshold"],
                "half_life_threshold": config["half_life_threshold"],
                "real_eg_cross_date": real_eg_row["date"].strftime("%Y-%m-%d") if real_eg_row else "",
                "real_eg_cross_p_value": real_eg_row["engle_granger_p_value"] if real_eg_row else np.nan,
                "real_hl_cross_date": real_hl_row["date"].strftime("%Y-%m-%d") if real_hl_row else "",
                "real_hl_cross_half_life": real_hl_row["half_life"] if real_hl_row else np.nan,
                "real_actual_order": real_order,
                "real_anchor_used_in_classification": False,
            }
        )

    real_metrics_rows = []
    for row in real_metrics:
        out = dict(row)
        out["date"] = out["date"].strftime("%Y-%m-%d")
        out["window_start_date"] = out["window_start_date"].strftime("%Y-%m-%d")
        real_metrics_rows.append(out)

    return pd.DataFrame(cell_rows), pd.DataFrame(anchor_rows), pd.DataFrame(real_metrics_rows)


def summarize_window(cell_df: pd.DataFrame, model: WindowModel) -> dict[str, Any]:
    classifications = list(cell_df["classification"])
    if "CONTRADICTED" in classifications:
        classification = "CONTRADICTED"
    elif all(value == "ROBUST" for value in classifications):
        classification = "ROBUST"
    else:
        classification = "INCONCLUSIVE"
    return {
        "window_length": model.window_length,
        "classification": classification,
        "well_powered": bool(cell_df["adequate_N"].all()),
        "parameter_stable": not model.parameter_unstable,
        "parameter_unstable": bool(model.parameter_unstable),
        "unstable_cells": ",".join(cell_df.loc[cell_df["parameter_unstable"], "config_id"].astype(str)),
        "min_effective_N": int(cell_df["effective_N"].min()),
        "max_effective_N": int(cell_df["effective_N"].max()),
        "phi_pre": model.pre.spread_ar.phi,
        "phi_pre_se": model.pre.spread_ar.phi_se,
        "phi_post": model.post.spread_ar.phi,
        "phi_post_se": model.post.spread_ar.phi_se,
        "phi_post_ci_low": model.post.spread_ar.phi_ci_low,
        "phi_post_ci_high": model.post.spread_ar.phi_ci_high,
    }


def study_level_status(window_summary: pd.DataFrame) -> str:
    summaries = {int(row.window_length): row for row in window_summary.itertuples(index=False)}
    classifications = [row.classification for row in summaries.values()]
    contradicted = [row for row in summaries.values() if row.classification == "CONTRADICTED"]
    if contradicted:
        unstable = [f"{int(row.window_length)}d" for row in contradicted if bool(row.parameter_unstable)]
        if unstable:
            return f"CONTRADICTED - PARAMETER-UNSTABLE: {', '.join(unstable)}"
        return "CONTRADICTED"

    if all(value == "ROBUST" for value in classifications):
        unstable = [f"{int(row.window_length)}d" for row in summaries.values() if bool(row.parameter_unstable)]
        if unstable:
            return f"ROBUST - PARAMETER-UNSTABLE: {', '.join(unstable)}"
        return "ROBUST"

    well_powered = all(bool(row.well_powered) for row in summaries.values())
    parameter_stable = all(bool(row.parameter_stable) for row in summaries.values())
    if well_powered and parameter_stable:
        if "ROBUST" in classifications and "INCONCLUSIVE" in classifications:
            return "WINDOW-LENGTH-DEPENDENT"
        return "INCONCLUSIVE - GENUINE AMBIGUITY"

    reasons = []
    if not well_powered:
        weak = [f"{int(row.window_length)}d" for row in summaries.values() if not bool(row.well_powered)]
        reasons.append(f"INSUFFICIENT DATA: {', '.join(weak)}")
    if not parameter_stable:
        unstable = [f"{int(row.window_length)}d" for row in summaries.values() if not bool(row.parameter_stable)]
        reasons.append(f"PARAMETER-UNSTABLE: {', '.join(unstable)}")
    return "INCONCLUSIVE - " + " and ".join(reasons)


def regime_rows(models: list[WindowModel]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model in models:
        for regime in [model.pre, model.post]:
            rows.append(
                {
                    "window_length": regime.window_length,
                    "regime": regime.regime,
                    "start_date": regime.start_date.strftime("%Y-%m-%d"),
                    "end_date": regime.end_date.strftime("%Y-%m-%d"),
                    "n_days": regime.n_days,
                    "alpha": regime.alpha,
                    "beta": regime.beta,
                    "spread_ar_intercept": regime.spread_ar.intercept,
                    "spread_phi": regime.spread_ar.phi,
                    "spread_phi_se": regime.spread_ar.phi_se,
                    "spread_phi_ci_low": regime.spread_ar.phi_ci_low,
                    "spread_phi_ci_high": regime.spread_ar.phi_ci_high,
                    "spread_ar_residual_std": regime.spread_ar.residual_std,
                    "spread_ar_residual_n": len(regime.spread_ar.residuals),
                    "infy_return_mean": regime.return_ar.mean,
                    "infy_return_phi": regime.return_ar.phi,
                    "infy_return_phi_se": regime.return_ar.phi_se,
                    "infy_return_residual_std": regime.return_ar.residual_std,
                    "infy_return_residual_n": len(regime.return_ar.residuals),
                    "parameter_unstable": bool(regime.regime == "degradation" and regime.spread_ar.phi_ci_high >= 0.98),
                }
            )
    return pd.DataFrame(rows)


def to_csv_body(df: pd.DataFrame) -> str:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def provenance_header(
    body: str,
    script_path: Path,
    commit: str,
    timestamp_utc: str,
    comment_prefix: str,
    hash_scope: str,
) -> tuple[str, str]:
    content_hash = sha256_bytes(body.encode("utf-8"))
    if comment_prefix == "<!--":
        lines = [
            "<!--",
            f"script_path: {script_path}",
            f"git_commit: {commit}",
            f"snapshot_id: {SNAPSHOT_ID}",
            f"timestamp_utc: {timestamp_utc}",
            f"output_content_sha256: {content_hash}",
            f"output_hash_scope: {hash_scope}",
            "final_file_sha256: recorded in output_manifest.csv",
            "-->",
        ]
    else:
        lines = [
            f"{comment_prefix} script_path: {script_path}",
            f"{comment_prefix} git_commit: {commit}",
            f"{comment_prefix} snapshot_id: {SNAPSHOT_ID}",
            f"{comment_prefix} timestamp_utc: {timestamp_utc}",
            f"{comment_prefix} output_content_sha256: {content_hash}",
            f"{comment_prefix} output_hash_scope: {hash_scope}",
            f"{comment_prefix} final_file_sha256: recorded in output_manifest.csv",
        ]
    return "\n".join(lines) + "\n", content_hash


def write_text_output(
    path: Path,
    body: str,
    script_path: Path,
    commit: str,
    timestamp_utc: str,
    description: str,
    comment_prefix: str = "#",
    hash_scope: str = "bytes after this provenance header",
) -> dict[str, Any]:
    header, content_hash = provenance_header(body, script_path, commit, timestamp_utc, comment_prefix, hash_scope)
    text = header + body
    path.write_text(text, encoding="utf-8", newline="\n")
    return {
        "path": str(path.relative_to(ROOT)),
        "description": description,
        "content_sha256": content_hash,
        "final_file_sha256": file_sha256(path),
        "hash_scope": hash_scope,
    }


def finite_or_text(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, np.floating):
        return finite_or_text(float(value))
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, dict):
        return {str(k): finite_or_text(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite_or_text(v) for v in value]
    return value


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    subset = df[columns].copy()
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = [header, separator]
    for row in subset.itertuples(index=False):
        rows.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(rows)


def make_summary_body(
    cell_results: pd.DataFrame,
    window_summary: pd.DataFrame,
    study_status: str,
    outputs: list[dict[str, Any]],
    args: argparse.Namespace,
) -> str:
    display_cells = cell_results[
        [
            "window_length",
            "config_id",
            "effective_N",
            "p_hat_EG_first_given_ordered",
            "ci95_low",
            "ci95_high",
            "adequate_N",
            "classification",
            "parameter_unstable",
            "real_actual_order",
        ]
    ].copy()
    for col in ["p_hat_EG_first_given_ordered", "ci95_low", "ci95_high"]:
        display_cells[col] = display_cells[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")

    display_windows = window_summary[
        [
            "window_length",
            "classification",
            "well_powered",
            "parameter_stable",
            "min_effective_N",
            "max_effective_N",
            "phi_pre",
            "phi_post",
            "phi_post_ci_high",
        ]
    ].copy()
    for col in ["phi_pre", "phi_post", "phi_post_ci_high"]:
        display_windows[col] = display_windows[col].map(lambda x: f"{x:.6f}")

    manifest_lines = [
        f"- `{row['path']}` final SHA256 `{row['final_file_sha256']}`"
        for row in outputs
    ]

    return f"""# Claim 003 EG Half-Life Ordering Robustness - Codex

## Study-Level Result

{study_status}

## Window Summary

{markdown_table(display_windows, list(display_windows.columns))}

## Cell Summary

{markdown_table(display_cells, list(display_cells.columns))}

## Method Notes

- Claim id: `{CLAIM_ID}`.
- Snapshot: `{SNAPSHOT_ID}`, `adjusted_close.csv`, no substitution or refresh.
- Replicates: `{args.replicates}`. Seed: `{args.seed}`.
- Rolling pipeline: log adjusted closes; TCS dependent, INFY regressor; intercept-inclusive OLS slope beta; residual spread equals `log(TCS) - (alpha + beta * log(INFY))` for ADF and half-life. This matches the claim 002 core-boundary convention used by the supplied strict healthy cores.
- Engle-Granger call: `statsmodels.tsa.stattools.coint(trend="c", autolag="aic")`.
- Residual ADF call: `adfuller(regression="n", autolag="aic")`.
- Half-life: `-log(2) / log(phi)` for `0 < phi < 1`, `inf` for `phi >= 1`, and blank/NaN for `phi <= 0`.
- Fixed-transition simulation: pre parameters are estimated on the strict core and applied to the full simulated pre-transition history needed by the rolling windows; post parameters start after the fixed core-end transition.
- INFY return process is AR(1) on daily log returns with a residual pool; this preserves first-order serial correlation, not volatility clustering.
- Real-data crossing dates are anchors only and are not used in the simulation classification.
- 500d and 730d cores/degradation windows overlap; non-robust or window-length-dependent results reflect overlapping procedures, not independent procedures.

## Output Hashes

{chr(10).join(manifest_lines)}
"""


def write_json(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(finite_or_text(data), indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.write_text(body, encoding="utf-8", newline="\n")
    return {
        "path": str(path.relative_to(ROOT)),
        "description": "Run provenance and method metadata",
        "content_sha256": sha256_bytes(body.encode("utf-8")),
        "final_file_sha256": file_sha256(path),
        "hash_scope": "entire JSON file",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.replicates <= 0:
        raise ValueError("--replicates must be positive")

    script_path = Path(__file__).resolve()
    commit = git_commit()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    close, snapshot_metadata = load_snapshot_prices()
    logs = np.log(close)

    models = [build_window_model(logs, window_length) for window_length in sorted(WINDOW_SPECS)]

    master_rng = np.random.default_rng(args.seed)
    all_cell_results: list[pd.DataFrame] = []
    all_anchor_results: list[pd.DataFrame] = []
    all_real_metrics: list[pd.DataFrame] = []
    for model in models:
        seeds = master_rng.integers(0, np.iinfo(np.int64).max, size=args.replicates, dtype=np.int64)
        cells, anchors, real_metrics = run_window_simulation(logs, model, seeds, args.progress_every, args.workers)
        all_cell_results.append(cells)
        all_anchor_results.append(anchors)
        all_real_metrics.append(real_metrics)

    cell_results = pd.concat(all_cell_results, ignore_index=True)
    real_anchors = pd.concat(all_anchor_results, ignore_index=True)
    real_rolling_metrics = pd.concat(all_real_metrics, ignore_index=True)
    regimes = regime_rows(models)
    window_summary = pd.DataFrame(
        [
            summarize_window(cell_results[cell_results["window_length"] == model.window_length], model)
            for model in models
        ]
    )
    study_status = study_level_status(window_summary)

    outputs: list[dict[str, Any]] = []
    outputs.append(
        write_text_output(
            OUT_DIR / "cell_results.csv",
            to_csv_body(cell_results),
            script_path,
            commit,
            timestamp_utc,
            "Per-window and per-threshold simulation counts, rates, intervals, and classifications",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "window_summary.csv",
            to_csv_body(window_summary),
            script_path,
            commit,
            timestamp_utc,
            "Per-window classification and power/stability status",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "regime_parameters.csv",
            to_csv_body(regimes),
            script_path,
            commit,
            timestamp_utc,
            "Pre-core and degradation fixed-transition model parameters",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "real_data_anchors.csv",
            to_csv_body(real_anchors),
            script_path,
            commit,
            timestamp_utc,
            "Real-data crossing anchors, excluded from classification",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "real_rolling_metrics.csv",
            to_csv_body(real_rolling_metrics),
            script_path,
            commit,
            timestamp_utc,
            "Real-data rolling diagnostics over each degradation window",
        )
    )

    provenance_data = {
        "claim_id": CLAIM_ID,
        "script_path": str(script_path),
        "script_sha256": script_sha256(),
        "git_commit": commit,
        "git_status_short_at_run": git_status_short(),
        "snapshot_id": SNAPSHOT_ID,
        "snapshot_adjusted_close_sha256": snapshot_metadata["files"]["adjusted_close.csv"]["sha256"],
        "snapshot_metadata": snapshot_metadata,
        "timestamp_utc": timestamp_utc,
        "python_executable": sys.executable,
        "statsmodels_version": statsmodels.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "replicates": args.replicates,
        "seed": args.seed,
        "workers": args.workers,
        "threshold_configs": THRESHOLD_CONFIGS,
        "window_specs": {
            str(k): {name: value.strftime("%Y-%m-%d") for name, value in spec.items()}
            for k, spec in WINDOW_SPECS.items()
        },
        "study_status": study_status,
        "classification_rule": {
            "cell": "ROBUST if 95% Clopper-Pearson CI is entirely > 0.5; CONTRADICTED if entirely < 0.5; otherwise INCONCLUSIVE; N=0 is INCONCLUSIVE with no CI.",
            "window": "CONTRADICTED if any threshold cell is CONTRADICTED; ROBUST if all five threshold cells are ROBUST; otherwise INCONCLUSIVE.",
            "study": "Spec v6 ordered rule with parameter-stability qualifiers applied before unqualified ROBUST/CONTRADICTED exits.",
        },
        "cross_implementation_agreement_rule": "Per cell, |P_hat_Codex - P_hat_Opus| <= 0.05 and identical classification including qualifiers; otherwise DISPUTED for that cell and window withheld from study-level conclusion.",
        "method_assumption": "The residual spread for ADF and half-life is intercept-inclusive OLS residual, matching claim 002 core-boundary generation. The spec's beta-only spread formula is treated as shorthand.",
        "outputs": outputs,
    }
    provenance_output = write_json(OUT_DIR / "provenance.json", provenance_data)
    outputs.append(provenance_output)

    summary_body = make_summary_body(cell_results, window_summary, study_status, outputs, args)
    outputs.append(
        write_text_output(
            OUT_DIR / "summary.md",
            summary_body,
            script_path,
            commit,
            timestamp_utc,
            "Human-readable study summary",
            comment_prefix="<!--",
            hash_scope="bytes after this HTML provenance header",
        )
    )

    manifest = pd.DataFrame(outputs)
    outputs.append(
        write_text_output(
            OUT_DIR / "output_manifest.csv",
            to_csv_body(manifest),
            script_path,
            commit,
            timestamp_utc,
            "Output manifest with content and final file hashes",
        )
    )

    print(f"study_status={study_status}")
    print(f"outputs_dir={OUT_DIR}")
    for row in outputs:
        print(f"{row['path']} {row['final_file_sha256']}")


if __name__ == "__main__":
    main()
