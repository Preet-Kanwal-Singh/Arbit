"""Provenance stamper for Tier B Z-score block-bootstrap check."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode("ascii").strip()
    except Exception:
        return "unknown"

def main():
    output_files = sorted(OUT_DIR.glob("*.json")) + sorted(OUT_DIR.glob("*.md")) + sorted(OUT_DIR.glob("*.py"))
    output_files = [f for f in output_files if f.name != "provenance.json"]

    provenance = {
        "claim_id": "wq_zscore_block_bootstrap_v0",
        "phase": "phase_ii_rl_agent_tcs_infy",
        "tier": "B",
        "snapshot_id": "tcs_infy_v4_2026-07-13",
        "synthetic": False,
        "script_path": str((OUT_DIR / "zscore_bootstrap.py").relative_to(ROOT)).replace("\\", "/"),
        "git_commit": git_commit(),
        "stamped_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "commit hash recorded after outputs were committed",
        "outputs": [str(f.relative_to(ROOT)).replace("\\", "/") for f in output_files],
    }

    (OUT_DIR / "provenance.json").write_text(json.dumps(provenance, indent=4) + "\n")
    print("Provenance saved to provenance.json")

if __name__ == "__main__":
    main()
