"""Stamp snapshot metadata git_commit after outputs are committed."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent
SNAPSHOT_ID = "tcs_infy_v3_2026-07-13"
SNAPSHOT_DIR = ROOT / "data" / "snapshots" / SNAPSHOT_ID
METADATA_JSON = SNAPSHOT_DIR / "metadata.json"
SCRIPT_PATH = OUT_DIR / "create_tcs_infy_snapshot.py"


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
    if not METADATA_JSON.exists():
        raise FileNotFoundError(f"missing snapshot metadata: {METADATA_JSON}")

    metadata = json.loads(METADATA_JSON.read_text(encoding="utf-8"))
    if metadata.get("snapshot_id") != SNAPSHOT_ID:
        raise RuntimeError(f"snapshot_id mismatch: {metadata.get('snapshot_id')}")

    csv_path = SNAPSHOT_DIR / "adjusted_close.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"missing snapshot file: {csv_path}")

    commit = git_commit()
    metadata["git_commit"] = commit
    metadata["provenance_stamped_at_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["files"][csv_path.name]["sha256"] = file_sha256(csv_path)
    METADATA_JSON.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    provenance = {
        "claim_id": "create_tcs_infy_snapshot_v3",
        "phase": "phase_ii_rl_agent_tcs_infy",
        "tier": "C",
        "snapshot_id": SNAPSHOT_ID,
        "script_path": str(SCRIPT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "git_commit": commit,
        "stamped_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "commit hash recorded after outputs were committed, not pre-run HEAD",
        "outputs": [
            {
                "path": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha256(csv_path),
            },
            {
                "path": str(METADATA_JSON.relative_to(ROOT)).replace("\\", "/"),
                "sha256": file_sha256(METADATA_JSON),
            },
        ],
    }
    provenance_path = OUT_DIR / "provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"updated {METADATA_JSON}")
    print(f"wrote {provenance_path}")


if __name__ == "__main__":
    main()
