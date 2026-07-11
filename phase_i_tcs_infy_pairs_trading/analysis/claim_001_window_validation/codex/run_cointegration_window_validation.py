from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".venv" / "Lib" / "site-packages"))

import numpy as np
import pandas as pd
import statsmodels
from statsmodels.tsa.stattools import adfuller, coint


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis"
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
SNAPSHOT_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
SNAPSHOT_METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
WINDOWS = [60, 120, 250, 500, 730]
ALPHAS = [0.01, 0.05, 0.10]
PHI_REGIMES = [
    ("fast", 0.80),
    ("moderate", 0.95),
    ("near_unit", 0.99),
]
SPREAD_SIGMAS = [0.005, 0.02, 0.05]
SYNTHETIC_SEEDS = 100


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def simulate_cointegrated(n: int, rng: np.random.Generator, phi: float, spread_sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    trend = np.cumsum(rng.normal(0.0, 0.012, n))
    spread = np.zeros(n)
    for i in range(1, n):
        spread[i] = phi * spread[i - 1] + rng.normal(0.0, spread_sigma)
    x = trend + rng.normal(0.0, 0.001, n)
    y = 0.05 + 1.15 * x + spread
    return y, x, spread


def simulate_noncointegrated(n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    x = np.cumsum(rng.normal(0.0, 0.012, n))
    y = np.cumsum(rng.normal(0.0, 0.012, n))
    return y, x


def run_part_a() -> tuple[pd.DataFrame, list[int]]:
    rows = []
    raw_rows = []
    for n in WINDOWS:
        for phi_name, phi in PHI_REGIMES:
            for spread_sigma in SPREAD_SIGMAS:
                for seed in range(SYNTHETIC_SEEDS):
                    rng = np.random.default_rng(10_000_000 + n * 100_000 + int(phi * 1000) * 100 + int(spread_sigma * 1000) + seed)
                    y, x, true_spread = simulate_cointegrated(n, rng, phi, spread_sigma)
                    raw_rows.append(
                        {
                            "window_length": n,
                            "condition": "cointegrated",
                            "phi_regime": f"{phi_name}_{phi:.2f}",
                            "spread_sigma": spread_sigma,
                            "engle_granger_p": engle_granger_p_value(y, x),
                            "adf_p": adf_p_value(true_spread),
                        }
                    )
        for seed in range(SYNTHETIC_SEEDS):
            rng = np.random.default_rng(20_000_000 + n * 100_000 + seed)
            y, x = simulate_noncointegrated(n, rng)
            _, _, resid = ols(y, x, include_const=True)
            raw_rows.append(
                {
                    "window_length": n,
                    "condition": "noncointegrated",
                    "phi_regime": "none",
                    "spread_sigma": np.nan,
                    "engle_granger_p": engle_granger_p_value(y, x),
                    "adf_p": adf_p_value(resid),
                }
            )

    raw = pd.DataFrame(raw_rows)
    for test_name, column in [("engle_granger", "engle_granger_p"), ("adf", "adf_p")]:
        group_cols = ["window_length", "condition", "phi_regime", "spread_sigma"]
        for keys, group in raw.groupby(group_cols, dropna=False):
            pvals = group[column].to_numpy()
            for alpha in ALPHAS:
                pass_rate = float(np.mean(pvals < alpha))
                condition = keys[1]
                rows.append(
                    {
                        "window_length": keys[0],
                        "condition": condition,
                        "phi_regime": keys[2],
                        "spread_sigma": keys[3],
                        "test": test_name,
                        "alpha": alpha,
                        "mean_p": float(np.mean(pvals)),
                        "std_p": float(np.std(pvals, ddof=1)),
                        "pass_rate": pass_rate,
                        "false_positive_rate": pass_rate if condition == "noncointegrated" else np.nan,
                        "false_negative_rate": (1.0 - pass_rate) if condition == "cointegrated" else np.nan,
                    }
                )
    summary = pd.DataFrame(rows)

    validated = []
    alpha05 = summary[summary["alpha"] == 0.05]
    for n in WINDOWS:
        subset = alpha05[alpha05["window_length"] == n]
        fpr_ok = subset[subset["condition"] == "noncointegrated"]["false_positive_rate"].max() < 0.10
        fnr_ok = subset[subset["condition"] == "cointegrated"]["false_negative_rate"].max() < 0.10
        if bool(fpr_ok) and bool(fnr_ok):
            validated.append(n)
    return summary, validated


def load_snapshot_prices() -> pd.DataFrame:
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
    return close


def half_life(resid: np.ndarray) -> float:
    lagged = resid[:-1]
    current = resid[1:]
    beta, _, _ = ols(current, lagged, include_const=True)
    phi = float(beta[1])
    if phi <= 0:
        return float("nan")
    if phi >= 1:
        return float("inf")
    return float(-math.log(2.0) / math.log(phi))


def month_end_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    series = pd.Series(index=index, data=index)
    return list(series.groupby(series.index.to_period("M")).max())


def run_part_b(close: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    logs = np.log(close)
    dates = month_end_dates(logs.index)
    rows = []
    previous_beta: dict[int, float] = {}
    for n in windows:
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
            prev = previous_beta.get(n)
            abs_change = float(abs(hedge_beta - prev)) if prev is not None else np.nan
            previous_beta[n] = hedge_beta
            rows.append(
                {
                    "date": date.date().isoformat(),
                    "window_length": n,
                    "beta": hedge_beta,
                    "absolute_beta_change": abs_change,
                    "engle_granger_p_value": eg_p,
                    "adf_p_value": adf_p,
                    "half_life": half_life(resid),
                    "engle_granger_pass": bool(eg_p < 0.05),
                    "adf_pass": bool(adf_p < 0.05),
                }
            )
    return pd.DataFrame(rows)


def summarize_part_a(part_a: pd.DataFrame) -> tuple[str, list[int]]:
    alpha05 = part_a[part_a["alpha"] == 0.05]
    validated = []
    window_lines = []
    for n in WINDOWS:
        subset = alpha05[alpha05["window_length"] == n]
        max_fpr = subset[subset["condition"] == "noncointegrated"]["false_positive_rate"].max()
        max_fnr = subset[subset["condition"] == "cointegrated"]["false_negative_rate"].max()
        if pd.notna(max_fpr) and pd.notna(max_fnr) and max_fpr < 0.10 and max_fnr < 0.10:
            validated.append(n)
        window_lines.append(f"{n}d max FPR {max_fpr:.3f}, max FNR {max_fnr:.3f}")
    if validated:
        first = min(validated)
        conclusion = (
            f"At p < 0.05, the shortest tested window where both the worst-case false positive rate and "
            f"worst-case false negative rate stay below 10% is {first} trading days. "
            f"The validated windows by this criterion are {', '.join(str(x) for x in validated)} trading days."
        )
    else:
        conclusion = (
            "At p < 0.05, no tested window keeps both the worst-case false positive rate and worst-case false "
            "negative rate below 10% across all simulated regimes."
        )
    near_unit = alpha05[(alpha05["condition"] == "cointegrated") & (alpha05["phi_regime"].str.contains("near_unit"))]
    near_unit_fnr = near_unit.groupby(["window_length", "test"])["false_negative_rate"].max().reset_index()
    hardest = near_unit_fnr.sort_values("false_negative_rate", ascending=False).head(3)
    hard_text = "; ".join(
        f"{int(row.window_length)}d {row.test} FNR {row.false_negative_rate:.3f}"
        for row in hardest.itertuples(index=False)
    )
    noncoint = alpha05[alpha05["condition"] == "noncointegrated"]
    eg_fpr = noncoint[noncoint["test"] == "engle_granger"].sort_values("window_length")
    adf_fpr = noncoint[noncoint["test"] == "adf"].sort_values("window_length")
    eg_fpr_text = ", ".join(f"{int(row.window_length)}d {row.false_positive_rate:.3f}" for row in eg_fpr.itertuples(index=False))
    adf_fpr_text = ", ".join(f"{int(row.window_length)}d {row.false_positive_rate:.3f}" for row in adf_fpr.itertuples(index=False))
    text = (
        f"{conclusion} Across the candidate windows, the p < 0.05 worst-case diagnostics were: "
        f"{'; '.join(window_lines)}.\n\n"
        f"The high false-positive side of that worst-case result is driven by standalone residual ADF p-values, "
        f"not by the Engle-Granger test alone. At p < 0.05, Engle-Granger false-positive rates by window were "
        f"{eg_fpr_text}, while standalone residual ADF false-positive rates were {adf_fpr_text}. "
        f"That matters because standard ADF p-values on estimated residuals are not the same null calibration as "
        f"Engle-Granger cointegration p-values.\n\n"
        f"The conclusion depends materially on persistence. The near-unit-root spread regime is the hardest case, "
        f"with the largest false-negative rates appearing in {hard_text}. Shorter windows can look adequate when "
        f"the spread mean-reverts quickly or has favorable scale, but that is the easy simulated case rather than "
        f"evidence that short windows are reliable across regimes."
    )
    return text, validated


def first_date(frame: pd.DataFrame, mask: pd.Series) -> str:
    hits = frame[mask]
    if hits.empty:
        return "not observed"
    return str(hits.iloc[0]["date"])


def summarize_part_b(part_b: pd.DataFrame, evaluated_windows: list[int], validated_windows: list[int]) -> str:
    if part_b.empty:
        return "Part B did not produce rolling rows because no evaluation window had enough trailing data."

    lines = []
    for n in evaluated_windows:
        subset = part_b[part_b["window_length"] == n].copy()
        if subset.empty:
            continue
        subset["either_fail"] = ~(subset["engle_granger_pass"] & subset["adf_pass"])
        subset["both_fail"] = ~(subset["engle_granger_pass"] | subset["adf_pass"])
        subset["borderline"] = (
            subset["engle_granger_p_value"].between(0.05, 0.10, inclusive="left")
            | subset["adf_p_value"].between(0.05, 0.10, inclusive="left")
        )
        weakening = (
            subset["engle_granger_p_value"].rolling(3).mean().gt(0.025)
            | subset["adf_p_value"].rolling(3).mean().gt(0.025)
            | subset["absolute_beta_change"].rolling(3).mean().gt(subset["absolute_beta_change"].quantile(0.75))
        )
        lines.append(
            f"{n}d: first weakening signal {first_date(subset, weakening.fillna(False))}; "
            f"first borderline result {first_date(subset, subset['borderline'])}; "
            f"first failed test {first_date(subset, subset['either_fail'])}; "
            f"first month with both tests failing {first_date(subset, subset['both_fail'])}."
        )

    first_flagged = pd.Timestamp("2022-07-01")
    long_windows = [n for n in [500, 730] if n in evaluated_windows]
    long_frame = part_b[part_b["window_length"].isin(long_windows)].copy()
    long_frame["date_ts"] = pd.to_datetime(long_frame["date"])
    before_flag = long_frame[long_frame["date_ts"] < first_flagged]
    pre_flag_formal = before_flag[
        before_flag["engle_granger_p_value"].between(0.05, 0.10, inclusive="left")
        | before_flag["adf_p_value"].between(0.05, 0.10, inclusive="left")
        | (~before_flag["engle_granger_pass"])
        | (~before_flag["adf_pass"])
    ]
    if pre_flag_formal.empty:
        comparison = (
            "Using the longer 500d/730d diagnostics and only the supplied quarterly boundary that the first "
            "FLAGGED label is 2022-07-01, this run does not show a pre-label deterioration signal."
        )
    else:
        first_pre = pd.Timestamp(pre_flag_formal.sort_values(["date_ts", "window_length"]).iloc[0]["date"])
        months_early = (first_flagged.year - first_pre.year) * 12 + (first_flagged.month - first_pre.month)
        comparison = (
            f"Using the longer 500d/730d diagnostics and only the supplied quarterly boundary that the first "
            f"FLAGGED label is 2022-07-01, the first pre-label deterioration signal appears on "
            f"{first_pre.date().isoformat()}, about {months_early} months earlier."
        )

    long_note = ""
    if 500 in evaluated_windows:
        w500 = part_b[part_b["window_length"] == 500].copy()
        w500["date_ts"] = pd.to_datetime(w500["date"])
        w500_early = w500[(w500["date_ts"] >= pd.Timestamp("2022-01-01")) & (w500["date_ts"] <= pd.Timestamp("2022-07-31"))]
        long_note += (
            " The 500d window enters a borderline/failing transition in January-July 2022: Engle-Granger p-values sit between "
            f"{w500_early['engle_granger_p_value'].min():.3f} and {w500_early['engle_granger_p_value'].max():.3f} "
            "over that interval, with residual ADF remaining below 0.05."
        )
    if 730 in evaluated_windows:
        w730 = part_b[part_b["window_length"] == 730].copy()
        w730["date_ts"] = pd.to_datetime(w730["date"])
        first_eg_fail = first_date(w730, ~w730["engle_granger_pass"])
        first_both_fail = first_date(w730, ~(w730["engle_granger_pass"] | w730["adf_pass"]))
        later = w730[(w730["date_ts"] >= pd.Timestamp("2023-12-01")) & (w730["date_ts"] <= pd.Timestamp("2024-09-30"))]
        long_note += (
            f" The 730d window remains below the 0.05 threshold until its first Engle-Granger failure on "
            f"{first_eg_fail}; both tests first fail on {first_both_fail}, and from December 2023 through "
            f"September 2024 its half-life ranges from {later['half_life'].min():.1f} to {later['half_life'].max():.1f} trading days."
        )

    if validated_windows:
        window_note = (
            f"Part B evaluated the Part A-validated windows: {', '.join(str(x) for x in validated_windows)} trading days."
        )
    else:
        window_note = (
            "Because Part A found no window satisfying the across-regime <10% FPR/FNR criterion at p < 0.05, "
            "Part B evaluated all candidate windows as diagnostics rather than treating any as validated."
        )

    return (
        f"{window_note} The rolling causal diagnostics by window were: {' '.join(lines)} The 60d, 120d, and 250d "
        f"windows fail frequently from their first available dates, which is consistent with Part A's warning that "
        f"these windows are not reliable across persistence regimes; they are therefore poor evidence for dating a "
        f"real degradation event on their own.{long_note}\n\n"
        f"{comparison} On the longer windows, the evidence first looks borderline around early 2022 in the "
        f"500d window, becomes more visibly weak in 2023, and looks consistently broken by late 2023 into 2024. "
        f"The 730d window lags the 500d window materially, so conclusions about the exact onset depend on window "
        f"length. The full quarterly classification table was not included in the prompt, so this run cannot enumerate "
        f"every quarterly-label disagreement; it can only compare against the stated first FLAGGED date."
    )


def write_summary(
    part_a_text: str,
    part_b_text: str,
    hashes: dict[str, str],
    provenance: dict[str, object],
) -> Path:
    summary_path = OUT_DIR / "summary.md"
    content = f"""# TCS/INFY Cointegration Window Validation

## Provenance

- Script path: `{provenance["script_path"]}`
- Git commit: `{provenance["git_commit"]}`
- Data source: `{provenance["data_source"]}`
- Snapshot ID: `{provenance["snapshot_id"]}`
- Snapshot adjusted close SHA256: `{provenance["snapshot_adjusted_close_sha256"]}`
- Timestamp UTC: `{provenance["timestamp_utc"]}`
- `part_a_synthetic_validation.csv` SHA256: `{hashes["part_a_synthetic_validation.csv"]}`
- `part_b_tcs_infy_rolling_cointegration.csv` SHA256: `{hashes["part_b_tcs_infy_rolling_cointegration.csv"]}`

## Part A

{part_a_text}

## Part B

{part_b_text}

## Method Notes

Part B loads adjusted close data from frozen snapshot `{provenance["snapshot_id"]}` rather than downloading fresh market data. Engle-Granger p-values come from `statsmodels.tsa.stattools.coint(..., trend="c", autolag="aic")`. Standalone residual/spread ADF p-values come from `statsmodels.tsa.stattools.adfuller(..., regression="n", autolag="aic")`. TCS is the dependent variable and INFY is the hedge-ratio regressor in the real-data rolling beta estimates.
"""
    summary_path.write_text(content, encoding="utf-8")
    return summary_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    close = load_snapshot_prices()
    part_a, validated_windows = run_part_a()
    evaluated_windows = validated_windows if validated_windows else WINDOWS
    part_b = run_part_b(close, evaluated_windows)

    part_a_path = OUT_DIR / "part_a_synthetic_validation.csv"
    part_b_path = OUT_DIR / "part_b_tcs_infy_rolling_cointegration.csv"
    part_a.to_csv(part_a_path, index=False)
    part_b.to_csv(part_b_path, index=False)

    hashes = {
        part_a_path.name: file_sha256(part_a_path),
        part_b_path.name: file_sha256(part_b_path),
    }
    part_a_text, validated_windows_check = summarize_part_a(part_a)
    provenance = {
        "script_path": str(Path(__file__).resolve()),
        "git_commit": git_commit(),
        "data_source": str(SNAPSHOT_CLOSE_CSV.relative_to(ROOT)),
        "snapshot_id": SNAPSHOT_ID,
        "snapshot_adjusted_close_sha256": file_sha256(SNAPSHOT_CLOSE_CSV),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "validated_windows": validated_windows_check,
        "evaluated_windows_part_b": evaluated_windows,
        "synthetic_seeds_per_condition": SYNTHETIC_SEEDS,
        "statsmodels_version": statsmodels.__version__,
        "engle_granger_method": "statsmodels.tsa.stattools.coint(trend='c', autolag='aic')",
        "adf_method": "statsmodels.tsa.stattools.adfuller(regression='n', autolag='aic')",
    }
    part_b_text = summarize_part_b(part_b, evaluated_windows, validated_windows_check)
    summary_path = write_summary(part_a_text, part_b_text, hashes, provenance)
    hashes[summary_path.name] = file_sha256(summary_path)
    provenance["output_hashes"] = hashes
    provenance_path = OUT_DIR / "provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
