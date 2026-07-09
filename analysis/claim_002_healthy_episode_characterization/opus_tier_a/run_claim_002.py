"""
Opus Tier A independent reproduction — claim_002_healthy_episode_characterization
Spec Block v3 + Addendum (2026-07-09)

Implements all four parts:
  Part 1: Boundary identification (§2)
  Part 2: Regime characterization (§3)
  Part 3: Homogeneity / sub-regime test (§4)
  Part 4: Degradation diagnostics (§5)

Rolling metrics computed per §1.

Methodology reference: characterize_episode_1.py (isolation carve-out).
Snapshot: tcs_infy_v1_2026-07-04
Z-scoring ddof: 1 (addendum item 3 — cancels in rss_improvement_ratio)
P-value floor: 1e-300 (addendum item 4 — clip before -log10)
First-half convention: first max(1, n // 2) observations (addendum item 2)
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VENV_SITE = ROOT / ".venv" / "Lib" / "site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))

import numpy as np
import pandas as pd
import statsmodels
from statsmodels.tsa.stattools import adfuller, coint

# ── Constants (from Spec Block v3) ──────────────────────────────────────────
OUT_DIR = Path(__file__).resolve().parent
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
SNAPSHOT_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
SNAPSHOT_METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
EXPECTED_SNAPSHOT_SHA256 = (
    "7f2b69cc3c2030bb10c6e7a6f9a727743bff8d7003f7db2f36fa3661bbd60959"
)

WINDOWS = [60, 120, 250, 500, 730]
P_STRICT = 0.05
P_BORDERLINE = 0.10
MIN_SUSTAINED = 6
N_PERM = 2000
RNG_SEED = 20260705
P_FLOOR = 1e-300  # addendum item 4

# Fixed Inputs (hardcoded from spec — not derived from own Part 1)
FI_500_START = "2020-01-31"
FI_500_END = "2021-12-31"
FI_730_START = "2020-12-31"
FI_730_END = "2023-03-31"
SHOULDER_END = "2023-01-31"


# ── Utility functions ───────────────────────────────────────────────────────

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
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
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


# ── Data loading ────────────────────────────────────────────────────────────

def load_snapshot() -> tuple[pd.DataFrame, dict]:
    actual_sha = file_sha256(SNAPSHOT_CLOSE_CSV)
    if actual_sha != EXPECTED_SNAPSHOT_SHA256:
        raise RuntimeError(
            f"Snapshot SHA256 mismatch:\n  got  {actual_sha}\n  want {EXPECTED_SNAPSHOT_SHA256}"
        )
    snap_meta = json.loads(SNAPSHOT_METADATA_JSON.read_text(encoding="utf-8"))
    close = pd.read_csv(SNAPSHOT_CLOSE_CSV, parse_dates=["date"]).set_index("date")
    close = close[["TCS.NS", "INFY.NS"]].dropna()
    if close.empty:
        raise RuntimeError("Snapshot empty after dropping NaN rows")
    return close, snap_meta


# ── §1: Rolling metrics ────────────────────────────────────────────────────

def ols_with_intercept(
    y: np.ndarray, x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """OLS of y on [1, x].  Returns (coefficients, residuals)."""
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return beta, resid


def eg_pvalue(y: np.ndarray, x: np.ndarray) -> float:
    try:
        _, p, _ = coint(y, x, trend="c", autolag="aic")
        return float(p)
    except Exception:
        return float("nan")


def adf_pvalue(resid: np.ndarray) -> float:
    vals = resid[np.isfinite(resid)]
    if len(vals) < 12:
        return float("nan")
    try:
        return float(adfuller(vals, regression="n", autolag="aic")[1])
    except Exception:
        return float("nan")


def ar1_phi(resid: np.ndarray) -> float:
    if len(resid) < 4:
        return float("nan")
    beta, _ = ols_with_intercept(resid[1:], resid[:-1])
    return float(beta[1])


def half_life_from_phi(phi: float) -> float:
    if not np.isfinite(phi) or phi <= 0:
        return float("nan")
    if phi >= 1:
        return float("inf")
    return -math.log(2) / math.log(phi)


def month_end_dates(idx: pd.DatetimeIndex) -> list[pd.Timestamp]:
    s = pd.Series(idx, index=idx)
    return list(s.groupby(s.index.to_period("M")).max())


def compute_rolling_metrics(close: pd.DataFrame) -> pd.DataFrame:
    logs = np.log(close)
    me_dates = month_end_dates(logs.index)
    rows: list[dict] = []
    for n in WINDOWS:
        for d in me_dates:
            window = logs.loc[:d].tail(n)
            if len(window) < n:
                continue
            y = window["TCS.NS"].to_numpy()
            x = window["INFY.NS"].to_numpy()
            beta_coeff, resid = ols_with_intercept(y, x)
            b = float(beta_coeff[1])
            eg = eg_pvalue(y, x)
            adf = adf_pvalue(resid)
            phi = ar1_phi(resid)
            hl = half_life_from_phi(phi)
            s_std = float(np.std(resid, ddof=1))
            sd_std = float(np.std(np.diff(resid), ddof=1))
            sp = bool(eg < P_STRICT and adf < P_STRICT)
            bp = bool(eg < P_BORDERLINE and adf < P_STRICT)
            rows.append({
                "date": d.strftime("%Y-%m-%d"),
                "window_length": n,
                "beta": b,
                "eg_p": eg,
                "adf_p": adf,
                "spread_phi": phi,
                "half_life": hl,
                "spread_std": s_std,
                "spread_daily_change_std": sd_std,
                "strict_pass": sp,
                "borderline_pass": bp,
            })
    return pd.DataFrame(rows)


# ── §2: Boundary candidates ────────────────────────────────────────────────

def find_runs(
    passing_dates: list[str], all_me_dates: list[str],
) -> list[list[str]]:
    """Find runs of consecutive month-ends in `passing_dates`, where
    'consecutive' means adjacent in `all_me_dates`."""
    pset = set(passing_dates)
    runs: list[list[str]] = []
    current: list[str] = []
    for d in all_me_dates:
        if d in pset:
            current.append(d)
        else:
            if current:
                runs.append(current)
                current = []
    if current:
        runs.append(current)
    return runs


def select_best_run(runs: list[list[str]]) -> dict:
    """Keep runs ≥ MIN_SUSTAINED, select latest-ending (ties: largest count)."""
    qualifying = [r for r in runs if len(r) >= MIN_SUSTAINED]
    if not qualifying:
        return {
            "status": "no_sustained_run",
            "start_date": "",
            "end_date": "",
            "month_end_count": 0,
        }
    qualifying.sort(key=lambda r: (r[-1], len(r)))
    best = qualifying[-1]
    return {
        "status": "sustained_run",
        "start_date": best[0],
        "end_date": best[-1],
        "month_end_count": len(best),
    }


def find_boundary_candidates(rolling: pd.DataFrame) -> pd.DataFrame:
    w500 = rolling[rolling["window_length"] == 500].sort_values("date")
    w730 = rolling[rolling["window_length"] == 730].sort_values("date")
    all_500 = w500["date"].tolist()
    all_730 = w730["date"].tolist()

    # 500d_strict
    pass_500s = w500[w500["strict_pass"]]["date"].tolist()
    res_500s = select_best_run(find_runs(pass_500s, all_500))
    res_500s["candidate_name"] = "500d_strict"

    # 730d_strict
    pass_730s = w730[w730["strict_pass"]]["date"].tolist()
    res_730s = select_best_run(find_runs(pass_730s, all_730))
    res_730s["candidate_name"] = "730d_strict"

    # 500d_730d_consensus_strict  (inner join on date)
    merged = w500.merge(w730, on="date", suffixes=("_500", "_730"))
    all_cons = sorted(merged["date"].tolist())
    pass_cons = merged[
        merged["strict_pass_500"] & merged["strict_pass_730"]
    ]["date"].tolist()
    res_cons = select_best_run(find_runs(pass_cons, all_cons))
    res_cons["candidate_name"] = "500d_730d_consensus_strict"

    # 500d_borderline_tolerant
    pass_500bl = w500[w500["borderline_pass"]]["date"].tolist()
    res_500bl = select_best_run(find_runs(pass_500bl, all_500))
    res_500bl["candidate_name"] = "500d_borderline_tolerant"

    candidates = pd.DataFrame([res_500s, res_730s, res_cons, res_500bl])
    return candidates[
        ["candidate_name", "start_date", "end_date", "month_end_count", "status"]
    ]


# ── §3: Regime summary ─────────────────────────────────────────────────────

REGIME_METRICS = [
    "beta", "half_life", "spread_phi", "eg_p", "adf_p",
    "spread_std", "spread_daily_change_std",
]


def compute_12_stats(values: np.ndarray) -> dict:
    n = len(values)
    nan = float("nan")
    if n == 0:
        return {k: nan for k in [
            "mean", "std", "min", "q25", "median", "q75", "max",
            "start", "end", "end_minus_start", "slope_per_month",
            "median_absolute_monthly_change",
        ]}
    v = pd.Series(values)
    slope = (
        float(np.polyfit(np.arange(n, dtype=float), values, 1)[0])
        if n >= 2 else nan
    )
    mac = float(v.diff().abs().median()) if n >= 2 else nan
    return {
        "mean": float(v.mean()),
        "std": float(v.std(ddof=1)) if n > 1 else 0.0,
        "min": float(v.min()),
        "q25": float(v.quantile(0.25)),
        "median": float(v.median()),
        "q75": float(v.quantile(0.75)),
        "max": float(v.max()),
        "start": float(v.iloc[0]),
        "end": float(v.iloc[-1]),
        "end_minus_start": float(v.iloc[-1] - v.iloc[0]),
        "slope_per_month": slope,
        "median_absolute_monthly_change": mac,
    }


def compute_regime_summary(rolling: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for base, wl, start, end in [
        ("500d_strict", 500, FI_500_START, FI_500_END),
        ("730d_strict", 730, FI_730_START, FI_730_END),
    ]:
        subset = rolling[
            (rolling["window_length"] == wl)
            & (rolling["date"] >= start)
            & (rolling["date"] <= end)
        ].sort_values("date")
        for metric in REGIME_METRICS:
            vals = (
                pd.to_numeric(subset[metric], errors="coerce")
                .replace([np.inf, -np.inf], np.nan)
                .dropna()
                .to_numpy()
            )
            stats = compute_12_stats(vals)
            stats["window_base"] = base
            stats["metric"] = metric
            rows.append(stats)
    cols = [
        "window_base", "metric", "mean", "std", "min", "q25", "median",
        "q75", "max", "start", "end", "end_minus_start", "slope_per_month",
        "median_absolute_monthly_change",
    ]
    return pd.DataFrame(rows)[cols]


# ── §4: Sub-regime test ────────────────────────────────────────────────────

SUBREGIME_METRICS = [
    "beta", "half_life", "spread_std", "spread_daily_change_std",
    "neg_log10_eg_p", "neg_log10_adf_p",
]


def build_standardized_matrix(
    subset: pd.DataFrame,
) -> tuple[np.ndarray, list[str]]:
    """Z-score 6 metrics after linear interpolation.  ddof=1."""
    cols: list[np.ndarray] = []
    names: list[str] = []
    for metric in SUBREGIME_METRICS:
        if metric == "neg_log10_eg_p":
            s = -np.log10(subset["eg_p"].clip(lower=P_FLOOR))
        elif metric == "neg_log10_adf_p":
            s = -np.log10(subset["adf_p"].clip(lower=P_FLOOR))
        else:
            s = pd.to_numeric(subset[metric], errors="coerce")
        s = s.replace([np.inf, -np.inf], np.nan)
        if s.notna().sum() < 3:
            continue
        filled = s.interpolate(limit_direction="both")
        std = float(filled.std(ddof=1))
        if not np.isfinite(std) or std == 0:
            continue
        cols.append(((filled - filled.mean()) / std).to_numpy())
        names.append(metric)
    if not cols:
        return np.empty((len(subset), 0)), []
    return np.column_stack(cols), names


def split_rss(matrix: np.ndarray, k: int) -> float:
    left = matrix[:k]
    right = matrix[k:]
    return float(
        ((left - left.mean(axis=0)) ** 2).sum()
        + ((right - right.mean(axis=0)) ** 2).sum()
    )


def total_rss(matrix: np.ndarray) -> float:
    return float(((matrix - matrix.mean(axis=0)) ** 2).sum())


def run_subregime_tests(rolling: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    rows: list[dict] = []

    # Process 500d_strict FIRST, then 730d_strict  (RNG call order per spec)
    for base, wl, start, end in [
        ("500d_strict", 500, FI_500_START, FI_500_END),
        ("730d_strict", 730, FI_730_START, FI_730_END),
    ]:
        subset = rolling[
            (rolling["window_length"] == wl)
            & (rolling["date"] >= start)
            & (rolling["date"] <= end)
        ].sort_values("date").reset_index(drop=True)

        n = len(subset)
        matrix, used_metrics = build_standardized_matrix(subset)
        min_seg = min(6, max(3, n // 4))
        dates = subset["date"].tolist()

        if n < min_seg * 2 or matrix.shape[1] == 0:
            rows.append({
                "window_base": base,
                "n_observations": n,
                "min_seg": min_seg,
                "best_split_index": -1,
                "best_split_after_date": "",
                "left_end": "",
                "right_start": "",
                "metrics_used": ",".join(used_metrics),
                "rss_improvement_ratio": float("nan"),
                "n_permutations": N_PERM,
                "permutation_p_value": float("nan"),
                "interpretation": "insufficient_data",
            })
            continue

        t_rss = total_rss(matrix)
        candidates = list(range(min_seg, n - min_seg + 1))

        # Find best split
        best_k = min(candidates, key=lambda k: split_rss(matrix, k))
        best_rss_val = split_rss(matrix, best_k)
        improvement = (
            1.0 - best_rss_val / t_rss if t_rss > 0 else float("nan")
        )

        # Permutation test
        count_ge = 0
        for _ in range(N_PERM):
            perm = matrix[rng.permutation(n)]
            perm_t = total_rss(perm)
            perm_best = min(split_rss(perm, k) for k in candidates)
            perm_imp = (
                1.0 - perm_best / perm_t if perm_t > 0 else 0.0
            )
            if perm_imp >= improvement:
                count_ge += 1
        p_val = (count_ge + 1) / (N_PERM + 1)

        interp = (
            "natural_split_supported"
            if p_val < 0.05 and improvement >= 0.25
            else "no_clear_split"
        )

        rows.append({
            "window_base": base,
            "n_observations": n,
            "min_seg": min_seg,
            "best_split_index": best_k,
            "best_split_after_date": dates[best_k - 1],
            "left_end": dates[best_k - 1],
            "right_start": dates[best_k],
            "metrics_used": ",".join(used_metrics),
            "rss_improvement_ratio": float(improvement),
            "n_permutations": N_PERM,
            "permutation_p_value": float(p_val),
            "interpretation": interp,
        })

    return pd.DataFrame(rows)


# ── §5: Degradation diagnostics ────────────────────────────────────────────

DEGRAD_METRICS = [
    "beta", "half_life", "eg_p", "adf_p",
    "spread_std", "spread_daily_change_std",
]


def compute_trend_stats(values: np.ndarray) -> dict:
    n = len(values)
    nan = float("nan")
    if n == 0:
        return {k: nan for k in [
            "start", "end", "end_minus_start", "slope_per_month",
            "first_half_mean", "second_half_mean",
        ]}
    slope = (
        float(np.polyfit(np.arange(n, dtype=float), values, 1)[0])
        if n >= 2 else nan
    )
    # Addendum item 2: first half = first max(1, n // 2), second = remainder
    split = max(1, n // 2)
    return {
        "start": float(values[0]),
        "end": float(values[-1]),
        "end_minus_start": float(values[-1] - values[0]),
        "slope_per_month": slope,
        "first_half_mean": float(values[:split].mean()),
        "second_half_mean": (
            float(values[split:].mean()) if n > 1 else nan
        ),
    }


def compute_degradation(rolling: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    specs = [
        ("500d_strict", 500, FI_500_START, FI_500_END),
        ("730d_strict", 730, FI_730_START, FI_730_END),
        ("shoulder", 500, None, None),
    ]
    for label, wl, start, end in specs:
        if label == "shoulder":
            # Dates strictly after 500d_strict end, up to shoulder cutoff
            subset = rolling[
                (rolling["window_length"] == wl)
                & (rolling["date"] > FI_500_END)
                & (rolling["date"] <= SHOULDER_END)
            ].sort_values("date")
        else:
            subset = rolling[
                (rolling["window_length"] == wl)
                & (rolling["date"] >= start)
                & (rolling["date"] <= end)
            ].sort_values("date")
        for metric in DEGRAD_METRICS:
            vals = (
                pd.to_numeric(subset[metric], errors="coerce")
                .replace([np.inf, -np.inf], np.nan)
                .dropna()
                .to_numpy()
            )
            stats = compute_trend_stats(vals)
            stats["window"] = label
            stats["metric"] = metric
            rows.append(stats)
    cols = [
        "window", "metric", "start", "end", "end_minus_start",
        "slope_per_month", "first_half_mean", "second_half_mean",
    ]
    return pd.DataFrame(rows)[cols]


# ── Summary ─────────────────────────────────────────────────────────────────

def build_summary(
    candidates: pd.DataFrame,
    regime: pd.DataFrame,
    subregimes: pd.DataFrame,
    degradation: pd.DataFrame,
    snap_meta: dict,
    output_hashes: dict,
) -> str:
    c = candidates.set_index("candidate_name")

    def rl(base: str, metric: str) -> pd.Series:
        row = regime[
            (regime["window_base"] == base) & (regime["metric"] == metric)
        ]
        return row.iloc[0] if not row.empty else pd.Series(dtype=float)

    b500 = rl("500d_strict", "beta")
    hl500 = rl("500d_strict", "half_life")
    eg500 = rl("500d_strict", "eg_p")
    adf500 = rl("500d_strict", "adf_p")
    sp500 = rl("500d_strict", "spread_std")

    body = f"""# Healthy Episode Characterization — TCS/INFY (Opus Tier A)

## Inputs

- **Snapshot:** `{SNAPSHOT_ID}`
- **Date range:** {snap_meta.get('first_data_date', 'N/A')} to {snap_meta.get('last_data_date', 'N/A')}
- **Rolling windows:** {', '.join(str(w) for w in WINDOWS)} trading days
- **Method:** Log adjusted closes; TCS.NS dependent, INFY.NS regressor; OLS with intercept
- **Cointegration:** `coint(trend="c", autolag="aic")`; ADF: `adfuller(regression="n", autolag="aic")`
- **Z-scoring ddof:** 1 (addendum item 3 — cancels in RSS ratio)
- **P-value floor:** {P_FLOOR} (addendum item 4 — clip before -log10)

## Part 1 — Episode Boundaries

| Candidate | Start | End | Month-ends | Status |
|-----------|-------|-----|------------|--------|
"""
    for _, row in candidates.iterrows():
        body += (
            f"| {row['candidate_name']} | {row['start_date']} "
            f"| {row['end_date']} | {row['month_end_count']} "
            f"| {row['status']} |\n"
        )

    fi_500_match = (
        c.loc["500d_strict", "start_date"] == FI_500_START
        and c.loc["500d_strict", "end_date"] == FI_500_END
    )
    fi_730_match = (
        c.loc["730d_strict", "start_date"] == FI_730_START
        and c.loc["730d_strict", "end_date"] == FI_730_END
    )
    body += f"""
### Fixed Input verification

- `500d_strict`: spec says {FI_500_START} to {FI_500_END} -> computed {'[OK] MATCH' if fi_500_match else '[FAIL] MISMATCH'}
- `730d_strict`: spec says {FI_730_START} to {FI_730_END} -> computed {'[OK] MATCH' if fi_730_match else '[FAIL] MISMATCH'}

## Part 2 — Regime Characterization

Full distributional statistics in `episode_regime_summary.csv`.  Key highlights for 500d_strict core:

- **Beta:** mean {b500['mean']:.4f}, std {b500['std']:.4f}, range [{b500['min']:.4f}, {b500['max']:.4f}]
- **Half-life:** mean {hl500['mean']:.1f}, median {hl500['median']:.1f} trading days, range [{hl500['min']:.1f}, {hl500['max']:.1f}]
- **EG p-value:** median {eg500['median']:.6f}, range [{eg500['min']:.6f}, {eg500['max']:.6f}]
- **ADF p-value:** median {adf500['median']:.6f}, range [{adf500['min']:.6f}, {adf500['max']:.6f}]
- **Spread volatility:** median {sp500['median']:.6f}

## Part 3 — Sub-regime Test
"""
    for _, sr in subregimes.iterrows():
        body += (
            f"\n- **{sr['window_base']}:** best split after "
            f"{sr['best_split_after_date']}, RSS improvement = "
            f"{sr['rss_improvement_ratio']:.4f}, permutation p = "
            f"{sr['permutation_p_value']:.4f} → {sr['interpretation']}"
        )

    body += f"""

## Part 4 — Degradation Diagnostics

Numbers-only output in `degradation_diagnostics.csv`.
Descriptive reconstruction only — no RL recommendations, no training-window selection, no claim of 'failure.'

## Output Hashes
"""
    for fname, sha in output_hashes.items():
        if fname != "summary.md":
            body += f"\n- `{fname}`: `{sha}`"

    body += "\n"
    return body


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    gh = git_commit()
    meta = {
        "script_path": str(Path(__file__).resolve()),
        "git_commit": gh,
        "snapshot_id": SNAPSHOT_ID,
        "timestamp_utc": ts,
    }

    # ── Load ────────────────────────────────────────────────────────────
    print("Loading snapshot...")
    close, snap_meta = load_snapshot()
    print(
        f"  {len(close)} trading days, "
        f"{close.index[0].date()} to {close.index[-1].date()}"
    )

    # ── §1: Rolling metrics ────────────────────────────────────────────
    print("Computing rolling metrics (§1)...")
    rolling = compute_rolling_metrics(close)
    print(f"  {len(rolling)} rows across {len(WINDOWS)} windows")

    # ── §2: Boundary candidates ────────────────────────────────────────
    print("Finding boundary candidates (§2)...")
    candidates = find_boundary_candidates(rolling)
    print(candidates.to_string(index=False))

    # Verify Part 1 against Fixed Inputs
    c500 = candidates[candidates["candidate_name"] == "500d_strict"].iloc[0]
    c730 = candidates[candidates["candidate_name"] == "730d_strict"].iloc[0]
    assert c500["start_date"] == FI_500_START, (
        f"500d start mismatch: {c500['start_date']} != {FI_500_START}"
    )
    assert c500["end_date"] == FI_500_END, (
        f"500d end mismatch: {c500['end_date']} != {FI_500_END}"
    )
    assert c730["start_date"] == FI_730_START, (
        f"730d start mismatch: {c730['start_date']} != {FI_730_START}"
    )
    assert c730["end_date"] == FI_730_END, (
        f"730d end mismatch: {c730['end_date']} != {FI_730_END}"
    )
    print("  [OK] Part 1 boundaries match Fixed Inputs")

    # ── §3: Regime summary ─────────────────────────────────────────────
    print("Computing regime summary (§3)...")
    regime = compute_regime_summary(rolling)
    print(f"  {len(regime)} rows (2 windows × 7 metrics)")

    # ── §4: Sub-regime tests ───────────────────────────────────────────
    print("Running sub-regime tests (§4)...")
    subregimes = run_subregime_tests(rolling)
    print(
        subregimes[
            ["window_base", "rss_improvement_ratio",
             "permutation_p_value", "interpretation"]
        ].to_string(index=False)
    )

    # ── §5: Degradation diagnostics ────────────────────────────────────
    print("Computing degradation diagnostics (§5)...")
    degradation = compute_degradation(rolling)
    print(f"  {len(degradation)} rows (3 windows × 6 metrics)")

    # ── Write outputs ──────────────────────────────────────────────────
    print("\nWriting outputs...")
    output_hashes: dict[str, str] = {}

    h = write_csv(OUT_DIR / "rolling_metrics.csv", rolling, meta)
    output_hashes["rolling_metrics.csv"] = h["sha256"]

    h = write_csv(
        OUT_DIR / "episode_boundary_candidates.csv", candidates, meta,
    )
    output_hashes["episode_boundary_candidates.csv"] = h["sha256"]

    h = write_csv(OUT_DIR / "episode_regime_summary.csv", regime, meta)
    output_hashes["episode_regime_summary.csv"] = h["sha256"]

    h = write_csv(OUT_DIR / "subregime_tests.csv", subregimes, meta)
    output_hashes["subregime_tests.csv"] = h["sha256"]

    h = write_csv(
        OUT_DIR / "degradation_diagnostics.csv", degradation, meta,
    )
    output_hashes["degradation_diagnostics.csv"] = h["sha256"]

    # Summary (provenance header written by the script itself)
    summary_body = build_summary(
        candidates, regime, subregimes, degradation, snap_meta, output_hashes,
    )
    h = write_md(OUT_DIR / "summary.md", summary_body, meta)
    output_hashes["summary.md"] = h["sha256"]

    # Provenance JSON
    provenance = {
        "snapshot_id": SNAPSHOT_ID,
        "snapshot_sha256": EXPECTED_SNAPSHOT_SHA256,
        "git_commit": gh,
        "script_path": str(
            Path(__file__).resolve().relative_to(ROOT)
        ),
        "execution_timestamp_utc": ts,
        "python_version": sys.version,
        "statsmodels_version": statsmodels.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "method_notes": {
            "z_scoring_ddof": 1,
            "p_value_floor_for_neg_log10": P_FLOOR,
            "rng_seed": RNG_SEED,
            "n_permutations": N_PERM,
            "rng_call_order": "500d_strict then 730d_strict",
            "first_half_convention": "first max(1, n // 2) observations",
            "split_candidate_range": "range(min_seg, n - min_seg + 1)",
        },
        "output_sha256": output_hashes,
    }
    prov_path = OUT_DIR / "provenance.json"
    prov_path.write_text(
        json.dumps(provenance, indent=2), encoding="utf-8",
    )

    print(f"\nAll outputs written to {OUT_DIR.relative_to(ROOT)}/")
    print(f"provenance: {prov_path.relative_to(ROOT)}")
    for fname, sha in output_hashes.items():
        print(f"  {fname}: {sha[:16]}...")
    print("\nDone.")


if __name__ == "__main__":
    main()
