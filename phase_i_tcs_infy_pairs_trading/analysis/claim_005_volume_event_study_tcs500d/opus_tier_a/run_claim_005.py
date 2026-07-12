"""
Opus Tier A independent reproduction -- claim_005_volume_event_study_tcs500d
Spec Block v2 (2026-07-12)

Question: Does TCS.NS exhibit statistically significant abnormal log trading
volume -- controlling for ^NSEI log volume and day-of-week effects -- in the
20 trading days immediately preceding 2021-12-31 (end of admitted 500d-core)?

Model:
  log(TCS_Volume_t) = a + b*log(NSEI_Volume_t) + DOW_dummies + g*EventWindow_t + e_t
  HC3 robust standard errors.  One-sided test: g > 0.

Outcome labels (from spec, used verbatim):
  REPRODUCED-ADJACENT-WINDOW -- both p<0.05, |g_A - g_B| <= 0.03, finite HC3 SE
  DISPUTED-BORDERLINE -- tolerance met, significance conclusions differ
  DISPUTED-VALUE -- coefficients disagree beyond tolerance
  Neither reaches p<0.05: does not reproduce (no special tag)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VENV_SITE = ROOT / ".venv" / "Lib" / "site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))

import numpy as np
import pandas as pd
import statsmodels.api as sm

# -- Constants ---------------------------------------------------------------
OUT_DIR = Path(__file__).resolve().parent

TCS_SNAPSHOT_ID = "tcs_infy_v2_2026-07-11"
TCS_SNAPSHOT_CSV = (
    ROOT / "data" / "snapshots" / TCS_SNAPSHOT_ID / "ohlcv.csv"
)
TCS_SNAPSHOT_SHA256 = (
    "28d1ef414f5973be6171649aebb0a2d3cf0dc3968564fc77961984b5b9c65ebd"
)

NSEI_SNAPSHOT_ID = "nifty_it_benchmark_v1_2026-07-11"
NSEI_SNAPSHOT_CSV = (
    ROOT / "data" / "snapshots" / NSEI_SNAPSHOT_ID / "ohlcv.csv"
)
NSEI_SNAPSHOT_SHA256 = (
    "fb842bcc8ed7dacf7533bc64789e0638181c8bc062095d92ae2154b53d9c542c"
)

DATA_FLOOR = "2018-09-06"
ESTIMATION_END = "2026-07-10"
ANCHOR_DATE = "2021-12-31"  # end of 500d_strict core (admitted)
EVENT_WINDOW_LEN = 20


# -- Utilities ---------------------------------------------------------------

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_commit() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        return r.stdout.strip()
    except Exception:
        return "unavailable"


def provenance_header_csv(meta: dict, content_sha: str) -> str:
    lines = [f"# {k}: {v}" for k, v in meta.items()]
    lines.append(f"# output_content_sha256: {content_sha}")
    return "\n".join(lines) + "\n"


def provenance_header_md(meta: dict, content_sha: str) -> str:
    lines = [f"{k}: {v}" for k, v in meta.items()]
    lines.append(f"output_content_sha256: {content_sha}")
    return "<!--\n" + "\n".join(lines) + "\n-->\n\n"


def write_csv(path: Path, df: pd.DataFrame, meta: dict) -> dict:
    body = df.to_csv(index=False, lineterminator="\n")
    content_sha = text_sha256(body)
    header = provenance_header_csv(meta, content_sha)
    path.write_text(header + body, encoding="utf-8", newline="\n")
    return {"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)}


def write_md(path: Path, body: str, meta: dict) -> dict:
    if not body.endswith("\n"):
        body += "\n"
    content_sha = text_sha256(body)
    header = provenance_header_md(meta, content_sha)
    path.write_text(header + body, encoding="utf-8", newline="\n")
    return {"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)}


# -- Data loading ------------------------------------------------------------

def load_tcs_volume() -> pd.DataFrame:
    sha = file_sha256(TCS_SNAPSHOT_CSV)
    if sha != TCS_SNAPSHOT_SHA256:
        raise RuntimeError(
            f"TCS snapshot SHA256 mismatch:\n  got  {sha}\n  want {TCS_SNAPSHOT_SHA256}"
        )
    df = pd.read_csv(TCS_SNAPSHOT_CSV, parse_dates=["date"])
    tcs = df[df["ticker"] == "TCS.NS"][["date", "volume"]].copy()
    tcs = tcs.rename(columns={"volume": "tcs_volume"})
    tcs = tcs.sort_values("date").reset_index(drop=True)
    return tcs


def load_nsei_volume() -> pd.DataFrame:
    sha = file_sha256(NSEI_SNAPSHOT_CSV)
    if sha != NSEI_SNAPSHOT_SHA256:
        raise RuntimeError(
            f"NSEI snapshot SHA256 mismatch:\n  got  {sha}\n  want {NSEI_SNAPSHOT_SHA256}"
        )
    df = pd.read_csv(NSEI_SNAPSHOT_CSV, parse_dates=["date"])
    nsei = df[df["ticker"] == "^NSEI"][["date", "volume"]].copy()
    nsei = nsei.rename(columns={"volume": "nsei_volume"})
    nsei = nsei.sort_values("date").reset_index(drop=True)
    return nsei


# -- Main --------------------------------------------------------------------

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    gh = git_commit()
    meta = {
        "script_path": str(Path(__file__).resolve()),
        "git_commit": gh,
        "tcs_snapshot_id": TCS_SNAPSHOT_ID,
        "nsei_snapshot_id": NSEI_SNAPSHOT_ID,
        "timestamp_utc": ts,
    }

    # ---- 1. Load data -----
    print("Loading TCS volume snapshot...")
    tcs = load_tcs_volume()
    print(f"  TCS.NS rows: {len(tcs)}, "
          f"{tcs['date'].min().date()} to {tcs['date'].max().date()}")

    print("Loading NSEI volume snapshot...")
    nsei = load_nsei_volume()
    print(f"  ^NSEI rows: {len(nsei)}, "
          f"{nsei['date'].min().date()} to {nsei['date'].max().date()}")

    # ---- 2. Data floor & merge -----
    tcs_pre_floor = len(tcs)
    tcs = tcs[tcs["date"] >= DATA_FLOOR].copy()
    tcs_floor_dropped = tcs_pre_floor - len(tcs)
    print(f"\nData floor {DATA_FLOOR}: dropped {tcs_floor_dropped} TCS rows, "
          f"{len(tcs)} remain")

    # Inner join
    tcs_dates = set(tcs["date"])
    nsei_dates = set(nsei["date"])
    tcs_only = tcs_dates - nsei_dates
    nsei_only = nsei_dates - tcs_dates

    merged = tcs.merge(nsei, on="date", how="inner").sort_values("date")
    merged = merged[merged["date"] <= ESTIMATION_END].reset_index(drop=True)

    # Also filter out any TCS-only or NSEI-only dates that are within
    # the estimation range for accurate reporting
    tcs_only_in_range = {d for d in tcs_only
                         if pd.Timestamp(DATA_FLOOR) <= d <= pd.Timestamp(ESTIMATION_END)}
    nsei_only_in_range = {d for d in nsei_only
                          if pd.Timestamp(DATA_FLOOR) <= d <= pd.Timestamp(ESTIMATION_END)}

    print(f"Inner join: {len(merged)} merged dates")
    print(f"  TCS-only dates dropped (in estimation range): {len(tcs_only_in_range)}")
    print(f"  NSEI-only dates dropped (in estimation range): {len(nsei_only_in_range)}")

    # ---- 3. Identify event window on FULL merged calendar (before dropping zeros) -----
    anchor = pd.Timestamp(ANCHOR_DATE)
    all_dates = merged["date"].sort_values().tolist()

    if anchor not in all_dates:
        candidates = [d for d in all_dates if d <= anchor]
        if not candidates:
            raise RuntimeError(f"No trading dates on or before {ANCHOR_DATE}")
        anchor_actual = candidates[-1]
        print(f"\nNote: {ANCHOR_DATE} not in trading calendar. "
              f"Using {anchor_actual.date()} as anchor.")
    else:
        anchor_actual = anchor

    anchor_idx = all_dates.index(anchor_actual)
    if anchor_idx < EVENT_WINDOW_LEN:
        raise RuntimeError(
            f"Not enough trading days before anchor: need {EVENT_WINDOW_LEN}, "
            f"have {anchor_idx}"
        )
    event_dates = all_dates[anchor_idx - EVENT_WINDOW_LEN : anchor_idx]
    assert len(event_dates) == EVENT_WINDOW_LEN, (
        f"Event window has {len(event_dates)} dates, expected {EVENT_WINDOW_LEN}"
    )

    merged["event_window"] = merged["date"].isin(event_dates).astype(int)

    print(f"\nEvent window ({EVENT_WINDOW_LEN} trading days before {ANCHOR_DATE}):")
    print(f"  Start: {event_dates[0].date()}")
    print(f"  End:   {event_dates[-1].date()}")
    print(f"  Count in merged data: {merged['event_window'].sum()}")

    # ---- 4. Drop zero-volume rows (AFTER event window is fixed) -----
    zero_mask = (merged["tcs_volume"] == 0) | (merged["nsei_volume"] == 0)
    zero_rows = merged[zero_mask].copy()
    n_zeros_dropped = len(zero_rows)
    zero_dates_dropped = sorted(zero_rows["date"].tolist())

    print(f"\nZero-volume rows dropped: {n_zeros_dropped}")
    for d in zero_dates_dropped:
        tcs_v = int(zero_rows[zero_rows["date"] == d]["tcs_volume"].iloc[0])
        nsei_v = int(zero_rows[zero_rows["date"] == d]["nsei_volume"].iloc[0])
        in_ew = "*EW*" if d in set(event_dates) else ""
        print(f"  {d.date()}  TCS_vol={tcs_v}  NSEI_vol={nsei_v}  {in_ew}")

    # Check if any zeros are in the event window
    ew_zeros = zero_rows[zero_rows["date"].isin(event_dates)]
    if len(ew_zeros) > 0:
        print(f"\n  WARNING: {len(ew_zeros)} zero-volume date(s) fall in the event window!")

    merged = merged[~zero_mask].reset_index(drop=True)
    n_after_zeros = len(merged)
    ew_after_zeros = int(merged["event_window"].sum())
    print(f"\nAfter dropping zeros: {n_after_zeros} observations, "
          f"{ew_after_zeros} in event window")

    # ---- 5. Log transform & features -----
    merged["log_tcs_vol"] = np.log(merged["tcs_volume"].astype(float))
    merged["log_nsei_vol"] = np.log(merged["nsei_volume"].astype(float))

    # Day-of-week dummies (Mon=0 ... Fri=4; drop Friday as reference)
    merged["dow"] = merged["date"].dt.dayofweek
    for i, name in enumerate(["mon", "tue", "wed", "thu"]):
        merged[name] = (merged["dow"] == i).astype(int)

    # ---- 6. Regression -----
    y = merged["log_tcs_vol"]
    X = merged[["log_nsei_vol", "mon", "tue", "wed", "thu", "event_window"]]
    X = sm.add_constant(X)

    model = sm.OLS(y, X)
    results = model.fit(cov_type="HC3")

    gamma = results.params["event_window"]
    gamma_se = results.bse["event_window"]
    gamma_t = results.tvalues["event_window"]
    gamma_p_twosided = results.pvalues["event_window"]

    # One-sided p-value: H1: gamma > 0
    if gamma > 0:
        gamma_p_onesided = gamma_p_twosided / 2
    else:
        gamma_p_onesided = 1 - gamma_p_twosided / 2

    # Check HC3 SE is finite
    se_finite = bool(np.isfinite(gamma_se))

    print(f"\n{'='*60}")
    print(f"REGRESSION RESULTS (HC3 robust SEs)")
    print(f"{'='*60}")
    print(f"  gamma (event_window coeff): {gamma:.6f}")
    print(f"  HC3 SE:                     {gamma_se:.6f}")
    print(f"  t-statistic:                {gamma_t:.4f}")
    print(f"  p-value (two-sided):        {gamma_p_twosided:.6f}")
    print(f"  p-value (one-sided, g>0):   {gamma_p_onesided:.6f}")
    print(f"  HC3 SE finite:              {se_finite}")
    print(f"  Significant (p<0.05, 1s):   {gamma_p_onesided < 0.05}")
    print(f"  N observations:             {results.nobs:.0f}")
    print(f"  R-squared:                  {results.rsquared:.4f}")
    print(f"{'='*60}")

    if not se_finite:
        print("\n*** INVALID: HC3 SE is non-finite. Diagnose before re-running. ***")

    # Full regression summary for reference
    print("\nFull model summary:")
    print(results.summary())

    # ---- 6. Write outputs -----
    print("\nWriting outputs...")
    output_hashes: dict[str, str] = {}

    # Data quality report
    quality_rows = [
        {"item": "tcs_snapshot_id", "value": TCS_SNAPSHOT_ID},
        {"item": "nsei_snapshot_id", "value": NSEI_SNAPSHOT_ID},
        {"item": "data_floor", "value": DATA_FLOOR},
        {"item": "estimation_end", "value": ESTIMATION_END},
        {"item": "tcs_rows_before_floor", "value": str(tcs_pre_floor)},
        {"item": "tcs_rows_dropped_by_floor", "value": str(tcs_floor_dropped)},
        {"item": "tcs_only_dates_dropped", "value": str(len(tcs_only_in_range))},
        {"item": "nsei_only_dates_dropped", "value": str(len(nsei_only_in_range))},
        {"item": "merged_before_zero_drop", "value": str(n_after_zeros + n_zeros_dropped)},
        {"item": "zero_volume_rows_dropped", "value": str(n_zeros_dropped)},
        {"item": "zero_volume_dates_dropped",
         "value": ",".join(d.date().isoformat() for d in zero_dates_dropped)},
        {"item": "zero_volume_in_event_window", "value": str(len(ew_zeros))},
        {"item": "regression_observation_count", "value": str(n_after_zeros)},
        {"item": "event_window_observations", "value": str(ew_after_zeros)},
        {"item": "anchor_date", "value": ANCHOR_DATE},
        {"item": "event_window_start", "value": str(event_dates[0].date())},
        {"item": "event_window_end", "value": str(event_dates[-1].date())},
        {"item": "event_window_count", "value": str(EVENT_WINDOW_LEN)},
        {"item": "log_base", "value": "natural_log"},
    ]
    h = write_csv(
        OUT_DIR / "data_quality_report.csv",
        pd.DataFrame(quality_rows), meta,
    )
    output_hashes["data_quality_report.csv"] = h["sha256"]

    # Event window dates
    ew_df = pd.DataFrame({
        "date": [d.date().isoformat() for d in event_dates],
        "position": list(range(-EVENT_WINDOW_LEN, 0)),
    })
    h = write_csv(OUT_DIR / "event_window_dates.csv", ew_df, meta)
    output_hashes["event_window_dates.csv"] = h["sha256"]

    # Dropped zero-volume dates (explicit list for cross-implementation check)
    dropped_rows = []
    for d in zero_dates_dropped:
        row = zero_rows[zero_rows["date"] == d].iloc[0]
        dropped_rows.append({
            "date": d.date().isoformat(),
            "tcs_volume": int(row["tcs_volume"]),
            "nsei_volume": int(row["nsei_volume"]),
            "in_event_window": d in set(event_dates),
        })
    dropped_df = pd.DataFrame(dropped_rows)
    h = write_csv(OUT_DIR / "dropped_zero_volume_dates.csv", dropped_df, meta)
    output_hashes["dropped_zero_volume_dates.csv"] = h["sha256"]

    # Regression results (all coefficients)
    reg_rows = []
    for var in results.params.index:
        reg_rows.append({
            "variable": var,
            "coefficient": results.params[var],
            "hc3_se": results.bse[var],
            "t_statistic": results.tvalues[var],
            "p_value_twosided": results.pvalues[var],
        })
    # Add one-sided p for event_window
    reg_df = pd.DataFrame(reg_rows)
    reg_df["p_value_onesided_gt0"] = np.nan
    mask = reg_df["variable"] == "event_window"
    reg_df.loc[mask, "p_value_onesided_gt0"] = gamma_p_onesided

    # Add model-level stats
    model_stats_df = pd.DataFrame([{
        "variable": "_n_obs",
        "coefficient": results.nobs,
    }, {
        "variable": "_r_squared",
        "coefficient": results.rsquared,
    }, {
        "variable": "_r_squared_adj",
        "coefficient": results.rsquared_adj,
    }])
    reg_df = pd.concat([reg_df, model_stats_df], ignore_index=True)

    h = write_csv(OUT_DIR / "regression_results.csv", reg_df, meta)
    output_hashes["regression_results.csv"] = h["sha256"]

    # Summary
    sig_label = "significant" if gamma_p_onesided < 0.05 else "not significant"
    summary_body = f"""# Volume Event Study -- TCS.NS 500d-Core Boundary (Opus Tier A)

## Result

- **gamma (event window coefficient):** {gamma:.6f}
- **HC3 standard error:** {gamma_se:.6f}
- **t-statistic:** {gamma_t:.4f}
- **p-value (one-sided, H1: gamma > 0):** {gamma_p_onesided:.6f}
- **Conclusion:** {sig_label} at the 0.05 level

## Outcome Label

If the paired reproduction (Codex Tier A) also finds p < 0.05 one-sided,
|gamma_A - gamma_B| <= 0.03, and both report finite HC3 SE, the verdict is:

**REPRODUCED-ADJACENT-WINDOW**

This exact label is deliberate and permanent. It is NOT equivalent to plain
"REPRODUCED." See Required Limitation below.

Other possible outcomes:
- **DISPUTED-BORDERLINE** -- tolerance met, significance conclusions differ
- **DISPUTED-VALUE** -- coefficients disagree beyond tolerance (|gamma_A - gamma_B| > 0.03)
- Neither reproduction reaches p < 0.05: claim does not reproduce (no special tag)

## Required Limitation

This claim tests a window anchored to claim_002's admitted healthy-core
boundary (2021-12-31), not the window explored in the prior Tier B pass
(2022-01-31, an unadmitted date -- see open_questions.md #18, still open).
The two prior exploratory runs that motivated this Tier A escalation tested
a different window and do not constitute prior replication of this specific
result. The window was selected because a nearby window showed a strong
result in that unadmitted exploratory pass -- readers should weight a bare
p < 0.05 pass here accordingly, not as equivalent evidence to a
pre-registered blind test.

This spec tests exactly one window definition (20 trading days, anchored to
end-of-day 2021-12-31, i.e. [-20,-1] trading days). Alternative nearby
specifications -- 15 or 25 trading days, or anchoring one day earlier/later
-- were not tested and must not be assumed to produce the same result.
Testing alternatives here would reopen the exact multiple-comparisons
problem this claim was rewritten to avoid, so none were tried; this is a
deliberate scope limit, not an oversight.

## Data Quality

- **Merged sample (before zero-drop):** {n_after_zeros + n_zeros_dropped} observations
- **Zero-volume rows dropped:** {n_zeros_dropped} (dates: {', '.join(d.date().isoformat() for d in zero_dates_dropped)})
- **Zero-volume dates in event window:** {len(ew_zeros)}
- **Regression sample:** {DATA_FLOOR} to {ESTIMATION_END} ({int(results.nobs)} observations)
- **TCS-only dates dropped (in range):** {len(tcs_only_in_range)}
- **NSEI-only dates dropped (in range):** {len(nsei_only_in_range)}
- **Event window observations in regression:** {ew_after_zeros}
- **Log base:** natural log (ln)

## Event Window

{EVENT_WINDOW_LEN} trading days at positions [-20, -1] before {ANCHOR_DATE}:
- Start: {event_dates[0].date()}
- End: {event_dates[-1].date()}

## Model

```
log(TCS_Volume_t) = a + b*log(NSEI_Volume_t) + DOW_dummies + g*EventWindow_t + e_t
```

HC3 robust standard errors. Day-of-week dummies: Mon-Thu (Friday = reference).
One-sided test: H1: gamma > 0.

## Non-goals

Does not confirm or deny the original Tier B finding (window before
2022-01-31) -- that remains open, tracked separately. Does not re-test
730d or INFY. Does not test window-length sensitivity.
"""

    h = write_md(OUT_DIR / "summary.md", summary_body, meta)
    output_hashes["summary.md"] = h["sha256"]

    # Provenance JSON
    provenance = {
        "tcs_snapshot_id": TCS_SNAPSHOT_ID,
        "tcs_snapshot_sha256": TCS_SNAPSHOT_SHA256,
        "nsei_snapshot_id": NSEI_SNAPSHOT_ID,
        "nsei_snapshot_sha256": NSEI_SNAPSHOT_SHA256,
        "git_commit": gh,
        "script_path": str(
            Path(__file__).resolve().relative_to(ROOT)
        ),
        "execution_timestamp_utc": ts,
        "python_version": sys.version,
        "statsmodels_version": sm.__version__ if hasattr(sm, "__version__") else "unknown",
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "method_notes": {
            "log_base": "natural_log",
            "robust_se": "HC3",
            "test_direction": "one_sided_gamma_gt_0",
            "dow_reference": "Friday",
            "event_window": f"[-{EVENT_WINDOW_LEN}, -1] trading days before {ANCHOR_DATE}",
            "data_floor": DATA_FLOOR,
        },
        "results": {
            "gamma": float(gamma),
            "gamma_hc3_se": float(gamma_se),
            "gamma_t_stat": float(gamma_t),
            "p_value_twosided": float(gamma_p_twosided),
            "p_value_onesided": float(gamma_p_onesided),
            "hc3_se_finite": se_finite,
            "n_obs": int(results.nobs),
            "r_squared": float(results.rsquared),
        },
        "output_sha256": output_hashes,
    }
    prov_path = OUT_DIR / "provenance.json"
    prov_path.write_text(
        json.dumps(provenance, indent=2), encoding="utf-8",
    )

    print(f"\nAll outputs written to {OUT_DIR.relative_to(ROOT)}/")
    for fname, sha in output_hashes.items():
        print(f"  {fname}: {sha[:16]}...")
    print("\nDone.")


if __name__ == "__main__":
    main()
