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


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

CLAIM_ID = "claim_004_episode1_beta_range"
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
SNAPSHOT_CLOSE_CSV = SNAPSHOT_DIR / "adjusted_close.csv"
SNAPSHOT_METADATA_JSON = SNAPSHOT_DIR / "metadata.json"

CORES = [
    {
        "core_id": "500d_core",
        "window_length": 500,
        "start_date": pd.Timestamp("2020-01-31"),
        "end_date": pd.Timestamp("2021-12-31"),
        "expected_observations": 24,
        "output_name": "beta_series_500d_core.csv",
    },
    {
        "core_id": "730d_core",
        "window_length": 730,
        "start_date": pd.Timestamp("2020-12-31"),
        "end_date": pd.Timestamp("2023-03-31"),
        "expected_observations": 28,
        "output_name": "beta_series_730d_core.csv",
    },
]


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
    missing = [col for col in required if col not in close.columns]
    if missing:
        raise RuntimeError(f"missing required columns: {missing}")
    close = close[required].dropna()
    if close.empty:
        raise RuntimeError("snapshot is empty after dropping missing TCS/INFY rows")
    return close, metadata


def month_end_trading_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    values = pd.Series(index=index, data=index)
    return list(values.groupby(values.index.to_period("M")).max())


def ols_beta_with_intercept(x: np.ndarray, y: np.ndarray) -> float:
    design = np.column_stack([np.ones(len(x)), x])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(coeffs[1])


def compute_beta_series(log_prices: pd.DataFrame, core: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    month_ends = [
        date
        for date in month_end_trading_dates(log_prices.index)
        if core["start_date"] <= pd.Timestamp(date) <= core["end_date"]
    ]
    for date in month_ends:
        trailing = log_prices.loc[:date].tail(int(core["window_length"]))
        if len(trailing) < int(core["window_length"]):
            skipped.append(pd.Timestamp(date).strftime("%Y-%m-%d"))
            continue
        x = trailing["INFY.NS"].to_numpy(dtype=float)
        y = trailing["TCS.NS"].to_numpy(dtype=float)
        rows.append({"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "beta": ols_beta_with_intercept(x, y)})
    return pd.DataFrame(rows, columns=["date", "beta"]), skipped


def stats_for_series(series: pd.DataFrame) -> dict[str, Any]:
    beta = series["beta"]
    first = series.iloc[0]
    last = series.iloc[-1]
    return {
        "min_beta": float(beta.min()),
        "max_beta": float(beta.max()),
        "mean_beta": float(beta.mean()),
        "median_beta": float(beta.median()),
        "std_beta_sample_ddof1": float(beta.std(ddof=1)),
        "first_observation_date": str(first["date"]),
        "first_observation_beta": float(first["beta"]),
        "last_observation_date": str(last["date"]),
        "last_observation_beta": float(last["beta"]),
        "observation_count": int(len(series)),
    }


def csv_body(series: pd.DataFrame) -> str:
    buffer = io.StringIO()
    series.to_csv(buffer, index=False, lineterminator="\n", float_format="%.15g")
    return buffer.getvalue()


def provenance_header(
    body: str,
    script_path: Path,
    commit: str,
    timestamp_utc: str,
    style: str,
) -> tuple[str, str]:
    content_hash = sha256_bytes(body.encode("utf-8"))
    lines = [
        f"script_path: {script_path}",
        f"git_commit: {commit}",
        f"snapshot_id: {SNAPSHOT_ID}",
        f"timestamp_utc: {timestamp_utc}",
        f"output_content_sha256: {content_hash}",
        "output_hash_scope: bytes after this provenance header",
        "final_file_sha256: recorded in provenance.json",
    ]
    if style == "html":
        return "<!--\n" + "\n".join(lines) + "\n-->\n", content_hash
    if style == "hash":
        return "\n".join(f"# {line}" for line in lines) + "\n", content_hash
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
    header, content_hash = provenance_header(body, script_path, commit, timestamp_utc, style)
    path.write_text(header + body, encoding="utf-8", newline="\n")
    return {
        "path": str(path.relative_to(ROOT)),
        "description": description,
        "content_sha256": content_hash,
        "final_file_sha256": file_sha256(path),
        "hash_scope": "bytes after provenance header",
    }


def format_float(value: float) -> str:
    return f"{value:.12f}"


def summary_body(
    all_stats: list[dict[str, Any]],
    skipped_by_core: dict[str, list[str]],
    csv_outputs: list[dict[str, Any]],
) -> str:
    lines = [
        "# Claim 004 Episode 1 Beta Range - Codex",
        "",
        "## Inputs",
        "",
        f"- Claim ID: `{CLAIM_ID}`",
        f"- Snapshot: `{SNAPSHOT_ID}`",
        "- Price file: `data/snapshots/tcs_infy_v1_2026-07-04/adjusted_close.csv`",
        "- Columns: `date`, `TCS.NS`, `INFY.NS`; rows missing either price dropped.",
        "- No live pulls and no snapshot regeneration.",
        "",
        "## Method",
        "",
        "- `y = log(TCS.NS)`, `x = log(INFY.NS)`.",
        "- Month-end trading dates within each supplied core boundary, inclusive.",
        "- OLS with intercept over the trailing N trading days ending at each month-end.",
        "- Beta is the coefficient on `x`; no pooling across cores or window lengths.",
        "- Standard deviation is sample standard deviation (`ddof=1`).",
        "",
        "## Results",
        "",
        "| core_id | window_length | observations | min_beta | max_beta | mean_beta | median_beta | std_beta_sample_ddof1 | first_date | first_beta | last_date | last_beta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: |",
    ]
    for row in all_stats:
        lines.append(
            "| {core_id} | {window_length} | {observation_count} | {min_beta} | {max_beta} | {mean_beta} | {median_beta} | {std_beta} | {first_date} | {first_beta} | {last_date} | {last_beta} |".format(
                core_id=row["core_id"],
                window_length=row["window_length"],
                observation_count=row["observation_count"],
                min_beta=format_float(row["min_beta"]),
                max_beta=format_float(row["max_beta"]),
                mean_beta=format_float(row["mean_beta"]),
                median_beta=format_float(row["median_beta"]),
                std_beta=format_float(row["std_beta_sample_ddof1"]),
                first_date=row["first_observation_date"],
                first_beta=format_float(row["first_observation_beta"]),
                last_date=row["last_observation_date"],
                last_beta=format_float(row["last_observation_beta"]),
            )
        )

    lines.extend(["", "## Skipped Month-Ends", ""])
    for core in CORES:
        skipped = skipped_by_core[core["core_id"]]
        value = ", ".join(skipped) if skipped else "None"
        lines.append(f"- `{core['core_id']}`: {value}")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
        ]
    )
    for output in csv_outputs:
        lines.append(f"- `{output['path']}` final SHA256 `{output['final_file_sha256']}`")
    lines.extend(
        [
            "",
            "## Limitation",
            "",
            "This output characterizes beta only at month-end sample points inside the supplied core boundaries. It does not characterize intra-month beta movement.",
            "",
        ]
    )
    return "\n".join(lines)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return json_safe(float(value))
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
    return value


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = Path(__file__).resolve()
    commit = git_commit()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    close, metadata = load_snapshot()
    log_prices = np.log(close)

    all_stats: list[dict[str, Any]] = []
    skipped_by_core: dict[str, list[str]] = {}
    outputs: list[dict[str, Any]] = []

    for core in CORES:
        series, skipped = compute_beta_series(log_prices, core)
        if series.empty:
            raise RuntimeError(f"no beta observations produced for {core['core_id']}")
        skipped_by_core[core["core_id"]] = skipped
        stats = stats_for_series(series)
        stats.update(
            {
                "core_id": core["core_id"],
                "window_length": core["window_length"],
                "core_start": core["start_date"].strftime("%Y-%m-%d"),
                "core_end": core["end_date"].strftime("%Y-%m-%d"),
                "expected_observations": core["expected_observations"],
                "skipped_month_ends": skipped,
            }
        )
        all_stats.append(stats)
        outputs.append(
            write_output(
                OUT_DIR / core["output_name"],
                csv_body(series),
                script_path,
                commit,
                timestamp_utc,
                f"Month-end rolling beta series for {core['core_id']}",
                "hash",
            )
        )

    summary_output = write_output(
        OUT_DIR / "summary.md",
        summary_body(all_stats, skipped_by_core, outputs),
        script_path,
        commit,
        timestamp_utc,
        "Descriptive statistics and method summary",
        "html",
    )
    outputs.append(summary_output)

    provenance = {
        "claim_id": CLAIM_ID,
        "snapshot_id": SNAPSHOT_ID,
        "snapshot_adjusted_close_sha256": metadata["files"]["adjusted_close.csv"]["sha256"],
        "snapshot_metadata": metadata,
        "script_path": str(script_path),
        "script_sha256": file_sha256(script_path),
        "git_commit": commit,
        "execution_timestamp_utc": timestamp_utc,
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "method": {
            "price_transform": "natural log adjusted close",
            "ols": "intercept included; beta is coefficient on log(INFY.NS)",
            "sampling": "last trading day of each calendar month within supplied core boundaries, inclusive",
            "std": "sample standard deviation, ddof=1",
            "isolation": "No isolation-prohibited prior beta-range paths or antigravity_opus outputs were read by this script.",
        },
        "cores": all_stats,
        "outputs": outputs,
    }
    provenance_body = json.dumps(json_safe(provenance), indent=2, sort_keys=True, allow_nan=False) + "\n"
    provenance_path = OUT_DIR / "provenance.json"
    provenance_path.write_text(provenance_body, encoding="utf-8", newline="\n")
    provenance_hash = file_sha256(provenance_path)

    print(f"claim_id={CLAIM_ID}")
    for row in all_stats:
        print(
            "{core_id} count={observation_count} min={min_beta:.12f} max={max_beta:.12f} mean={mean_beta:.12f} median={median_beta:.12f} std={std_beta_sample_ddof1:.12f}".format(
                **row
            )
        )
    for output in outputs:
        print(f"{output['path']} {output['final_file_sha256']}")
    print(f"{provenance_path.relative_to(ROOT)} {provenance_hash}")


if __name__ == "__main__":
    main()
