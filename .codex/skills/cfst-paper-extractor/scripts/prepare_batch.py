#!/usr/bin/env python3
"""Prepare a batch workspace from available MinerU paper folders only."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reorganize_parsed_with_tables import find_parse_dir, reorganize_one_paper, write_json  # noqa: E402


def discover_raw_paper_dirs(raw_root: Path, include_regex: str | None) -> dict[str, Path]:
    pattern = re.compile(include_regex) if include_regex else None
    paper_dirs: dict[str, Path] = {}
    for item in sorted(raw_root.iterdir()):
        if not item.is_dir():
            continue
        if pattern and not pattern.search(item.name):
            continue
        match = re.search(r"\[(A\d+-\d+)\]", item.name)
        if not match:
            continue
        paper_id = match.group(1)
        paper_dirs[paper_id] = item
    return paper_dirs


def git_repo_status(cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--is-inside-work-tree"],
        check=False,
        text=True,
        capture_output=True,
    )
    return {
        "is_git_repo": proc.returncode == 0 and proc.stdout.strip() == "true",
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def infer_paper_title_hint(raw_dir: Path) -> str:
    text = raw_dir.name
    text = re.sub(r"^\[[^\]]+\]\s*", "", text)
    return text.replace("_ ", ": ").strip()


def build_folder_metadata(raw_dirs: dict[str, Path], paper_id: str) -> dict[str, Any]:
    raw_dir = raw_dirs.get(paper_id)
    return {
        "paper_id": paper_id,
        "citation_tag": f"[{paper_id}]",
        "paper_title_hint": infer_paper_title_hint(raw_dir) if raw_dir else "",
        "expected_specimen_count": None,
    }


def build_worker_job(
    output_root: Path,
    paper_id: str,
    normalized_dir: Path | None,
    expected_specimen_count: int | None,
) -> dict[str, Any]:
    tmp_json = output_root / "tmp" / paper_id / f"{paper_id}.json"
    final_json = output_root / "output" / f"{paper_id}.json"
    return {
        "paper_id": paper_id,
        "paper_dir_relpath": str(normalized_dir.relative_to(output_root)) if normalized_dir else None,
        "worker_output_json_path": str(tmp_json),
        "final_output_json_path": str(final_json),
        "expected_specimen_count": expected_specimen_count,
        "status": "prepared" if normalized_dir else "missing_raw_data",
    }


def selected_paper_ids(raw_dirs: dict[str, Path], explicit_ids: list[str] | None) -> list[str]:
    ids = explicit_ids or sorted(raw_dirs.keys())
    return sorted(set(ids), key=lambda value: tuple(int(x) for x in re.findall(r"\d+", value)) or (10**9,))


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare CFST batch workspace from MinerU folders.")
    parser.add_argument("--raw-root", type=Path, required=True, help="Root containing raw MinerU paper folders.")
    parser.add_argument("--output-root", type=Path, required=True, help="Batch output root.")
    parser.add_argument(
        "--include-regex",
        default=r"^\[A\d+-\d+\]",
        help="Regex for raw paper folder discovery.",
    )
    parser.add_argument(
        "--paper-ids",
        nargs="*",
        default=None,
        help="Optional explicit list like A1-1 A1-2.",
    )
    parser.add_argument(
        "--copy-legacy-json",
        action="store_true",
        help="Copy legacy content_list.json into normalized folders when available.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write files.")
    args = parser.parse_args()

    if not args.raw_root.exists():
        print(f"[FAIL] Raw root not found: {args.raw_root}")
        return 1

    output_root = args.output_root.resolve()
    manifests_dir = output_root / "manifests"
    normalized_root = output_root / "parsed_with_tables"
    logs_dir = output_root / "logs"
    exports_dir = output_root / "exports"
    tmp_dir = output_root / "tmp"
    final_output_dir = output_root / "output"

    raw_dirs = discover_raw_paper_dirs(args.raw_root, args.include_regex)
    selected_ids = selected_paper_ids(raw_dirs, args.paper_ids)

    batch_entries: list[dict[str, Any]] = []
    worker_jobs: list[dict[str, Any]] = []
    state_entries: list[dict[str, Any]] = []

    for paper_id in selected_ids:
        folder_metadata = build_folder_metadata(raw_dirs, paper_id)
        raw_dir = raw_dirs.get(paper_id)
        parse_dir = find_parse_dir(raw_dir) if raw_dir else None
        normalized_dir = normalized_root / paper_id if raw_dir else None
        preprocess_stats = None
        status = "missing_raw_data"

        if raw_dir and parse_dir:
            status = "prepared"
            if not args.dry_run:
                preprocess_stats = reorganize_one_paper(
                    src_paper_dir=raw_dir,
                    dst_root=normalized_root,
                    paper_token=paper_id,
                    dry_run=False,
                    copy_legacy_json=args.copy_legacy_json,
                )
            else:
                preprocess_stats = {
                    "paper_token": paper_id,
                    "source_paper_dir": str(raw_dir),
                    "source_parse_dir": str(parse_dir),
                    "normalized_paper_dir": str(normalized_dir),
                }
        elif raw_dir:
            status = "missing_parse_leaf"

        batch_entry = {
            "paper_id": paper_id,
            "citation_tag": folder_metadata["citation_tag"],
            "paper_title_hint": folder_metadata["paper_title_hint"],
            "expected_specimen_count": folder_metadata["expected_specimen_count"],
            "raw_dir": str(raw_dir) if raw_dir else None,
            "raw_parse_dir": str(parse_dir) if parse_dir else None,
            "normalized_dir": str(normalized_dir) if normalized_dir else None,
            "status": status,
            "preprocess_stats": preprocess_stats,
        }
        batch_entries.append(batch_entry)
        worker_jobs.append(
            build_worker_job(
                output_root=output_root,
                paper_id=paper_id,
                normalized_dir=normalized_dir if status == "prepared" else None,
                expected_specimen_count=folder_metadata["expected_specimen_count"],
            )
        )
        state_entries.append(
            {
                "paper_id": paper_id,
                "status": status,
                "retry_count": 0,
                "validated": False,
                "published": False,
                "last_error": None,
            }
        )

    batch_manifest = {
        "schema_version": "cfst-batch-manifest-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_root": str(args.raw_root.resolve()),
        "output_root": str(output_root),
        "git_status": git_repo_status(args.raw_root.resolve()),
        "paper_count": len(batch_entries),
        "papers": batch_entries,
    }

    batch_state = {
        "schema_version": "cfst-batch-state-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(state_entries),
        "papers": state_entries,
    }

    if not args.dry_run:
        for directory in (manifests_dir, logs_dir, exports_dir, tmp_dir, final_output_dir):
            directory.mkdir(parents=True, exist_ok=True)
        write_json(manifests_dir / "batch_manifest.json", batch_manifest)
        write_json(manifests_dir / "worker_jobs.json", worker_jobs)
        write_json(manifests_dir / "batch_state.json", batch_state)

    print(f"[OK] Prepared {len(batch_entries)} papers.")
    print(f"[INFO] Git repo present: {batch_manifest['git_status']['is_git_repo']}")
    print(f"[INFO] Output root: {output_root}")
    if not args.dry_run:
        print(f"[OK] Batch manifest: {manifests_dir / 'batch_manifest.json'}")
        print(f"[OK] Worker jobs: {manifests_dir / 'worker_jobs.json'}")
        print(f"[OK] Batch state: {manifests_dir / 'batch_state.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
