"""Stamp provenance.json after outputs are committed (post-output commit hash)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

SCRIPT_PATH = OUT_DIR / "run_acceptance_test.py"
SNAPSHOT_ID = "tcs_infy_v1_2026-07-04"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> None:
    output_files = sorted(OUT_DIR.glob("run_log*.txt"))
    provenance = {
        "claim_id": "wq_env_scaffolding_v0",
        "phase": "phase_ii_rl_agent_tcs_infy",
        "tier": "C",
        "snapshot_id": SNAPSHOT_ID,
        "script_path": str(SCRIPT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "git_commit": git_commit(),
        "stamped_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "commit hash recorded after outputs were committed, not pre-run HEAD",
        "outputs": [
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha256(path),
            }
            for path in output_files
        ],
    }
    out_path = OUT_DIR / "provenance.json"
    out_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
