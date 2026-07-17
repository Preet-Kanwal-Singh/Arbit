"""Stamp provenance for PC-2 runs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

SNAPSHOT_ID = "synthetic_positive_control_v2"
DGP_PARAMS = {
    "kappa": 0.1,
    "sigma": 0.3,
    "beta": 0.70,
    "sigma_x": 0.015,
    "eps_x_t": "~ N(0, 0.000225)",
    "master_seed": 20260101,
    "length": 2800
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True,
    )
    return result.stdout.strip()


def main() -> None:
    oracle_refs = json.loads((OUT_DIR / "oracle_refs.json").read_text())

    output_files = sorted(OUT_DIR.glob("*.json")) + sorted(OUT_DIR.glob("*.md")) + sorted(OUT_DIR.glob("*.py"))
    output_files = [f for f in output_files if f.name != "provenance.json"]

    provenance = {
        "claim_id": "wq_positive_control_v1_pc2",
        "phase": "phase_ii_rl_agent_tcs_infy",
        "tier": "C",
        "snapshot_id": SNAPSHOT_ID,
        "synthetic": True,
        "synthetic_dgp": {
            "process": "AR(1) mean-reverting spread, Random Walk log(X_t)",
            "formula": "spread_{t+1} = (1-kappa)*spread_t + sigma*eps_t; log(Y_t) = beta*log(X_t) + spread_t",
            **DGP_PARAMS,
        },
        "script_path": str((OUT_DIR / "train_pc2b.py").relative_to(ROOT)).replace("\\", "/"),
        "git_commit": git_commit(),
        "stamped_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "commit hash recorded after outputs were committed",
        "oracle_refs": oracle_refs,
        "outputs": [
            {"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": file_sha256(p)}
            for p in output_files if p.is_file()
        ],
    }

    (OUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print("Provenance saved to provenance.json")


if __name__ == "__main__":
    main()
