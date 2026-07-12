from __future__ import annotations

import hashlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


ROOT = Path(__file__).resolve().parents[4]
PHASE_DIR = ROOT / "phase_i_tcs_infy_pairs_trading"
OUT_DIR = Path(__file__).resolve().parent

CLAIM_ID = "wq_volume_signal_test_tier_b_codex_independent"
TIER = "B"
TCS_INFY_SNAPSHOT_ID = "tcs_infy_v2_2026-07-11"
BENCHMARK_SNAPSHOT_ID = "nifty_it_benchmark_v1_2026-07-11"
ROLLING_METRICS_SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"
DATA_FLOOR = pd.Timestamp("2018-09-06")
BONFERRONI_FAMILY_SIZE = 8
BONFERRONI_THRESHOLD = 0.05 / BONFERRONI_FAMILY_SIZE
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20260712

TCS_INFY_OHLCV = ROOT / "data" / "snapshots" / TCS_INFY_SNAPSHOT_ID / "ohlcv.csv"
TCS_INFY_METADATA = ROOT / "data" / "snapshots" / TCS_INFY_SNAPSHOT_ID / "metadata.json"
BENCHMARK_OHLCV = ROOT / "data" / "snapshots" / BENCHMARK_SNAPSHOT_ID / "ohlcv.csv"
BENCHMARK_METADATA = ROOT / "data" / "snapshots" / BENCHMARK_SNAPSHOT_ID / "metadata.json"
ROLLING_METRICS = (
    PHASE_DIR
    / "analysis"
    / "claim_002_healthy_episode_characterization"
    / "codex_tier_a"
    / "rolling_metrics.csv"
)

CORES = {
    "500d": {
        "window_length": 500,
        "core_start": pd.Timestamp("2020-01-31"),
        "core_end": pd.Timestamp("2021-12-31"),
        "breakdown_date": pd.Timestamp("2022-01-31"),
    },
    "730d": {
        "window_length": 730,
        "core_start": pd.Timestamp("2020-12-31"),
        "core_end": pd.Timestamp("2023-03-31"),
        "breakdown_date": pd.Timestamp("2023-04-28"),
    },
}
TICKERS = ["TCS.NS", "INFY.NS"]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def read_metadata(path: Path, expected_snapshot_id: str) -> dict[str, Any]:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    if metadata.get("snapshot_id") != expected_snapshot_id:
        raise RuntimeError(f"snapshot_id mismatch in {path}: {metadata.get('snapshot_id')}")
    return metadata


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    tcs_infy_metadata = read_metadata(TCS_INFY_METADATA, TCS_INFY_SNAPSHOT_ID)
    benchmark_metadata = read_metadata(BENCHMARK_METADATA, BENCHMARK_SNAPSHOT_ID)

    tcs_infy = pd.read_csv(TCS_INFY_OHLCV, parse_dates=["date"])
    expected_columns = {"date", "ticker", "open", "high", "low", "close", "volume"}
    if set(tcs_infy.columns) != expected_columns:
        raise RuntimeError(f"unexpected TCS/INFY columns: {list(tcs_infy.columns)}")

    benchmark = pd.read_csv(BENCHMARK_OHLCV, parse_dates=["date"])
    if set(benchmark.columns) != expected_columns:
        raise RuntimeError(f"unexpected benchmark columns: {list(benchmark.columns)}")
    benchmark = benchmark[benchmark["ticker"] == "^NSEI"].copy()
    if benchmark.empty:
        raise RuntimeError("no ^NSEI rows found in benchmark snapshot")

    rolling = pd.read_csv(ROLLING_METRICS, comment="#", parse_dates=["date"])
    required_rolling = {
        "date",
        "window_length",
        "beta",
        "half_life",
        "phi",
        "eg_p",
        "adf_p",
        "spread_std",
        "spread_daily_change_std",
        "strict_pass",
        "borderline_pass",
    }
    if not required_rolling.issubset(set(rolling.columns)):
        missing = sorted(required_rolling - set(rolling.columns))
        raise RuntimeError(f"rolling_metrics.csv missing columns: {missing}")

    return tcs_infy, benchmark, rolling, tcs_infy_metadata, benchmark_metadata


def event_window_dates(sample_dates: pd.Series, breakdown_date: pd.Timestamp) -> list[pd.Timestamp]:
    candidates = pd.Series(pd.to_datetime(sample_dates).sort_values().unique())
    pre_breakdown = candidates[candidates < breakdown_date]
    if len(pre_breakdown) < 20:
        raise RuntimeError(f"fewer than 20 pre-breakdown trading days before {breakdown_date.date()}")
    return list(pre_breakdown.tail(20))


def design_matrix(frame: pd.DataFrame, include_event_dummy: bool) -> pd.DataFrame:
    columns: dict[str, Any] = {"const": 1.0, "log_nsei_volume": frame["log_nsei_volume"].to_numpy(dtype=float)}
    dummies = pd.get_dummies(frame["day_of_week"], prefix="dow", drop_first=True, dtype=float)
    for column in dummies.columns:
        columns[column] = dummies[column].to_numpy(dtype=float)
    if include_event_dummy:
        columns["event_window_dummy"] = frame["event_window_dummy"].to_numpy(dtype=float)
    return pd.DataFrame(columns, index=frame.index)


def one_sided_positive_p_value(t_value: float, df_resid: float) -> float:
    if not math.isfinite(t_value):
        return float("nan")
    return float(stats.t.sf(t_value, df_resid))


def fit_volume_regression(
    tcs_infy: pd.DataFrame,
    benchmark: pd.DataFrame,
    ticker: str,
    core_id: str,
    include_event_dummy: bool,
) -> tuple[sm.regression.linear_model.RegressionResultsWrapper, pd.DataFrame, list[pd.Timestamp]]:
    ticker_frame = tcs_infy[(tcs_infy["ticker"] == ticker) & (tcs_infy["date"] >= DATA_FLOOR)].copy()
    ticker_frame = ticker_frame[["date", "volume"]].rename(columns={"volume": "ticker_volume"})
    nsei_frame = benchmark[["date", "volume"]].rename(columns={"volume": "nsei_volume"}).copy()
    merged = pd.merge(ticker_frame, nsei_frame, on="date", how="inner").sort_values("date").reset_index(drop=True)
    merged = merged[(merged["ticker_volume"] > 0) & (merged["nsei_volume"] > 0)].copy()
    if merged.empty:
        raise RuntimeError(f"empty estimation sample for {ticker} {core_id}")

    event_dates = event_window_dates(merged["date"], CORES[core_id]["breakdown_date"])
    merged["event_window_dummy"] = merged["date"].isin(event_dates).astype(int)
    merged["log_ticker_volume"] = np.log(merged["ticker_volume"].astype(float))
    merged["log_nsei_volume"] = np.log(merged["nsei_volume"].astype(float))
    merged["day_of_week"] = merged["date"].dt.dayofweek.astype(int)
    merged["ticker"] = ticker
    merged["core"] = core_id

    y = merged["log_ticker_volume"].to_numpy(dtype=float)
    x = design_matrix(merged, include_event_dummy=include_event_dummy)
    model = sm.OLS(y, x)
    result = model.fit(cov_type="HC3", use_t=True)
    return result, merged, event_dates


def confidence_interval(result: sm.regression.linear_model.RegressionResultsWrapper, term: str) -> tuple[float, float]:
    intervals = result.conf_int(alpha=0.05)
    if isinstance(intervals, pd.DataFrame):
        low, high = intervals.loc[term]
    else:
        index = list(result.params.index).index(term)
        low, high = intervals[index]
    return float(low), float(high)


def regression_rows(
    result: sm.regression.linear_model.RegressionResultsWrapper,
    ticker: str,
    core_id: str,
    model_type: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    coefficient_rows: list[dict[str, Any]] = []
    for term in result.params.index:
        ci_low, ci_high = confidence_interval(result, term)
        coefficient_rows.append(
            {
                "ticker": ticker,
                "core": core_id,
                "model_type": model_type,
                "term": term,
                "coefficient": float(result.params[term]),
                "hc3_standard_error": float(result.bse[term]),
                "t_stat": float(result.tvalues[term]),
                "p_value_two_sided_hc3_t": float(result.pvalues[term]),
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "n_obs": int(result.nobs),
                "r_squared": float(result.rsquared),
            }
        )

    model_row = {
        "ticker": ticker,
        "core": core_id,
        "model_type": model_type,
        "n_obs": int(result.nobs),
        "df_model": float(result.df_model),
        "df_resid": float(result.df_resid),
        "r_squared": float(result.rsquared),
        "adj_r_squared": float(result.rsquared_adj),
    }
    if "event_window_dummy" in result.params.index:
        model_row["event_gamma"] = float(result.params["event_window_dummy"])
        model_row["event_gamma_hc3_se"] = float(result.bse["event_window_dummy"])
        model_row["event_gamma_hc3_se_is_finite"] = bool(math.isfinite(float(result.bse["event_window_dummy"])))
        model_row["event_gamma_t_stat"] = float(result.tvalues["event_window_dummy"])
        model_row["event_gamma_p_value_two_sided_hc3_t"] = float(result.pvalues["event_window_dummy"])
        model_row["event_gamma_p_value_one_sided_positive_hc3_t"] = one_sided_positive_p_value(
            float(result.tvalues["event_window_dummy"]),
            float(result.df_resid),
        )
    return coefficient_rows, model_row


def fit_part_a(
    tcs_infy: pd.DataFrame,
    benchmark: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    coefficient_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    event_window_rows: list[dict[str, Any]] = []

    for ticker in TICKERS:
        for core_id in CORES:
            dummy_result, dummy_sample, event_dates = fit_volume_regression(
                tcs_infy,
                benchmark,
                ticker,
                core_id,
                include_event_dummy=True,
            )
            rows, model_row = regression_rows(dummy_result, ticker, core_id, "with_event_dummy")
            coefficient_rows.extend(rows)
            model_row["event_window_start"] = event_dates[0].strftime("%Y-%m-%d")
            model_row["event_window_end"] = event_dates[-1].strftime("%Y-%m-%d")
            model_row["event_window_trading_days"] = len(event_dates)
            model_rows.append(model_row)
            for date in event_dates:
                event_window_rows.append(
                    {
                        "ticker": ticker,
                        "core": core_id,
                        "breakdown_date": CORES[core_id]["breakdown_date"].strftime("%Y-%m-%d"),
                        "event_date": pd.Timestamp(date).strftime("%Y-%m-%d"),
                    }
                )

            nodummy_result, nodummy_sample, _ = fit_volume_regression(
                tcs_infy,
                benchmark,
                ticker,
                core_id,
                include_event_dummy=False,
            )
            rows, model_row = regression_rows(nodummy_result, ticker, core_id, "without_event_dummy")
            coefficient_rows.extend(rows)
            model_rows.append(model_row)

            residual_series = nodummy_result.resid
            for idx, residual in zip(nodummy_sample.index, residual_series):
                row = nodummy_sample.loc[idx]
                residual_rows.append(
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "core": core_id,
                        "residual": float(residual),
                        "log_ticker_volume": float(row["log_ticker_volume"]),
                        "log_nsei_volume": float(row["log_nsei_volume"]),
                        "day_of_week": int(row["day_of_week"]),
                    }
                )

    return (
        pd.DataFrame(coefficient_rows),
        pd.DataFrame(model_rows),
        pd.DataFrame(residual_rows),
        pd.DataFrame(event_window_rows),
    )


def logit(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    lower = np.nextafter(0.0, 1.0)
    upper = np.nextafter(1.0, 0.0)
    return np.log(numeric.clip(lower=lower, upper=upper) / (1.0 - numeric.clip(lower=lower, upper=upper)))


def prepare_monthly_series(
    residuals: pd.DataFrame,
    rolling: pd.DataFrame,
    ticker: str,
    core_id: str,
) -> pd.DataFrame:
    core = CORES[core_id]
    residual_subset = residuals[(residuals["ticker"] == ticker) & (residuals["core"] == core_id)].copy()
    residual_subset["date"] = pd.to_datetime(residual_subset["date"])
    residual_subset["month"] = residual_subset["date"].dt.to_period("M")
    monthly_resid = (
        residual_subset.groupby("month", as_index=False)
        .agg(date=("date", "max"), monthly_volume_residual=("residual", "mean"), daily_residual_count=("residual", "size"))
        .sort_values("date")
    )

    eg = rolling[rolling["window_length"] == core["window_length"]][["date", "eg_p"]].copy()
    eg["date"] = pd.to_datetime(eg["date"])
    eg["eg_logit"] = logit(eg["eg_p"])
    merged = pd.merge(eg, monthly_resid[["date", "monthly_volume_residual", "daily_residual_count"]], on="date", how="inner")
    merged = merged[(merged["date"] >= core["core_start"]) & (merged["date"] <= core["core_end"])].copy()
    merged = merged.sort_values("date").reset_index(drop=True)
    merged["delta_eg_logit"] = merged["eg_logit"].diff()
    merged["delta_volume_residual"] = merged["monthly_volume_residual"].diff()
    return merged


def granger_design(monthly: pd.DataFrame) -> pd.DataFrame:
    frame = monthly[["date", "delta_eg_logit", "delta_volume_residual"]].dropna().copy().reset_index(drop=True)
    frame["delta_eg_logit_lag1"] = frame["delta_eg_logit"].shift(1)
    frame["delta_volume_residual_lag1"] = frame["delta_volume_residual"].shift(1)
    return frame.dropna().reset_index(drop=True)


def ols_fit(y: np.ndarray, x_columns: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray, float]:
    x = np.column_stack([np.ones(len(y)), *x_columns])
    coeffs, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ coeffs
    rss = float(np.sum(resid * resid))
    return coeffs, resid, rss


def granger_f_stat(y: np.ndarray, y_lag: np.ndarray, volume_lag: np.ndarray) -> tuple[float, dict[str, Any]]:
    restricted_coeffs, restricted_resid, restricted_rss = ols_fit(y, [y_lag])
    unrestricted_coeffs, unrestricted_resid, unrestricted_rss = ols_fit(y, [y_lag, volume_lag])
    df_num = 1
    df_den = len(y) - 3
    if df_den <= 0:
        raise RuntimeError("not enough observations for unrestricted Granger model")
    f_stat = ((restricted_rss - unrestricted_rss) / df_num) / (unrestricted_rss / df_den)
    return float(f_stat), {
        "restricted_intercept": float(restricted_coeffs[0]),
        "restricted_delta_eg_lag1_beta": float(restricted_coeffs[1]),
        "restricted_rss": restricted_rss,
        "unrestricted_intercept": float(unrestricted_coeffs[0]),
        "unrestricted_delta_eg_lag1_beta": float(unrestricted_coeffs[1]),
        "unrestricted_delta_volume_lag1_gamma": float(unrestricted_coeffs[2]),
        "unrestricted_rss": unrestricted_rss,
        "restricted_residuals": restricted_resid,
        "unrestricted_residuals": unrestricted_resid,
        "df_num": df_num,
        "df_den": int(df_den),
    }


def bootstrap_granger(
    design: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[dict[str, Any], pd.DataFrame]:
    y = design["delta_eg_logit"].to_numpy(dtype=float)
    y_lag = design["delta_eg_logit_lag1"].to_numpy(dtype=float)
    volume_lag = design["delta_volume_residual_lag1"].to_numpy(dtype=float)
    actual_f, model_info = granger_f_stat(y, y_lag, volume_lag)

    restricted_intercept = model_info["restricted_intercept"]
    restricted_beta = model_info["restricted_delta_eg_lag1_beta"]
    restricted_residuals = np.asarray(model_info["restricted_residuals"], dtype=float)
    centered_residuals = restricted_residuals - restricted_residuals.mean()

    full_delta_eg = pd.concat(
        [
            pd.Series([design.loc[0, "delta_eg_logit_lag1"]]),
            design["delta_eg_logit"],
        ],
        ignore_index=True,
    ).to_numpy(dtype=float)

    replicate_rows: list[dict[str, Any]] = []
    exceed_count = 0
    for replicate_id in range(1, BOOTSTRAP_REPLICATES + 1):
        pseudo = np.empty_like(full_delta_eg)
        pseudo[0] = full_delta_eg[0]
        sampled_errors = rng.choice(centered_residuals, size=len(y), replace=True)
        for idx in range(1, len(pseudo)):
            pseudo[idx] = restricted_intercept + restricted_beta * pseudo[idx - 1] + sampled_errors[idx - 1]
        pseudo_y_lag = pseudo[:-1]
        pseudo_y = pseudo[1:]
        pseudo_f, _ = granger_f_stat(pseudo_y, pseudo_y_lag, volume_lag)
        if pseudo_f >= actual_f:
            exceed_count += 1
        replicate_rows.append({"replicate_id": replicate_id, "bootstrap_f_stat": float(pseudo_f)})

    bootstrap_p = float((exceed_count + 1) / (BOOTSTRAP_REPLICATES + 1))
    result = {
        "actual_f_stat": actual_f,
        "bootstrap_p_value": bootstrap_p,
        "bootstrap_exceed_count": int(exceed_count),
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "n_model_obs": int(len(y)),
        "model_start_date": design.iloc[0]["date"].strftime("%Y-%m-%d"),
        "model_end_date": design.iloc[-1]["date"].strftime("%Y-%m-%d"),
        **{key: val for key, val in model_info.items() if not key.endswith("residuals")},
    }
    return result, pd.DataFrame(replicate_rows)


def fit_part_b(
    residuals: pd.DataFrame,
    rolling: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    result_rows: list[dict[str, Any]] = []
    replicate_frames: list[pd.DataFrame] = []
    monthly_frames: list[pd.DataFrame] = []

    for ticker in TICKERS:
        for core_id in CORES:
            monthly = prepare_monthly_series(residuals, rolling, ticker, core_id)
            monthly.insert(1, "ticker", ticker)
            monthly.insert(2, "core", core_id)
            monthly_frames.append(monthly)

            design = granger_design(monthly)
            result, replicates = bootstrap_granger(design, rng)
            result_rows.append(
                {
                    "ticker": ticker,
                    "core": core_id,
                    "window_length": CORES[core_id]["window_length"],
                    "core_start": CORES[core_id]["core_start"].strftime("%Y-%m-%d"),
                    "core_end": CORES[core_id]["core_end"].strftime("%Y-%m-%d"),
                    **result,
                }
            )
            replicates.insert(0, "ticker", ticker)
            replicates.insert(1, "core", core_id)
            replicate_frames.append(replicates)

    return pd.DataFrame(result_rows), pd.concat(replicate_frames, ignore_index=True), pd.concat(monthly_frames, ignore_index=True)


def multiple_comparisons(part_a_models: pd.DataFrame, part_b_results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    event_models = part_a_models[part_a_models["model_type"] == "with_event_dummy"].copy()
    for row in event_models.itertuples(index=False):
        raw_p = float(row.event_gamma_p_value_one_sided_positive_hc3_t)
        rows.append(
            {
                "part": "A",
                "test": "event_window_gamma_positive",
                "ticker": row.ticker,
                "core": row.core,
                "raw_p_value": raw_p,
                "bonferroni_family_size": BONFERRONI_FAMILY_SIZE,
                "bonferroni_threshold": BONFERRONI_THRESHOLD,
                "passes_bonferroni": bool(raw_p < BONFERRONI_THRESHOLD),
            }
        )
    for row in part_b_results.itertuples(index=False):
        raw_p = float(row.bootstrap_p_value)
        rows.append(
            {
                "part": "B",
                "test": "volume_residual_granger_causes_eg_logit",
                "ticker": row.ticker,
                "core": row.core,
                "raw_p_value": raw_p,
                "bonferroni_family_size": BONFERRONI_FAMILY_SIZE,
                "bonferroni_threshold": BONFERRONI_THRESHOLD,
                "passes_bonferroni": bool(raw_p < BONFERRONI_THRESHOLD),
            }
        )
    return pd.DataFrame(rows)


def csv_body(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False, lineterminator="\n", float_format="%.15g")
    return buffer.getvalue()


def output_header(output_name: str, timestamp_utc: str, content: str, comment: str) -> str:
    lines = [
        f"script_path: {Path(__file__).resolve()}",
        "git_commit: PENDING_STAMP",
        f"snapshot_id: {TCS_INFY_SNAPSHOT_ID}; {BENCHMARK_SNAPSHOT_ID}; rolling_metrics={ROLLING_METRICS_SNAPSHOT_ID}",
        f"timestamp_utc: {timestamp_utc}",
        f"output_file: {output_name}",
        f"output_content_sha256: {sha256_text(content)}",
        "output_hash_scope: bytes after this provenance header",
        "final_file_sha256: PENDING_STAMP",
    ]
    if comment == "csv":
        return "\n".join(f"# {line}" for line in lines) + "\n"
    if comment == "markdown":
        return "<!--\n" + "\n".join(lines) + "\n-->\n"
    raise ValueError(f"unknown comment style: {comment}")


def write_text_output(path: Path, body: str, timestamp_utc: str, description: str, comment: str) -> dict[str, Any]:
    header = output_header(path.name, timestamp_utc, body, comment)
    path.write_text(header + body, encoding="utf-8", newline="\n")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "description": description,
        "content_sha256": sha256_text(body),
        "final_file_sha256": "PENDING_STAMP",
        "hash_scope": "bytes after provenance header",
    }


def summary_body(comparisons: pd.DataFrame, part_a_models: pd.DataFrame, part_b_results: pd.DataFrame) -> str:
    rows = [
        "| Part | Ticker | Core | Raw p-value | Bonferroni threshold | Passes threshold |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in comparisons.itertuples(index=False):
        rows.append(
            f"| {row.part} | {row.ticker} | {row.core} | {row.raw_p_value:.12g} | {row.bonferroni_threshold:.8f} | {row.passes_bonferroni} |"
        )

    part_a_rows = [
        "| Ticker | Core | gamma | HC3 SE finite | HC3 t | one-sided p | n | R2 |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in part_a_models[part_a_models["model_type"] == "with_event_dummy"].itertuples(index=False):
        part_a_rows.append(
            f"| {row.ticker} | {row.core} | {row.event_gamma:.12g} | {row.event_gamma_hc3_se_is_finite} | {row.event_gamma_t_stat:.12g} | {row.event_gamma_p_value_one_sided_positive_hc3_t:.12g} | {row.n_obs} | {row.r_squared:.12g} |"
        )

    part_b_rows = [
        "| Ticker | Core | actual F | bootstrap p | model n |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in part_b_results.itertuples(index=False):
        part_b_rows.append(
            f"| {row.ticker} | {row.core} | {row.actual_f_stat:.12g} | {row.bootstrap_p_value:.12g} | {row.n_model_obs} |"
        )

    return "\n".join(
        [
            "# Independent Volume Signal Test - Codex",
            "",
            f"Claim/work question: `{CLAIM_ID}`",
            "",
            "## Multiple-Comparisons Family",
            "",
            f"Bonferroni family size: `{BONFERRONI_FAMILY_SIZE}`. Threshold: `{BONFERRONI_THRESHOLD:.8f}`.",
            "",
            *rows,
            "",
            "## Part A Event Study",
            "",
            *part_a_rows,
            "",
            "## Part B Bootstrap Granger",
            "",
            *part_b_rows,
            "",
            "## Required Limitation",
            "",
            "`^NSEI` is a broad-market control, not a sector control -- it was used because `^CNXIT` and `ITBEES.NS` failed a structural data-quality check, not because sector-level confounding was judged less relevant. This result, whatever it is, doesn't settle the sector-specific question.",
            "",
            "## Method Notes",
            "",
            "- TCS/INFY volume observations before `2018-09-06` were excluded from every regression.",
            "- Part A uses four separate event-dummy regressions and four separate no-dummy residual regressions, one per ticker/core pair.",
            "- The model-level output records whether each event-dummy HC3 standard error is finite; non-finite HC3 standard errors are left visible rather than replaced.",
            "- Part B uses monthly mean residuals, logit-transformed EG p-values, first differences, lag 1, and a residual bootstrap under the restricted null.",
            "- Bootstrap RNG seed: `20260712`; replicate count per test: `2000`.",
            "",
        ]
    )


def worklog_body(comparisons: pd.DataFrame, part_a_models: pd.DataFrame, part_b_results: pd.DataFrame) -> str:
    body = summary_body(comparisons, part_a_models, part_b_results)
    return "\n".join(
        [
            f"## {CLAIM_ID}",
            "",
            body,
        ]
    )


def write_worklog_entry(
    comparisons: pd.DataFrame,
    part_a_models: pd.DataFrame,
    part_b_results: pd.DataFrame,
    timestamp_utc: str,
) -> dict[str, Any]:
    body = worklog_body(comparisons, part_a_models, part_b_results)
    return write_text_output(
        OUT_DIR / "worklog_entry.md",
        body,
        timestamp_utc,
        "Append-ready Tier B worklog entry",
        "markdown",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    tcs_infy, benchmark, rolling, tcs_infy_metadata, benchmark_metadata = load_inputs()

    part_a_coefficients, part_a_models, residuals, event_windows = fit_part_a(tcs_infy, benchmark)
    part_b_results, bootstrap_replicates, monthly_series = fit_part_b(residuals, rolling)
    comparisons = multiple_comparisons(part_a_models, part_b_results)

    outputs: list[dict[str, Any]] = []
    outputs.append(
        write_text_output(
            OUT_DIR / "part_a_regression_coefficients.csv",
            csv_body(part_a_coefficients),
            timestamp_utc,
            "HC3 coefficient tables for Part A regressions",
            "csv",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "part_a_regression_models.csv",
            csv_body(part_a_models),
            timestamp_utc,
            "Model-level Part A regression statistics",
            "csv",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "part_a_event_windows.csv",
            csv_body(event_windows),
            timestamp_utc,
            "The 20 pre-breakdown trading days used for each event dummy",
            "csv",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "market_adjusted_volume_residuals_daily.csv",
            csv_body(residuals),
            timestamp_utc,
            "Daily residuals from no-dummy Part A regressions",
            "csv",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "market_adjusted_volume_residuals_monthly.csv",
            csv_body(monthly_series),
            timestamp_utc,
            "Monthly mean residuals joined to EG p-values and first differences",
            "csv",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "part_b_granger_results.csv",
            csv_body(part_b_results),
            timestamp_utc,
            "Bootstrap Granger results",
            "csv",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "part_b_bootstrap_replicates.csv",
            csv_body(bootstrap_replicates),
            timestamp_utc,
            "Full bootstrap F-statistic replicate array",
            "csv",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "multiple_comparisons.csv",
            csv_body(comparisons),
            timestamp_utc,
            "Raw p-values and Bonferroni threshold for all eight tests",
            "csv",
        )
    )
    outputs.append(
        write_text_output(
            OUT_DIR / "summary.md",
            summary_body(comparisons, part_a_models, part_b_results),
            timestamp_utc,
            "Human-readable summary",
            "markdown",
        )
    )
    outputs.append(write_worklog_entry(comparisons, part_a_models, part_b_results, timestamp_utc))

    provenance = {
        "claim_id": CLAIM_ID,
        "phase": "phase_i_tcs_infy_pairs_trading",
        "tier": TIER,
        "script_path": str(Path(__file__).resolve().relative_to(ROOT)).replace("\\", "/"),
        "script_sha256": file_sha256(Path(__file__).resolve()),
        "git_commit": "PENDING_STAMP",
        "timestamp_utc": timestamp_utc,
        "snapshot_ids": [TCS_INFY_SNAPSHOT_ID, BENCHMARK_SNAPSHOT_ID, ROLLING_METRICS_SNAPSHOT_ID],
        "input_files": [
            {
                "path": str(TCS_INFY_OHLCV.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha256(TCS_INFY_OHLCV),
                "metadata_sha256": file_sha256(TCS_INFY_METADATA),
                "metadata": tcs_infy_metadata,
            },
            {
                "path": str(BENCHMARK_OHLCV.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha256(BENCHMARK_OHLCV),
                "metadata_sha256": file_sha256(BENCHMARK_METADATA),
                "metadata": benchmark_metadata,
                "ticker_filter": "^NSEI only",
            },
            {
                "path": str(ROLLING_METRICS.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha256(ROLLING_METRICS),
                "window_filters": {"500d": 500, "730d": 730},
                "column_used": "eg_p",
            },
        ],
        "parameters": {
            "data_floor": DATA_FLOOR.strftime("%Y-%m-%d"),
            "event_window": "20 trading days immediately before each core breakdown date, excluding breakdown date",
            "part_a_covariance": "HC3 robust standard errors, Student-t p-values with df_resid",
            "part_a_event_p_value": "one-sided positive p-value for event_window_dummy gamma",
            "part_b_transform": "logit EG p-value, first difference EG logit and monthly mean volume residual",
            "part_b_bootstrap": {
                "replicates": BOOTSTRAP_REPLICATES,
                "seed": BOOTSTRAP_SEED,
                "null": "restricted AR(1) in delta EG logit without lagged volume residual",
            },
            "multiple_comparisons": {
                "family_size": BONFERRONI_FAMILY_SIZE,
                "threshold": BONFERRONI_THRESHOLD,
            },
        },
        "outputs": outputs,
    }
    (OUT_DIR / "provenance.json").write_text(
        json.dumps(json_safe(provenance), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"claim_id={CLAIM_ID}")
    print(f"timestamp_utc={timestamp_utc}")
    print(comparisons.to_string(index=False))
    print(f"outputs={len(outputs) + 1}")


if __name__ == "__main__":
    main()
