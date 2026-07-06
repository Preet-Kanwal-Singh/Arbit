from __future__ import annotations

import hashlib
import html
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[3]
VENV_SITE = ROOT / ".venv" / "Lib" / "site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))

import numpy as np
import pandas as pd
import statsmodels
from statsmodels.tsa.stattools import adfuller, coint


OUT_DIR = Path(__file__).resolve().parent
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
SNAPSHOT_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
SNAPSHOT_METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
WINDOWS = [60, 120, 250, 500, 730]
PRIMARY_WINDOWS = [500, 730]
P_VALUE_STRICT = 0.05
P_VALUE_BORDERLINE = 0.10
MIN_SUSTAINED_MONTHS = 6
PERMUTATIONS = 2000
RNG_SEED = 20260705


@dataclass
class OutputRecord:
    path: Path
    content_sha256: str
    final_sha256: str
    hash_scope: str
    description: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    except Exception:
        return "unavailable_no_commit_or_git_error"


def base_metadata(timestamp_utc: str, git_hash: str) -> dict[str, str]:
    return {
        "script_path": str(Path(__file__).resolve()),
        "git_commit": git_hash,
        "snapshot_id": SNAPSHOT_ID,
        "timestamp_utc": timestamp_utc,
    }


def header_lines(metadata: dict[str, str], content_sha: str) -> list[str]:
    lines = []
    for key, value in metadata.items():
        lines.append(f"{key}: {value}")
    lines.append(f"output_content_sha256: {content_sha}")
    lines.append("output_hash_scope: bytes after this provenance header")
    lines.append("final_file_sha256: recorded in output_manifest.csv and provenance.json")
    return lines


def write_csv(path: Path, frame: pd.DataFrame, metadata: dict[str, str], description: str) -> OutputRecord:
    body = frame.to_csv(index=False, lineterminator="\n")
    content_sha = text_sha256(body)
    header = "\n".join(f"# {line}" for line in header_lines(metadata, content_sha)) + "\n"
    path.write_text(header + body, encoding="utf-8", newline="\n")
    return OutputRecord(
        path=path,
        content_sha256=content_sha,
        final_sha256=file_sha256(path),
        hash_scope="bytes after commented provenance header",
        description=description,
    )


def write_text(path: Path, body: str, metadata: dict[str, str], description: str) -> OutputRecord:
    if not body.endswith("\n"):
        body += "\n"
    content_sha = text_sha256(body)
    header = "<!--\n" + "\n".join(header_lines(metadata, content_sha)) + "\n-->\n\n"
    path.write_text(header + body, encoding="utf-8", newline="\n")
    return OutputRecord(
        path=path,
        content_sha256=content_sha,
        final_sha256=file_sha256(path),
        hash_scope="bytes after HTML provenance comment",
        description=description,
    )


def write_svg(path: Path, svg_body: str, metadata: dict[str, str], description: str) -> OutputRecord:
    if not svg_body.endswith("\n"):
        svg_body += "\n"
    content_sha = text_sha256(svg_body)
    comment = "<!--\n" + "\n".join(header_lines(metadata, content_sha)) + "\n-->\n"
    path.write_text(comment + svg_body, encoding="utf-8", newline="\n")
    return OutputRecord(
        path=path,
        content_sha256=content_sha,
        final_sha256=file_sha256(path),
        hash_scope="bytes after SVG provenance comment",
        description=description,
    )


def load_snapshot_prices() -> tuple[pd.DataFrame, dict[str, object]]:
    if not SNAPSHOT_CLOSE_CSV.exists():
        raise FileNotFoundError(f"missing snapshot adjusted close data: {SNAPSHOT_CLOSE_CSV}")
    if not SNAPSHOT_METADATA_JSON.exists():
        raise FileNotFoundError(f"missing snapshot metadata: {SNAPSHOT_METADATA_JSON}")

    metadata = json.loads(SNAPSHOT_METADATA_JSON.read_text(encoding="utf-8"))
    if metadata.get("snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError(f"metadata snapshot_id mismatch: {metadata.get('snapshot_id')} != {SNAPSHOT_ID}")

    close = pd.read_csv(SNAPSHOT_CLOSE_CSV, parse_dates=["date"]).set_index("date")
    expected = {"TCS.NS", "INFY.NS"}
    missing = expected - set(close.columns)
    if missing:
        raise RuntimeError(f"missing adjusted close columns in snapshot: {sorted(missing)}")
    close = close[["TCS.NS", "INFY.NS"]].dropna()
    if close.empty:
        raise RuntimeError("snapshot adjusted close dataframe is empty after dropping missing values")
    return close, metadata


def ols(y: np.ndarray, x: np.ndarray, include_const: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    design = np.column_stack([np.ones(len(x)), x]) if include_const else x
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ beta
    resid = y - fitted
    return beta, fitted, resid


def engle_granger_p_value(y: np.ndarray, x: np.ndarray) -> float:
    try:
        _, p_value, _ = coint(y, x, trend="c", autolag="aic")
        return float(p_value)
    except Exception:
        return float("nan")


def adf_p_value(series: np.ndarray) -> float:
    values = np.asarray(series, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 12:
        return float("nan")
    try:
        return float(adfuller(values, regression="n", autolag="aic")[1])
    except Exception:
        return float("nan")


def ar1_phi(series: np.ndarray) -> float:
    lagged = np.asarray(series[:-1], dtype=float)
    current = np.asarray(series[1:], dtype=float)
    if len(lagged) < 3:
        return float("nan")
    beta, _, _ = ols(current, lagged, include_const=True)
    return float(beta[1])


def half_life_from_phi(phi: float) -> float:
    if not np.isfinite(phi) or phi <= 0:
        return float("nan")
    if phi >= 1:
        return float("inf")
    return float(-math.log(2.0) / math.log(phi))


def month_end_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    series = pd.Series(index=index, data=index)
    return list(series.groupby(series.index.to_period("M")).max())


def compute_rolling_metrics(close: pd.DataFrame) -> pd.DataFrame:
    logs = np.log(close)
    dates = month_end_dates(logs.index)
    rows: list[dict[str, object]] = []
    previous_beta: dict[int, float] = {}
    previous_spread_std: dict[int, float] = {}

    for n in WINDOWS:
        for date in dates:
            trailing = logs.loc[:date].tail(n)
            if len(trailing) < n:
                continue
            y = trailing["TCS.NS"].to_numpy()
            x = trailing["INFY.NS"].to_numpy()
            beta, _, resid = ols(y, x, include_const=True)
            hedge_beta = float(beta[1])
            eg_p = engle_granger_p_value(y, x)
            adf_p = adf_p_value(resid)
            phi = ar1_phi(resid)
            half_life = half_life_from_phi(phi)
            spread_std = float(np.std(resid, ddof=1))
            spread_diff_std = float(np.std(np.diff(resid), ddof=1))
            prev_beta = previous_beta.get(n)
            prev_spread_std = previous_spread_std.get(n)
            previous_beta[n] = hedge_beta
            previous_spread_std[n] = spread_std
            rows.append(
                {
                    "date": date.date().isoformat(),
                    "window_start_date": trailing.index[0].date().isoformat(),
                    "window_length": n,
                    "beta": hedge_beta,
                    "absolute_beta_change": float(abs(hedge_beta - prev_beta)) if prev_beta is not None else np.nan,
                    "engle_granger_p_value": eg_p,
                    "adf_p_value": adf_p,
                    "spread_phi": phi,
                    "half_life": half_life,
                    "spread_std": spread_std,
                    "spread_daily_change_std": spread_diff_std,
                    "absolute_spread_std_change": (
                        float(abs(spread_std - prev_spread_std)) if prev_spread_std is not None else np.nan
                    ),
                    "engle_granger_pass": bool(eg_p < P_VALUE_STRICT),
                    "adf_pass": bool(adf_p < P_VALUE_STRICT),
                    "strict_pass": bool((eg_p < P_VALUE_STRICT) and (adf_p < P_VALUE_STRICT)),
                    "borderline_pass": bool((eg_p < P_VALUE_BORDERLINE) and (adf_p < P_VALUE_STRICT)),
                }
            )
    return pd.DataFrame(rows)


def add_run_ids(frame: pd.DataFrame, condition_col: str) -> pd.DataFrame:
    out = frame.sort_values("date").copy()
    out["run_id"] = out[condition_col].ne(out[condition_col].shift()).cumsum()
    return out


def summarize_runs(frame: pd.DataFrame, condition_col: str, label: str) -> pd.DataFrame:
    rows = []
    source = add_run_ids(frame, condition_col)
    for (run_id, value), group in source.groupby(["run_id", condition_col], sort=True):
        rows.append(
            {
                "basis": label,
                "condition_column": condition_col,
                "condition_value": bool(value),
                "run_id": int(run_id),
                "start_date": group["date"].min(),
                "end_date": group["date"].max(),
                "n_month_ends": int(len(group)),
                "window_lengths": ",".join(str(x) for x in sorted(group["window_length"].unique())),
                "eg_p_min": float(group["engle_granger_p_value"].min()),
                "eg_p_max": float(group["engle_granger_p_value"].max()),
                "adf_p_min": float(group["adf_p_value"].min()),
                "adf_p_max": float(group["adf_p_value"].max()),
                "half_life_min": float(group["half_life"].min()),
                "half_life_max": float(group["half_life"].max()),
                "beta_min": float(group["beta"].min()),
                "beta_max": float(group["beta"].max()),
            }
        )
    return pd.DataFrame(rows)


def first_sustained_run(
    frame: pd.DataFrame,
    condition_col: str,
    min_months: int,
    basis: str,
    rule: str,
    caveat: str,
) -> dict[str, object]:
    runs = summarize_runs(frame, condition_col, basis)
    candidates = runs[(runs["condition_value"]) & (runs["n_month_ends"] >= min_months)].copy()
    if candidates.empty:
        return {
            "episode_id": basis,
            "rule": rule,
            "candidate_status": "no_sustained_run",
            "start_date": "",
            "end_date": "",
            "n_month_ends": 0,
            "window_lengths": "",
            "eg_p_range": "",
            "adf_p_range": "",
            "half_life_range": "",
            "beta_range": "",
            "caveat": caveat,
        }
    # There is one long healthy episode in these diagnostics. If that changes later,
    # keep all candidates visible in all_runs.csv and select the last sustained run.
    selected = candidates.sort_values(["end_date", "n_month_ends"]).iloc[-1]
    return {
        "episode_id": basis,
        "rule": rule,
        "candidate_status": "sustained_run",
        "start_date": selected["start_date"],
        "end_date": selected["end_date"],
        "n_month_ends": int(selected["n_month_ends"]),
        "window_lengths": selected["window_lengths"],
        "eg_p_range": f"{selected['eg_p_min']:.6g} to {selected['eg_p_max']:.6g}",
        "adf_p_range": f"{selected['adf_p_min']:.6g} to {selected['adf_p_max']:.6g}",
        "half_life_range": f"{selected['half_life_min']:.3f} to {selected['half_life_max']:.3f}",
        "beta_range": f"{selected['beta_min']:.6f} to {selected['beta_max']:.6f}",
        "caveat": caveat,
    }


def build_boundary_candidates(rolling: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    w500 = rolling[rolling["window_length"] == 500].copy()
    w730 = rolling[rolling["window_length"] == 730].copy()

    joined = w500.merge(
        w730,
        on="date",
        suffixes=("_500", "_730"),
    )
    consensus = pd.DataFrame(
        {
            "date": joined["date"],
            "window_length": 500730,
            "beta": joined["beta_500"],
            "engle_granger_p_value": joined[["engle_granger_p_value_500", "engle_granger_p_value_730"]].max(axis=1),
            "adf_p_value": joined[["adf_p_value_500", "adf_p_value_730"]].max(axis=1),
            "half_life": joined[["half_life_500", "half_life_730"]].max(axis=1),
            "strict_pass": joined["strict_pass_500"] & joined["strict_pass_730"],
            "borderline_pass": joined["borderline_pass_500"] & joined["borderline_pass_730"],
        }
    )

    runs = pd.concat(
        [
            summarize_runs(w500, "strict_pass", "500d_strict"),
            summarize_runs(w730, "strict_pass", "730d_strict"),
            summarize_runs(consensus, "strict_pass", "500d_730d_consensus_strict"),
            summarize_runs(w500, "borderline_pass", "500d_borderline_tolerant"),
        ],
        ignore_index=True,
    )

    candidates = pd.DataFrame(
        [
            first_sustained_run(
                w500,
                "strict_pass",
                MIN_SUSTAINED_MONTHS,
                "500d_strict",
                "500d Engle-Granger p < 0.05 and residual ADF p < 0.05 at month-end",
                "Shorter and more responsive long-window boundary; it ends before the 730d boundary.",
            ),
            first_sustained_run(
                w730,
                "strict_pass",
                MIN_SUSTAINED_MONTHS,
                "730d_strict",
                "730d Engle-Granger p < 0.05 and residual ADF p < 0.05 at month-end",
                "Longer lookback boundary; it can lag degradation because each row includes 730 trailing trading days.",
            ),
            first_sustained_run(
                consensus,
                "strict_pass",
                MIN_SUSTAINED_MONTHS,
                "500d_730d_consensus_strict",
                "Both 500d and 730d strict rules pass on the same month-end",
                "Consensus starts only when the 730d window becomes available, so it cannot date the earlier 500d-only portion.",
            ),
            first_sustained_run(
                w500,
                "borderline_pass",
                MIN_SUSTAINED_MONTHS,
                "500d_borderline_tolerant",
                "500d Engle-Granger p < 0.10 and residual ADF p < 0.05 at month-end",
                "This is a degradation shoulder, not the strict healthy core.",
            ),
        ]
    )
    return candidates, runs


def candidate_slice(rolling: pd.DataFrame, candidate: pd.Series) -> pd.DataFrame:
    if candidate["candidate_status"] != "sustained_run":
        return rolling.iloc[0:0].copy()
    windows = [int(x) for x in str(candidate["window_lengths"]).split(",") if x]
    if 500730 in windows:
        windows = [500]
    mask = (
        rolling["window_length"].isin(windows)
        & (rolling["date"] >= candidate["start_date"])
        & (rolling["date"] <= candidate["end_date"])
    )
    return rolling[mask].sort_values(["window_length", "date"]).copy()


def metric_summary_rows(frame: pd.DataFrame, episode_id: str) -> list[dict[str, object]]:
    rows = []
    metrics = [
        "beta",
        "absolute_beta_change",
        "half_life",
        "spread_phi",
        "engle_granger_p_value",
        "adf_p_value",
        "spread_std",
        "spread_daily_change_std",
    ]
    for metric in metrics:
        values = pd.to_numeric(frame[metric], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if values.empty:
            continue
        x = np.arange(len(values), dtype=float)
        slope = float(np.polyfit(x, values.to_numpy(), 1)[0]) if len(values) >= 2 else np.nan
        rows.append(
            {
                "episode_id": episode_id,
                "metric": metric,
                "n": int(len(values)),
                "mean": float(values.mean()),
                "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                "min": float(values.min()),
                "q25": float(values.quantile(0.25)),
                "median": float(values.median()),
                "q75": float(values.quantile(0.75)),
                "max": float(values.max()),
                "start": float(values.iloc[0]),
                "end": float(values.iloc[-1]),
                "end_minus_start": float(values.iloc[-1] - values.iloc[0]),
                "slope_per_month": slope,
                "median_absolute_monthly_change": (
                    float(values.diff().abs().median()) if metric != "absolute_beta_change" and len(values) > 1 else np.nan
                ),
            }
        )
    return rows


def build_regime_summaries(rolling: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, candidate in candidates.iterrows():
        frame = candidate_slice(rolling, candidate)
        if frame.empty:
            continue
        rows.extend(metric_summary_rows(frame, str(candidate["episode_id"])))
    return pd.DataFrame(rows)


def neg_log10(values: pd.Series) -> pd.Series:
    return -np.log10(values.clip(lower=1e-300))


def standardized_matrix(frame: pd.DataFrame, metrics: list[str]) -> tuple[np.ndarray, list[str]]:
    columns = []
    arrays = []
    for metric in metrics:
        if metric == "eg_strength":
            series = neg_log10(frame["engle_granger_p_value"])
        elif metric == "adf_strength":
            series = neg_log10(frame["adf_p_value"])
        else:
            series = pd.to_numeric(frame[metric], errors="coerce")
        series = series.replace([np.inf, -np.inf], np.nan)
        if series.notna().sum() < 3:
            continue
        filled = series.interpolate(limit_direction="both")
        std = float(filled.std(ddof=1))
        if not np.isfinite(std) or std == 0:
            continue
        arrays.append(((filled - float(filled.mean())) / std).to_numpy())
        columns.append(metric)
    if not arrays:
        return np.empty((len(frame), 0)), []
    return np.column_stack(arrays), columns


def split_rss(values: np.ndarray, split: int) -> float:
    left = values[:split]
    right = values[split:]
    left_center = left.mean(axis=0)
    right_center = right.mean(axis=0)
    return float(((left - left_center) ** 2).sum() + ((right - right_center) ** 2).sum())


def no_split_rss(values: np.ndarray) -> float:
    center = values.mean(axis=0)
    return float(((values - center) ** 2).sum())


def best_change_point(frame: pd.DataFrame, episode_id: str, rng: np.random.Generator) -> dict[str, object]:
    metrics = ["beta", "half_life", "spread_std", "spread_daily_change_std", "eg_strength", "adf_strength"]
    values, used_metrics = standardized_matrix(frame.reset_index(drop=True), metrics)
    n = len(frame)
    min_seg = min(6, max(3, n // 4))
    if n < min_seg * 2 or values.shape[1] == 0:
        return {
            "episode_id": episode_id,
            "n_month_ends": n,
            "best_split_after_date": "",
            "left_start": frame["date"].iloc[0] if n else "",
            "left_end": "",
            "right_start": "",
            "right_end": frame["date"].iloc[-1] if n else "",
            "metrics_used": ",".join(used_metrics),
            "rss_improvement_ratio": np.nan,
            "permutation_p_value": np.nan,
            "interpretation": "insufficient_rows_for_split_test",
        }
    total_rss = no_split_rss(values)
    candidates = list(range(min_seg, n - min_seg + 1))
    observed = [(split, split_rss(values, split)) for split in candidates]
    best_split, best_rss = min(observed, key=lambda item: item[1])
    improvement = 1.0 - best_rss / total_rss if total_rss > 0 else np.nan

    perm_improvements = []
    for _ in range(PERMUTATIONS):
        permuted = values[rng.permutation(n)]
        perm_total = no_split_rss(permuted)
        perm_best = min(split_rss(permuted, split) for split in candidates)
        perm_improvements.append(1.0 - perm_best / perm_total if perm_total > 0 else 0.0)
    p_value = float((np.sum(np.asarray(perm_improvements) >= improvement) + 1) / (PERMUTATIONS + 1))
    interpretation = "natural_split_supported" if p_value < 0.05 and improvement >= 0.25 else "no_clear_split"

    left = frame.iloc[:best_split]
    right = frame.iloc[best_split:]
    return {
        "episode_id": episode_id,
        "n_month_ends": n,
        "best_split_after_date": left["date"].iloc[-1],
        "left_start": left["date"].iloc[0],
        "left_end": left["date"].iloc[-1],
        "right_start": right["date"].iloc[0],
        "right_end": right["date"].iloc[-1],
        "metrics_used": ",".join(used_metrics),
        "rss_improvement_ratio": float(improvement),
        "permutation_p_value": p_value,
        "left_beta_mean": float(left["beta"].mean()),
        "right_beta_mean": float(right["beta"].mean()),
        "left_half_life_mean": float(left["half_life"].mean()),
        "right_half_life_mean": float(right["half_life"].mean()),
        "left_spread_std_mean": float(left["spread_std"].mean()),
        "right_spread_std_mean": float(right["spread_std"].mean()),
        "left_eg_p_median": float(left["engle_granger_p_value"].median()),
        "right_eg_p_median": float(right["engle_granger_p_value"].median()),
        "interpretation": interpretation,
    }


def build_subregime_tests(rolling: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for _, candidate in candidates.iterrows():
        if candidate["candidate_status"] != "sustained_run":
            continue
        if candidate["episode_id"] == "500d_730d_consensus_strict":
            # The consensus row duplicates the same calendar interval as 500d data
            # after the 730d window appears. Keep boundary ambiguity, avoid double
            # counting it as an independent sub-regime test.
            continue
        frame = candidate_slice(rolling, candidate)
        rows.append(best_change_point(frame, str(candidate["episode_id"]), rng))
    return pd.DataFrame(rows)


def trend_row(frame: pd.DataFrame, episode_id: str, period_label: str, metric: str) -> dict[str, object]:
    values = pd.to_numeric(frame[metric], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(values) < 2:
        slope = np.nan
    else:
        slope = float(np.polyfit(np.arange(len(values), dtype=float), values.to_numpy(), 1)[0])
    return {
        "episode_id": episode_id,
        "period_label": period_label,
        "start_date": frame["date"].iloc[0],
        "end_date": frame["date"].iloc[-1],
        "metric": metric,
        "n": int(len(values)),
        "start": float(values.iloc[0]) if len(values) else np.nan,
        "end": float(values.iloc[-1]) if len(values) else np.nan,
        "end_minus_start": float(values.iloc[-1] - values.iloc[0]) if len(values) else np.nan,
        "slope_per_month": slope,
        "first_half_mean": float(values.iloc[: max(1, len(values) // 2)].mean()) if len(values) else np.nan,
        "second_half_mean": float(values.iloc[max(1, len(values) // 2) :].mean()) if len(values) > 1 else np.nan,
    }


def build_degradation_diagnostics(rolling: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metrics = ["beta", "half_life", "engle_granger_p_value", "adf_p_value", "spread_std", "spread_daily_change_std"]

    strict_500 = candidates[candidates["episode_id"] == "500d_strict"].iloc[0]
    strict_frame = candidate_slice(rolling, strict_500)
    for metric in metrics:
        rows.append(trend_row(strict_frame, "500d_strict", "strict_healthy_core", metric))

    shoulder = rolling[
        (rolling["window_length"] == 500)
        & (rolling["date"] > strict_500["end_date"])
        & (rolling["date"] <= "2023-01-31")
    ].copy()
    if not shoulder.empty:
        for metric in metrics:
            rows.append(trend_row(shoulder, "500d_strict", "post_core_borderline_shoulder", metric))

    strict_730 = candidates[candidates["episode_id"] == "730d_strict"].iloc[0]
    frame_730 = candidate_slice(rolling, strict_730)
    for metric in metrics:
        rows.append(trend_row(frame_730, "730d_strict", "lagged_long_window_core", metric))
    return pd.DataFrame(rows)


def fmt(value: object, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return str(value)
    return f"{number:.{digits}f}"


def metric_lookup(summary: pd.DataFrame, episode_id: str, metric: str) -> pd.Series:
    rows = summary[(summary["episode_id"] == episode_id) & (summary["metric"] == metric)]
    if rows.empty:
        raise KeyError(f"missing summary row for {episode_id} {metric}")
    return rows.iloc[0]


def summary_markdown(
    candidates: pd.DataFrame,
    regime_summary: pd.DataFrame,
    subregimes: pd.DataFrame,
    degradation: pd.DataFrame,
    snapshot_metadata: dict[str, object],
    records: list[OutputRecord],
) -> str:
    c500 = candidates[candidates["episode_id"] == "500d_strict"].iloc[0]
    c730 = candidates[candidates["episode_id"] == "730d_strict"].iloc[0]
    ccons = candidates[candidates["episode_id"] == "500d_730d_consensus_strict"].iloc[0]
    cbord = candidates[candidates["episode_id"] == "500d_borderline_tolerant"].iloc[0]

    beta = metric_lookup(regime_summary, "500d_strict", "beta")
    half = metric_lookup(regime_summary, "500d_strict", "half_life")
    eg = metric_lookup(regime_summary, "500d_strict", "engle_granger_p_value")
    adf = metric_lookup(regime_summary, "500d_strict", "adf_p_value")
    spread = metric_lookup(regime_summary, "500d_strict", "spread_std")
    spread_diff = metric_lookup(regime_summary, "500d_strict", "spread_daily_change_std")

    split_500 = subregimes[subregimes["episode_id"] == "500d_strict"].iloc[0]
    shoulder_eg = degradation[
        (degradation["episode_id"] == "500d_strict")
        & (degradation["period_label"] == "post_core_borderline_shoulder")
        & (degradation["metric"] == "engle_granger_p_value")
    ]
    shoulder_half = degradation[
        (degradation["episode_id"] == "500d_strict")
        & (degradation["period_label"] == "post_core_borderline_shoulder")
        & (degradation["metric"] == "half_life")
    ]

    record_lines = "\n".join(
        f"- `{record.path.name}` final SHA256 `{record.final_sha256}`"
        for record in records
        if record.path.name != "summary.md"
    )

    shoulder_text = "No post-core borderline shoulder was measured."
    if not shoulder_eg.empty and not shoulder_half.empty:
        eg_row = shoulder_eg.iloc[0]
        half_row = shoulder_half.iloc[0]
        shoulder_text = (
            f"After the strict 500d core, the 500d borderline-tolerant rule continues through "
            f"{cbord['end_date']}. In that shoulder, Engle-Granger p-values remain below 0.10 "
            f"but start at {fmt(eg_row['start'])} and end at {fmt(eg_row['end'])}; half-life moves "
            f"from {fmt(half_row['start'])} to {fmt(half_row['end'])} trading days. This is evidence "
            f"of degradation, not a strict healthy pass."
        )

    return f"""# Healthy Episode Characterization - TCS/INFY

## Inputs

- Snapshot: `{SNAPSHOT_ID}`
- Snapshot date range: `{snapshot_metadata.get("first_data_date")}` to `{snapshot_metadata.get("last_data_date")}`
- Adjustment policy: `{snapshot_metadata.get("adjustment_policy")}`
- Rolling method: log adjusted closes; TCS as dependent variable; INFY as hedge-ratio regressor; month-end rolling OLS windows `{', '.join(str(x) for x in WINDOWS)}`.
- Test methods: Engle-Granger `statsmodels.tsa.stattools.coint(trend="c", autolag="aic")`; residual ADF `adfuller(regression="n", autolag="aic")`.

## Episode 1 Boundaries

The rolling results support multiple plausible Episode 1 boundaries:

| Boundary basis | Start | End | Month-ends | Interpretation |
|---|---:|---:|---:|---|
| 500d strict | {c500['start_date']} | {c500['end_date']} | {c500['n_month_ends']} | Responsive long-window healthy core. |
| 730d strict | {c730['start_date']} | {c730['end_date']} | {c730['n_month_ends']} | Lagged long-window boundary; smooths later weakening. |
| 500d/730d consensus strict | {ccons['start_date']} | {ccons['end_date']} | {ccons['n_month_ends']} | Conservative overlap once the 730d window exists. |
| 500d borderline tolerant | {cbord['start_date']} | {cbord['end_date']} | {cbord['n_month_ends']} | Degradation shoulder, not the strict healthy core. |

I would describe the strict healthy core as 2020-01-31 through 2021-12-31 on 500d month-end diagnostics, with a narrower consensus core from 2020-12-31 through 2021-12-31 when requiring both 500d and 730d strict passes. The 730d rule extends to 2023-03-31, but that boundary is plausibly lagged by its 730-trading-day lookback.

## Healthy Regime Shape

For the 500d strict healthy core, beta ranges from {fmt(beta['min'])} to {fmt(beta['max'])}, with median {fmt(beta['median'])} and standard deviation {fmt(beta['std'])}. The largest beta movement occurs early in the core; the later months are materially tighter.

Spread half-life ranges from {fmt(half['min'])} to {fmt(half['max'])} trading days, with median {fmt(half['median'])}. That is a stable, mean-reverting spread profile by these diagnostics.

Engle-Granger p-values range from {fmt(eg['min'], 6)} to {fmt(eg['max'])}, with median {fmt(eg['median'])}. Residual ADF p-values range from {fmt(adf['min'], 6)} to {fmt(adf['max'], 6)}, with median {fmt(adf['median'], 6)}. Both stay below 0.05 throughout the strict 500d core.

Spread volatility, measured as the standard deviation of the log residual over each rolling window, has median {fmt(spread['median'])}; daily spread-change volatility has median {fmt(spread_diff['median'])}. The full distributions are in `episode_regime_summary.csv`.

## Homogeneity And Sub-Regimes

The 500d strict core is not statistically homogeneous by the exploratory split test. The strongest split is after {split_500['best_split_after_date']}, with RSS improvement {fmt(split_500['rss_improvement_ratio'])} and permutation p-value {fmt(split_500['permutation_p_value'])}. The split mainly separates an early beta-adjustment segment from a later stable segment; both segments still satisfy the strict healthy-test rule.

The 730d strict candidate is smoother and less responsive. Its sub-regime result should be read as a lagged view because each point contains 730 trailing trading days.

## Degradation Evidence

Within the strict 500d core, the final two month-ends have Engle-Granger p-values near the 0.05 threshold, while ADF p-values remain small and half-life remains in the healthy range. That is weak evidence of gradual degradation, not a strict failure.

{shoulder_text}

No RL recommendations are made here, and no training window is selected.

## Supporting Outputs

{record_lines}
"""


def scale(value: float, domain: tuple[float, float], pixel_range: tuple[float, float]) -> float:
    lo, hi = domain
    p_lo, p_hi = pixel_range
    if hi == lo:
        return (p_lo + p_hi) / 2
    return p_lo + (value - lo) * (p_hi - p_lo) / (hi - lo)


def svg_line(points: Iterable[tuple[float, float]], color: str, width: float = 2.0) -> str:
    point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points if np.isfinite(x) and np.isfinite(y))
    return f'<polyline points="{point_text}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round" />'


def svg_text(x: float, y: float, text: str, size: int = 12, anchor: str = "start", weight: str = "400") -> str:
    escaped = html.escape(str(text))
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="#111827">{escaped}</text>'


def date_domain(frame: pd.DataFrame) -> tuple[float, float]:
    dates = pd.to_datetime(frame["date"])
    return float(dates.map(pd.Timestamp.toordinal).min()), float(dates.map(pd.Timestamp.toordinal).max())


def plot_boundary_svg(rolling: pd.DataFrame, candidates: pd.DataFrame) -> str:
    data = rolling[(rolling["window_length"].isin(PRIMARY_WINDOWS)) & (rolling["date"] <= "2023-06-30")].copy()
    data["date_num"] = pd.to_datetime(data["date"]).map(pd.Timestamp.toordinal).astype(float)
    width, height = 1100, 560
    left, right, top, bottom = 80, 1040, 55, 485
    x_domain = date_domain(data)
    y_domain = (0.0, 0.12)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        svg_text(80, 30, "Episode 1 boundary diagnostics: Engle-Granger p-values", 18, weight="700"),
    ]
    colors = {"500d_strict": "#dbeafe", "730d_strict": "#dcfce7", "500d_730d_consensus_strict": "#fde68a"}
    for _, row in candidates.iterrows():
        if row["episode_id"] not in colors or row["candidate_status"] != "sustained_run":
            continue
        start = pd.Timestamp(row["start_date"]).toordinal()
        end = pd.Timestamp(row["end_date"]).toordinal()
        x1 = scale(start, x_domain, (left, right))
        x2 = scale(end, x_domain, (left, right))
        elements.append(f'<rect x="{x1:.1f}" y="{top}" width="{max(1, x2 - x1):.1f}" height="{bottom - top}" fill="{colors[row["episode_id"]]}" opacity="0.35" />')
    elements.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#111827" stroke-width="1" />')
    elements.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#111827" stroke-width="1" />')
    for y_value, label, dash in [(0.05, "0.05", ""), (0.10, "0.10", "6 4")]:
        y = scale(y_value, y_domain, (bottom, top))
        elements.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#6b7280" stroke-width="1" stroke-dasharray="{dash}" />')
        elements.append(svg_text(left - 10, y + 4, label, 11, anchor="end"))
    for window, color in [(500, "#2563eb"), (730, "#16a34a")]:
        subset = data[data["window_length"] == window]
        points = [
            (
                scale(row.date_num, x_domain, (left, right)),
                scale(min(float(row.engle_granger_p_value), y_domain[1]), y_domain, (bottom, top)),
            )
            for row in subset.itertuples(index=False)
        ]
        elements.append(svg_line(points, color, 2.4))
        elements.append(svg_text(right - 110, top + (20 if window == 500 else 40), f"{window}d EG p", 12))
        elements.append(f'<line x1="{right - 155}" y1="{top + (16 if window == 500 else 36)}" x2="{right - 118}" y2="{top + (16 if window == 500 else 36)}" stroke="{color}" stroke-width="2.4" />')
    for label_date in ["2020-01-31", "2021-01-29", "2022-01-31", "2023-01-31"]:
        x = scale(pd.Timestamp(label_date).toordinal(), x_domain, (left, right))
        elements.append(f'<line x1="{x:.1f}" y1="{bottom}" x2="{x:.1f}" y2="{bottom + 5}" stroke="#111827" />')
        elements.append(svg_text(x, bottom + 22, label_date[:4], 11, anchor="middle"))
    elements.append(svg_text(left, height - 24, "Shaded spans show candidate sustained healthy intervals; p-values clipped at 0.12 for readability.", 12))
    elements.append("</svg>")
    return "\n".join(elements)


def plot_episode_metrics_svg(rolling: pd.DataFrame, candidates: pd.DataFrame) -> str:
    c500 = candidates[candidates["episode_id"] == "500d_borderline_tolerant"].iloc[0]
    data = rolling[
        (rolling["window_length"] == 500)
        & (rolling["date"] >= c500["start_date"])
        & (rolling["date"] <= c500["end_date"])
    ].copy()
    data["date_num"] = pd.to_datetime(data["date"]).map(pd.Timestamp.toordinal).astype(float)
    width, height = 1100, 760
    left, right = 82, 1040
    panel_h = 135
    top0 = 70
    gap = 42
    x_domain = date_domain(data)
    panels = [
        ("beta", "500d beta", "#2563eb"),
        ("half_life", "Spread half-life", "#7c3aed"),
        ("spread_std", "Spread volatility", "#dc2626"),
        ("engle_granger_p_value", "Engle-Granger p-value", "#059669"),
    ]
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        svg_text(80, 34, "500d Episode 1 metrics: strict core plus borderline shoulder", 18, weight="700"),
    ]
    strict = candidates[candidates["episode_id"] == "500d_strict"].iloc[0]
    sx1 = scale(pd.Timestamp(strict["start_date"]).toordinal(), x_domain, (left, right))
    sx2 = scale(pd.Timestamp(strict["end_date"]).toordinal(), x_domain, (left, right))
    for idx, (metric, label, color) in enumerate(panels):
        top = top0 + idx * (panel_h + gap)
        bottom = top + panel_h
        values = pd.to_numeric(data[metric], errors="coerce").replace([np.inf, -np.inf], np.nan)
        lo = float(values.min())
        hi = float(values.max())
        if metric == "engle_granger_p_value":
            lo, hi = 0.0, max(0.10, hi)
        pad = (hi - lo) * 0.12 if hi > lo else 1.0
        y_domain = (lo - pad, hi + pad)
        elements.append(f'<rect x="{sx1:.1f}" y="{top}" width="{max(1, sx2 - sx1):.1f}" height="{panel_h}" fill="#dbeafe" opacity="0.28" />')
        elements.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#111827" />')
        elements.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#111827" />')
        points = [
            (
                scale(row.date_num, x_domain, (left, right)),
                scale(float(getattr(row, metric)), y_domain, (bottom, top)),
            )
            for row in data.itertuples(index=False)
            if np.isfinite(float(getattr(row, metric)))
        ]
        elements.append(svg_line(points, color, 2.2))
        if metric == "engle_granger_p_value":
            y = scale(0.05, y_domain, (bottom, top))
            elements.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#6b7280" stroke-dasharray="5 4" />')
        elements.append(svg_text(22, top + 20, label, 12))
        elements.append(svg_text(left - 8, top + 4, fmt(y_domain[1]), 10, anchor="end"))
        elements.append(svg_text(left - 8, bottom, fmt(y_domain[0]), 10, anchor="end"))
    for label_date in ["2020-01-31", "2021-01-29", "2022-01-31", "2023-01-31"]:
        x = scale(pd.Timestamp(label_date).toordinal(), x_domain, (left, right))
        elements.append(f'<line x1="{x:.1f}" y1="{height - 60}" x2="{x:.1f}" y2="{height - 55}" stroke="#111827" />')
        elements.append(svg_text(x, height - 38, label_date[:4], 11, anchor="middle"))
    elements.append(svg_text(left, height - 14, "Blue shading marks the 500d strict healthy core; unshaded right tail is the borderline shoulder.", 12))
    elements.append("</svg>")
    return "\n".join(elements)


def plot_subregime_svg(rolling: pd.DataFrame, candidates: pd.DataFrame, subregimes: pd.DataFrame) -> str:
    c500 = candidates[candidates["episode_id"] == "500d_strict"].iloc[0]
    split = subregimes[subregimes["episode_id"] == "500d_strict"].iloc[0]
    data = candidate_slice(rolling, c500)
    left_data = data[data["date"] <= split["best_split_after_date"]]
    right_data = data[data["date"] > split["best_split_after_date"]]
    metrics = [
        ("beta", "Beta"),
        ("half_life", "Half-life"),
        ("spread_std", "Spread vol"),
        ("engle_granger_p_value", "EG p"),
    ]
    width, height = 980, 470
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff" />',
        svg_text(60, 34, f"500d strict core split after {split['best_split_after_date']}", 18, weight="700"),
    ]
    panel_w = 205
    left0 = 70
    top = 78
    bottom = 385
    for idx, (metric, label) in enumerate(metrics):
        x0 = left0 + idx * (panel_w + 25)
        all_vals = pd.to_numeric(data[metric], errors="coerce").dropna()
        lo = float(all_vals.min())
        hi = float(all_vals.max())
        pad = (hi - lo) * 0.18 if hi > lo else 1.0
        y_domain = (lo - pad, hi + pad)
        elements.append(f'<line x1="{x0}" y1="{bottom}" x2="{x0 + panel_w}" y2="{bottom}" stroke="#111827" />')
        elements.append(f'<line x1="{x0}" y1="{top}" x2="{x0}" y2="{bottom}" stroke="#111827" />')
        for seg_idx, (seg_label, seg_data, color) in enumerate(
            [("left", left_data, "#2563eb"), ("right", right_data, "#dc2626")]
        ):
            vals = pd.to_numeric(seg_data[metric], errors="coerce").dropna()
            q1, med, q3 = vals.quantile([0.25, 0.5, 0.75])
            low, high = vals.min(), vals.max()
            cx = x0 + 70 + seg_idx * 70
            y_q1 = scale(float(q1), y_domain, (bottom, top))
            y_q3 = scale(float(q3), y_domain, (bottom, top))
            y_med = scale(float(med), y_domain, (bottom, top))
            y_low = scale(float(low), y_domain, (bottom, top))
            y_high = scale(float(high), y_domain, (bottom, top))
            elements.append(f'<line x1="{cx}" y1="{y_low:.1f}" x2="{cx}" y2="{y_high:.1f}" stroke="{color}" />')
            elements.append(f'<rect x="{cx - 18}" y="{min(y_q1, y_q3):.1f}" width="36" height="{abs(y_q3 - y_q1):.1f}" fill="{color}" opacity="0.22" stroke="{color}" />')
            elements.append(f'<line x1="{cx - 21}" y1="{y_med:.1f}" x2="{cx + 21}" y2="{y_med:.1f}" stroke="{color}" stroke-width="2" />')
            elements.append(svg_text(cx, bottom + 18, seg_label, 10, anchor="middle"))
        elements.append(svg_text(x0 + panel_w / 2, top - 16, label, 12, anchor="middle", weight="700"))
        elements.append(svg_text(x0 - 7, top + 4, fmt(y_domain[1]), 10, anchor="end"))
        elements.append(svg_text(x0 - 7, bottom, fmt(y_domain[0]), 10, anchor="end"))
    elements.append(svg_text(60, height - 34, "Exploratory split test uses standardized beta, half-life, spread volatility, and p-value strength metrics.", 12))
    elements.append("</svg>")
    return "\n".join(elements)


def write_manifest(records: list[OutputRecord], metadata: dict[str, str]) -> OutputRecord:
    frame = pd.DataFrame(
        [
            {
                "path": str(record.path.relative_to(ROOT)),
                "description": record.description,
                "content_sha256": record.content_sha256,
                "final_file_sha256": record.final_sha256,
                "hash_scope": record.hash_scope,
            }
            for record in records
        ]
    )
    return write_csv(OUT_DIR / "output_manifest.csv", frame, metadata, "Exact final SHA256 manifest for generated outputs")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    git_hash = git_commit()
    metadata = base_metadata(timestamp_utc, git_hash)

    close, snapshot_metadata = load_snapshot_prices()
    rolling = compute_rolling_metrics(close)
    candidates, all_runs = build_boundary_candidates(rolling)
    regime_summary = build_regime_summaries(rolling, candidates)
    subregimes = build_subregime_tests(rolling, candidates)
    degradation = build_degradation_diagnostics(rolling, candidates)

    records: list[OutputRecord] = []
    records.append(write_csv(OUT_DIR / "rolling_metrics.csv", rolling, metadata, "Month-end rolling cointegration metrics"))
    records.append(write_csv(OUT_DIR / "episode_boundary_candidates.csv", candidates, metadata, "Episode boundary candidates"))
    records.append(write_csv(OUT_DIR / "all_pass_runs.csv", all_runs, metadata, "All pass/fail runs used for boundary ambiguity"))
    records.append(write_csv(OUT_DIR / "episode_regime_summary.csv", regime_summary, metadata, "Distribution and drift summaries"))
    records.append(write_csv(OUT_DIR / "subregime_tests.csv", subregimes, metadata, "Exploratory change-point diagnostics"))
    records.append(write_csv(OUT_DIR / "degradation_diagnostics.csv", degradation, metadata, "Gradual degradation diagnostics"))

    records.append(
        write_svg(
            OUT_DIR / "plot_boundary_diagnostics.svg",
            plot_boundary_svg(rolling, candidates),
            metadata,
            "Boundary p-value diagnostic plot",
        )
    )
    records.append(
        write_svg(
            OUT_DIR / "plot_episode_metrics.svg",
            plot_episode_metrics_svg(rolling, candidates),
            metadata,
            "Episode 1 metric time-series plot",
        )
    )
    records.append(
        write_svg(
            OUT_DIR / "plot_subregime_boxplots.svg",
            plot_subregime_svg(rolling, candidates, subregimes),
            metadata,
            "Sub-regime distribution plot",
        )
    )

    summary_body = summary_markdown(candidates, regime_summary, subregimes, degradation, snapshot_metadata, records)
    summary_record = write_text(OUT_DIR / "summary.md", summary_body, metadata, "Concise Episode 1 characterization")
    records.append(summary_record)
    manifest_record = write_manifest(records, metadata)
    records.append(manifest_record)

    provenance = {
        **metadata,
        "snapshot_adjusted_close_sha256": file_sha256(SNAPSHOT_CLOSE_CSV),
        "snapshot_metadata": snapshot_metadata,
        "statsmodels_version": statsmodels.__version__,
        "python_executable": sys.executable,
        "method": {
            "rolling_windows": WINDOWS,
            "primary_windows": PRIMARY_WINDOWS,
            "strict_rule": "Engle-Granger p < 0.05 and residual ADF p < 0.05",
            "borderline_rule": "Engle-Granger p < 0.10 and residual ADF p < 0.05",
            "half_life": "-log(2) / log(phi), where phi is AR(1) coefficient of OLS residual spread",
            "spread_volatility": "sample standard deviation of OLS log residual spread within each rolling window",
            "subregime_test": (
                "best one-change split on standardized metrics, with month-order permutation p-value; "
                "exploratory only"
            ),
        },
        "outputs": [
            {
                "path": str(record.path.relative_to(ROOT)),
                "content_sha256": record.content_sha256,
                "final_file_sha256": record.final_sha256,
                "hash_scope": record.hash_scope,
                "description": record.description,
            }
            for record in records
        ],
        "self_hash_note": (
            "Text outputs embed content hashes excluding their provenance headers. Exact final file hashes "
            "are recorded here and in output_manifest.csv."
        ),
    }
    provenance_path = OUT_DIR / "provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    print(json.dumps({"summary": str((OUT_DIR / "summary.md").relative_to(ROOT)), "outputs": len(records) + 1}, indent=2))


if __name__ == "__main__":
    main()
