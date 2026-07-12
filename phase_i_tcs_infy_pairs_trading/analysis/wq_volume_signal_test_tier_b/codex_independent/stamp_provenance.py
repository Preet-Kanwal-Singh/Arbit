from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent
PROVENANCE_JSON = OUT_DIR / "provenance.json"
WORKLOG = ROOT / "phase_i_tcs_infy_pairs_trading" / "ledger" / "worklog" / "worklog_tier_b.md"
WORKLOG_ENTRY = OUT_DIR / "worklog_entry.md"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_out_ref() -> tuple[str, str, str]:
    git_dir = ROOT / ".git"
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref_name = head.removeprefix("ref: ").strip()
        ref_path = git_dir / ref_name
        commit = ref_path.read_text(encoding="utf-8").strip()
        branch = ref_name.removeprefix("refs/heads/")
        return branch, str(ref_path.relative_to(ROOT)).replace("\\", "/"), commit
    return "DETACHED", ".git/HEAD", head


def replace_placeholders(path: Path, commit: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("git_commit: PENDING_STAMP", f"git_commit: {commit}")
    text = text.replace("final_file_sha256: PENDING_STAMP", "final_file_sha256: recorded in provenance.json")
    path.write_text(text, encoding="utf-8", newline="\n")


def append_worklog_once() -> bool:
    entry = WORKLOG_ENTRY.read_text(encoding="utf-8").strip() + "\n"
    worklog_text = WORKLOG.read_text(encoding="utf-8")
    if "## wq_volume_signal_test_tier_b_codex_independent" in worklog_text:
        return False
    separator = "\n\n"
    if not worklog_text.endswith("\n"):
        separator = "\n\n"
    WORKLOG.write_text(worklog_text + separator + entry, encoding="utf-8", newline="\n")
    return True


def main() -> None:
    if not PROVENANCE_JSON.exists():
        raise FileNotFoundError(f"missing provenance file: {PROVENANCE_JSON}")
    provenance: dict[str, Any] = json.loads(PROVENANCE_JSON.read_text(encoding="utf-8"))
    branch, ref_path, commit = checked_out_ref()
    stamped_at = datetime.now(timezone.utc).isoformat()

    for output in provenance["outputs"]:
        replace_placeholders(ROOT / output["path"], commit)

    appended = append_worklog_once()

    provenance["git_commit"] = commit
    provenance["git_branch"] = branch
    provenance["git_ref_path_read"] = ref_path
    provenance["stamped_at_utc"] = stamped_at
    provenance["stamp_note"] = "commit read directly from the checked-out branch ref named by .git/HEAD"
    provenance["worklog_append"] = {
        "path": str(WORKLOG.relative_to(ROOT)).replace("\\", "/"),
        "appended": appended,
        "sha256_after_stamp": file_sha256(WORKLOG),
    }
    for output in provenance["outputs"]:
        output["final_file_sha256"] = file_sha256(ROOT / output["path"])

    PROVENANCE_JSON.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    print(f"git_commit={commit}")
    print(f"git_branch={branch}")
    print(f"worklog_appended={appended}")
    print(f"provenance_sha256={file_sha256(PROVENANCE_JSON)}")


if __name__ == "__main__":
    main()
