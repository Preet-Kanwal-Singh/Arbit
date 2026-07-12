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
import scipy
import statsmodels
import statsmodels.api as sm
from scipy.stats import norm


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent

CLAIM_ID = "claim_005_volume_event_study_tcs500d"
TCS_SNAPSHOT_ID = "tcs_infy_v2_2026-07-11"
BENCHMARK_SNAPSHOT_ID = "nifty_it_benchmark_v1_2026-07-11"

TCS_SNAPSHOT_DIR = ROOT / "data" / "snapshots" / TCS_SNAPSHOT_ID
BENCHMARK_SNAPSHOT_DIR = ROOT / "data" / "snapshots" / BENCHMARK_SNAPSHOT_ID

TCS_CSV = TCS_SNAPSHOT_DIR / "ohlcv.csv"
TCS_METADATA_JSON = TCS_SNAPSHOT_DIR / "metadata.json"
BENCHMARK_CSV = BENCHMARK_SNAPSHOT_DIR / "ohlcv.csv"
BENCHMARK_METADATA_JSON = BENCHMARK_SNAPSHOT_DIR / "metadata.json"

TCS_TICKER = "TCS.NS"
BENCHMARK_TICKER = "^NSEI"
DATA_FLOOR = pd.Timestamp("2018-09-06")
ESTIMATION_END = pd.Timestamp("2026-07-10")
ANCHOR_DATE = pd.Timestamp("2021-12-31")
EVENT_WINDOW_LENGTH = 20
SIGNIFICANCE_THRESHOLD = 0.05

EXPECTED_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def script_sha256() -> str:
    return file_sha256(Path(__file__).resolve())


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


def load_metadata(path: Path, expected_snapshot_id: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing snapshot metadata: {path}")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    actual_id = metadata.get("snapshot_id")
    if actual_id != expected_snapshot_id:
        raise RuntimeError(
            f"metadata snapshot_id mismatch: {actual_id!r} != {expected_snapshot_id!r}"
        )
    if metadata.get("last_data_date") != ESTIMATION_END.strftime("%Y-%m-%d"):
        raise RuntimeError(
            f"{expected_snapshot_id} last_data_date mismatch: "
            f"{metadata.get('last_data_date')!r} != {ESTIMATION_END.date()}"
        )
    return metadata


def validate_snapshot_file(
    csv_path: Path,
    metadata: dict[str, Any],
    expected_snapshot_id: str,
) -> str:
    if not csv_path.exists():
        raise FileNotFoundError(f"missing snapshot data: {csv_path}")

    declared = metadata.get("files", {}).get("ohlcv.csv", {}).get("sha256")
    if not declared:
        raise RuntimeError(f"{expected_snapshot_id} metadata has no ohlcv.csv SHA256")

    actual = file_sha256(csv_path)
    if actual != declared:
        raise RuntimeError(
            f"{expected_snapshot_id} ohlcv.csv SHA256 mismatch: {actual} != {declared}"
        )
    return actual


def load_ticker_volume(csv_path: Path, ticker: str) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, parse_dates=["date"])
    missing = [column for column in EXPECTED_COLUMNS if column not in frame.columns]
    if missing:
        raise RuntimeError(f"{csv_path} missing required columns: {missing}")

    subset = frame.loc[frame["ticker"].eq(ticker), ["date", "volume"]].copy()
    if subset.empty:
        raise RuntimeError(f"no rows found for ticker {ticker} in {csv_path}")

    if subset["date"].duplicated().any():
        duplicates = (
            subset.loc[subset["date"].duplicated(keep=False), "date"]
            .dt.strftime("%Y-%m-%d")
            .tolist()
        )
        raise RuntimeError(f"duplicate dates for {ticker}: {duplicates}")

    if subset["volume"].isna().any():
        dates = subset.loc[subset["volume"].isna(), "date"].dt.strftime("%Y-%m-%d").tolist()
        raise RuntimeError(f"missing volume values for {ticker}: {dates}")

    if (subset["volume"] < 0).any():
        dates = subset.loc[subset["volume"] < 0, "date"].dt.strftime("%Y-%m-%d").tolist()
        raise RuntimeError(f"negative volume values for {ticker}: {dates}")

    return subset.sort_values("date").reset_index(drop=True)


def to_csv_body(df: pd.DataFrame) -> str:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def write_csv(path: Path, df: pd.DataFrame) -> dict[str, Any]:
    body = to_csv_body(df)
    path.write_text(body, encoding="utf-8", newline="\n")
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": file_sha256(path),
        "rows": int(len(df)),
    }


def write_json(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.write_text(body, encoding="utf-8", newline="\n")
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": file_sha256(path),
    }


def markdown_table(df: pd.DataFrame) -> str:
    columns = list(df.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in df.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def build_data_quality_report(
    tcs_post_floor: pd.DataFrame,
    nsei_post_floor: pd.DataFrame,
    merged_pre_drop: pd.DataFrame,
    analysis: pd.DataFrame,
    tcs_only_dates: list[pd.Timestamp],
    nsei_only_dates: list[pd.Timestamp],
    zero_drop_mask: pd.Series,
    event_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    rows = [
        ("claim_id", CLAIM_ID),
        ("data_floor", DATA_FLOOR.strftime("%Y-%m-%d")),
        ("estimation_end", ESTIMATION_END.strftime("%Y-%m-%d")),
        ("anchor_date", ANCHOR_DATE.strftime("%Y-%m-%d")),
        ("event_window_length", EVENT_WINDOW_LENGTH),
        ("tcs_post_floor_rows", len(tcs_post_floor)),
        ("nsei_post_floor_rows", len(nsei_post_floor)),
        (
            "tcs_zero_volume_count_post_floor_pre_merge",
            int(tcs_post_floor["volume"].eq(0).sum()),
        ),
        (
            "nsei_zero_volume_count_post_floor_pre_merge",
            int(nsei_post_floor["volume"].eq(0).sum()),
        ),
        ("inner_join_rows_pre_zero_drop", len(merged_pre_drop)),
        ("tcs_only_dates_dropped_by_inner_join", len(tcs_only_dates)),
        ("nsei_only_dates_dropped_by_inner_join", len(nsei_only_dates)),
        (
            "total_unmatched_dates_dropped_by_inner_join",
            len(tcs_only_dates) + len(nsei_only_dates),
        ),
        (
            "tcs_zero_volume_count_merged_pre_drop",
            int(merged_pre_drop["TCS_Volume"].eq(0).sum()),
        ),
        (
            "nsei_zero_volume_count_merged_pre_drop",
            int(merged_pre_drop["NSEI_Volume"].eq(0).sum()),
        ),
        ("zero_volume_rows_dropped", int(zero_drop_mask.sum())),
        ("analysis_rows_after_zero_drop", len(analysis)),
        ("event_window_rows_pre_zero_drop", len(event_dates)),
        (
            "event_window_rows_dropped_for_zero_volume",
            int(
                merged_pre_drop.loc[zero_drop_mask, "date"]
                .isin(event_dates)
                .sum()
            ),
        ),
        (
            "event_window_rows_in_regression",
            int(analysis["EventWindowDummy"].sum()),
        ),
        ("event_window_first_date", event_dates[0].strftime("%Y-%m-%d")),
        ("event_window_last_date", event_dates[-1].strftime("%Y-%m-%d")),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    script_path = Path(__file__).resolve()
    commit = git_commit()

    tcs_metadata = load_metadata(TCS_METADATA_JSON, TCS_SNAPSHOT_ID)
    benchmark_metadata = load_metadata(BENCHMARK_METADATA_JSON, BENCHMARK_SNAPSHOT_ID)
    tcs_csv_sha256 = validate_snapshot_file(TCS_CSV, tcs_metadata, TCS_SNAPSHOT_ID)
    benchmark_csv_sha256 = validate_snapshot_file(
        BENCHMARK_CSV, benchmark_metadata, BENCHMARK_SNAPSHOT_ID
    )

    tcs = load_ticker_volume(TCS_CSV, TCS_TICKER)
    nsei = load_ticker_volume(BENCHMARK_CSV, BENCHMARK_TICKER)

    # The estimation sample is explicitly bounded at both ends before the join.
    tcs = tcs.loc[tcs["date"].between(DATA_FLOOR, ESTIMATION_END)].copy()
    nsei = nsei.loc[nsei["date"].between(DATA_FLOOR, ESTIMATION_END)].copy()
    if tcs.empty or nsei.empty:
        raise RuntimeError("one or both ticker samples are empty after estimation bounds")

    # Report the exact dates removed by the required inner join.
    tcs_dates = pd.DatetimeIndex(tcs["date"])
    nsei_dates = pd.DatetimeIndex(nsei["date"])
    tcs_only_dates = sorted(tcs_dates.difference(nsei_dates))
    nsei_only_dates = sorted(nsei_dates.difference(tcs_dates))

    merged = (
        tcs.rename(columns={"volume": "TCS_Volume"})
        .merge(
            nsei.rename(columns={"volume": "NSEI_Volume"}),
            on="date",
            how="inner",
            validate="one_to_one",
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    if merged.empty:
        raise RuntimeError("inner join produced an empty estimation sample")

    # Fix the event window against the full merged calendar BEFORE zero-volume rows
    # are removed. The anchor date itself is excluded by the [-20,-1] definition.
    pre_anchor = merged.loc[merged["date"] < ANCHOR_DATE, "date"]
    if len(pre_anchor) < EVENT_WINDOW_LENGTH:
        raise RuntimeError(
            f"fewer than {EVENT_WINDOW_LENGTH} merged trading days before anchor"
        )
    event_dates = pd.DatetimeIndex(pre_anchor.tail(EVENT_WINDOW_LENGTH))
    if len(event_dates) != EVENT_WINDOW_LENGTH or event_dates.duplicated().any():
        raise RuntimeError("event window construction did not yield 20 unique dates")

    event_window_dates = pd.DataFrame(
        {
            "event_time": np.arange(-EVENT_WINDOW_LENGTH, 0, dtype=int),
            "date": event_dates.strftime("%Y-%m-%d"),
        }
    )

    # Final Option 1 rule in the spec: after the event calendar is fixed, remove
    # rows with zero volume in either series and report the exact dropped dates.
    zero_drop_mask = merged["TCS_Volume"].eq(0) | merged["NSEI_Volume"].eq(0)
    dropped_zero = merged.loc[
        zero_drop_mask, ["date", "TCS_Volume", "NSEI_Volume"]
    ].copy()
    dropped_zero["TCS_zero"] = dropped_zero["TCS_Volume"].eq(0)
    dropped_zero["NSEI_zero"] = dropped_zero["NSEI_Volume"].eq(0)
    dropped_zero["date"] = dropped_zero["date"].dt.strftime("%Y-%m-%d")

    analysis = merged.loc[~zero_drop_mask].copy()
    analysis["EventWindowDummy"] = analysis["date"].isin(event_dates).astype(int)

    if (analysis["TCS_Volume"] <= 0).any() or (analysis["NSEI_Volume"] <= 0).any():
        raise RuntimeError("non-positive volume remains after the specified zero drop")

    analysis["log_TCS_Volume"] = np.log(analysis["TCS_Volume"].astype(float))
    analysis["log_NSEI_Volume"] = np.log(analysis["NSEI_Volume"].astype(float))
    analysis["day_of_week"] = analysis["date"].dt.day_name()

    # Monday is the fixed omitted category. With an intercept this yields four
    # day-of-week indicators: Tuesday, Wednesday, Thursday, Friday

    dow_categories = [
    day for day in
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if day in set(analysis["day_of_week"])
    ]

    dow = pd.get_dummies(
        pd.Categorical(
            analysis["day_of_week"],
            categories=dow_categories,
            ordered=False,
        ),
        prefix="DOW",
        dtype=float,
    )

    dow = dow.drop(columns=["DOW_Monday"])

    X = pd.concat(
        [
            analysis[["log_NSEI_Volume"]].reset_index(drop=True),
            dow.reset_index(drop=True),
            analysis[["EventWindowDummy"]].reset_index(drop=True),
        ],
        axis=1,
    )
    X = sm.add_constant(X, has_constant="add").astype(float)
    y = analysis["log_TCS_Volume"].reset_index(drop=True).astype(float)

    model = sm.OLS(y, X)
    result = model.fit(cov_type="HC3")

    gamma = float(result.params["EventWindowDummy"])
    gamma_se = float(result.bse["EventWindowDummy"])
    gamma_stat = float(gamma / gamma_se) if gamma_se != 0 else float("nan")

    if not math.isfinite(gamma_se):
        raise RuntimeError(
            "INVALID reproduction: EventWindowDummy HC3 standard error is non-finite"
        )
    if gamma_se <= 0:
        raise RuntimeError(
            "INVALID reproduction: EventWindowDummy HC3 standard error is not positive"
        )
    if not math.isfinite(gamma_stat):
        raise RuntimeError(
            "INVALID reproduction: EventWindowDummy test statistic is non-finite"
        )

    # HC3 covariance with statsmodels OLS uses asymptotic normal inference here.
    # For the pre-declared one-sided alternative gamma > 0, p = P[Z >= gamma/SE].
    one_sided_p = float(norm.sf(gamma_stat))
    significant = bool(one_sided_p < SIGNIFICANCE_THRESHOLD)
    individual_result = (
        "POSITIVE_P_LT_0.05" if significant else "DOES_NOT_REACH_P_LT_0.05"
    )

    coefficient_rows = []
    for term in result.params.index:
        coefficient_rows.append(
            {
                "claim_id": CLAIM_ID,
                "term": term,
                "coefficient": float(result.params[term]),
                "hc3_standard_error": float(result.bse[term]),
                "test_statistic": float(result.params[term] / result.bse[term]),
                "two_sided_asymptotic_p_value": float(result.pvalues[term]),
                "one_sided_p_value_gamma_gt_0": (
                    one_sided_p if term == "EventWindowDummy" else np.nan
                ),
                "n_obs": int(result.nobs),
                "r_squared": float(result.rsquared),
                "adjusted_r_squared": float(result.rsquared_adj),
                "covariance_type": "HC3",
                "event_window_significant_p_lt_0_05": (
                    significant if term == "EventWindowDummy" else ""
                ),
                "individual_reproduction_result": (
                    individual_result if term == "EventWindowDummy" else ""
                ),
            }
        )
    regression_results = pd.DataFrame(coefficient_rows)

    data_quality_report = build_data_quality_report(
        tcs_post_floor=tcs,
        nsei_post_floor=nsei,
        merged_pre_drop=merged,
        analysis=analysis,
        tcs_only_dates=tcs_only_dates,
        nsei_only_dates=nsei_only_dates,
        zero_drop_mask=zero_drop_mask,
        event_dates=event_dates,
    )

    outputs: list[dict[str, Any]] = []
    outputs.append(
        write_csv(OUT_DIR / "data_quality_report.csv", data_quality_report)
    )
    outputs.append(
        write_csv(OUT_DIR / "dropped_zero_volume_dates.csv", dropped_zero)
    )
    outputs.append(
        write_csv(OUT_DIR / "event_window_dates.csv", event_window_dates)
    )
    outputs.append(
        write_csv(OUT_DIR / "regression_results.csv", regression_results)
    )

    summary_result = pd.DataFrame(
        [
            {
                "gamma": f"{gamma:.10f}",
                "HC3_SE": f"{gamma_se:.10f}",
                "test_statistic": f"{gamma_stat:.10f}",
                "one_sided_p_gamma_gt_0": f"{one_sided_p:.10g}",
                "p_lt_0_05": significant,
                "individual_result": individual_result,
            }
        ]
    )

    limitation = (
        "This claim tests a window anchored to claim_002's admitted healthy-core "
        "boundary (2021-12-31), not the window explored in the prior Tier B pass "
        "(2022-01-31, an unadmitted date; open_questions.md #18 remains open). "
        "The two prior exploratory runs tested a different window and do not "
        "constitute prior replication of this specific result. This window was "
        "selected because a nearby window showed a strong result in that unadmitted "
        "exploratory pass; therefore a bare p<0.05 pass here should not be weighted "
        "as equivalent evidence to a pre-registered blind test. If cross-implementation "
        "agreement is achieved, the permanent positive outcome label is "
        "REPRODUCED-ADJACENT-WINDOW, not REPRODUCED."
    )

    summary_body = f"""# Claim 005 Volume Event Study — Independent Tier A Implementation

## Individual Reproduction Result

{markdown_table(summary_result)}

Cross-implementation status is intentionally not assigned by this script. The second
independent reproduction must be compared using the pre-declared coefficient tolerance
`|gamma_A - gamma_B| <= 0.03`, finite HC3 standard errors in both runs, and the claim's
outcome rules.

## Event Window

- Anchor date: `2021-12-31`.
- Definition: the 20 merged-calendar trading days immediately preceding the anchor,
  `[-20,-1]`.
- First event date: `{event_dates[0].strftime("%Y-%m-%d")}`.
- Last event date: `{event_dates[-1].strftime("%Y-%m-%d")}`.
- The event window was fixed before zero-volume rows were dropped.

## Model

`ln(TCS_Volume_t) = alpha + beta * ln(NSEI_Volume_t) + day-of-week dummies + gamma * EventWindowDummy_t + epsilon_t`

- Natural logarithms throughout.
- Monday is the omitted day-of-week category.
- HC3 robust covariance.
- One-sided alternative: `gamma > 0`.
- One-sided p-value uses the asymptotic standard-normal tail of `gamma / HC3_SE`.

## Data Handling

- TCS snapshot: `{TCS_SNAPSHOT_ID}`.
- Benchmark snapshot: `{BENCHMARK_SNAPSHOT_ID}`; only `{BENCHMARK_TICKER}` is used.
- Estimation bounds: `2018-09-06` through `2026-07-10`.
- TCS and NSEI are inner-joined on date.
- Exact unmatched-date counts and zero-volume diagnostics are in
  `data_quality_report.csv`.
- Exact zero-volume rows removed after event-window construction are in
  `dropped_zero_volume_dates.csv`.
- Exact event dates are in `event_window_dates.csv`.

## Required Limitation

{limitation}

## Non-Goals

This implementation does not confirm or deny the original Tier B finding for the window
before `2022-01-31`. It does not re-test the 730d core or INFY.
"""
    summary_path = OUT_DIR / "summary.md"
    summary_path.write_text(summary_body, encoding="utf-8", newline="\n")
    outputs.append(
        {
            "path": str(summary_path.relative_to(ROOT)),
            "sha256": file_sha256(summary_path),
        }
    )

    provenance = {
        "claim_id": CLAIM_ID,
        "tier": "A",
        "phase": "phase_i_tcs_infy_pairs_trading",
        "implementation": "independent",
        "timestamp_utc": timestamp_utc,
        "script_path": str(script_path),
        "script_sha256": script_sha256(),
        "git_commit": commit,
        "git_status_short_at_run": git_status_short(),
        "python_executable": sys.executable,
        "versions": {
            "python": sys.version,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
        },
        "snapshots": {
            "tcs": {
                "snapshot_id": TCS_SNAPSHOT_ID,
                "ohlcv_sha256": tcs_csv_sha256,
                "metadata": tcs_metadata,
            },
            "benchmark": {
                "snapshot_id": BENCHMARK_SNAPSHOT_ID,
                "ticker_used": BENCHMARK_TICKER,
                "ohlcv_sha256": benchmark_csv_sha256,
                "metadata": benchmark_metadata,
            },
        },
        "fixed_method": {
            "data_floor": DATA_FLOOR.strftime("%Y-%m-%d"),
            "estimation_end": ESTIMATION_END.strftime("%Y-%m-%d"),
            "anchor_date": ANCHOR_DATE.strftime("%Y-%m-%d"),
            "event_window": "20 merged-calendar trading days immediately before anchor; [-20,-1]",
            "event_window_defined_before_zero_volume_drop": True,
            "zero_volume_rule": "After event-window identification, drop any merged row where TCS_Volume == 0 or NSEI_Volume == 0 and report exact dates.",
            "log_base": "natural",
            "day_of_week_baseline": "Monday",
            "covariance_type": "HC3",
            "alternative": "gamma > 0",
            "one_sided_p_value": "scipy.stats.norm.sf(gamma / HC3_SE)",
            "significance_threshold": SIGNIFICANCE_THRESHOLD,
            "cross_implementation_gamma_tolerance": 0.03,
        },
        "diagnostics": {
            "tcs_only_dates_dropped_by_inner_join": [
                date.strftime("%Y-%m-%d") for date in tcs_only_dates
            ],
            "nsei_only_dates_dropped_by_inner_join": [
                date.strftime("%Y-%m-%d") for date in nsei_only_dates
            ],
            "zero_volume_dates_dropped": dropped_zero["date"].tolist(),
            "event_window_dates": event_window_dates["date"].tolist(),
        },
        "individual_result": {
            "gamma": gamma,
            "hc3_standard_error": gamma_se,
            "test_statistic": gamma_stat,
            "one_sided_p_value_gamma_gt_0": one_sided_p,
            "p_lt_0_05": significant,
            "status": individual_result,
        },
        "cross_implementation_status": "PENDING_INDEPENDENT_COMPARISON",
        "positive_cross_implementation_label_if_rules_met": "REPRODUCED-ADJACENT-WINDOW",
        "required_limitation": limitation,
        "outputs": outputs,
    }
    provenance_output = write_json(OUT_DIR / "provenance.json", provenance)

    print(f"claim_id={CLAIM_ID}")
    print(f"gamma={gamma:.10f}")
    print(f"hc3_se={gamma_se:.10f}")
    print(f"one_sided_p_gamma_gt_0={one_sided_p:.10g}")
    print(f"individual_result={individual_result}")
    print(f"outputs_dir={OUT_DIR}")
    for row in outputs + [provenance_output]:
        print(f"{row['path']} {row['sha256']}")


if __name__ == "__main__":
    main()
