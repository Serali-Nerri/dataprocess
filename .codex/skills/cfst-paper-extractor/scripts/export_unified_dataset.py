#!/usr/bin/env python3
"""Flatten validated CFST JSON outputs into a unified CSV for ML/DL workflows."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_output_files(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.glob("*.json") if path.is_file())


def derive_features(row: dict[str, Any]) -> dict[str, Any]:
    b = row.get("b")
    h = row.get("h")
    t = row.get("t")
    L = row.get("L")
    e1 = row.get("e1")
    e2 = row.get("e2")

    d_eq_geom = None
    L_over_deq = None
    b_over_t = None
    h_over_t = None
    e_abs_max = None
    e_over_deq = None

    if isinstance(b, (int, float)) and isinstance(h, (int, float)) and b > 0 and h > 0:
        d_eq_geom = round(math.sqrt(float(b) * float(h)), 6)
    if isinstance(L, (int, float)) and d_eq_geom and d_eq_geom > 0:
        L_over_deq = round(float(L) / d_eq_geom, 6)
    if isinstance(t, (int, float)) and t > 0:
        if isinstance(b, (int, float)):
            b_over_t = round(float(b) / float(t), 6)
        if isinstance(h, (int, float)):
            h_over_t = round(float(h) / float(t), 6)
    if isinstance(e1, (int, float)) and isinstance(e2, (int, float)):
        e_abs_max = round(max(abs(float(e1)), abs(float(e2))), 6)
        if d_eq_geom and d_eq_geom > 0:
            e_over_deq = round(e_abs_max / d_eq_geom, 6)

    return {
        "d_eq_geom_mm": d_eq_geom,
        "L_over_d_eq": L_over_deq,
        "b_over_t": b_over_t,
        "h_over_t": h_over_t,
        "e_abs_max_mm": e_abs_max,
        "e_over_d_eq": e_over_deq,
    }


def flatten_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    paper_id = payload.get("paper_id")
    ref_info = payload.get("ref_info", {})
    ordinary_filter = payload.get("ordinary_filter", {})
    paper_level = payload.get("paper_level", {})

    rows: list[dict[str, Any]] = []
    for group_name in ("Group_A", "Group_B", "Group_C"):
        group = payload.get(group_name, [])
        if not isinstance(group, list):
            continue

        for specimen in group:
            if not isinstance(specimen, dict):
                continue
            flat = {
                "schema_version": payload.get("schema_version"),
                "paper_id": paper_id,
                "citation_tag": ref_info.get("citation_tag"),
                "title": ref_info.get("title"),
                "journal": ref_info.get("journal"),
                "year": ref_info.get("year"),
                "is_valid": payload.get("is_valid"),
                "is_ordinary_cfst": payload.get("is_ordinary_cfst"),
                "include_in_dataset": ordinary_filter.get("include_in_dataset"),
                "special_factors": "|".join(ordinary_filter.get("special_factors", [])),
                "group_name": group_name,
                "paper_loading_mode": paper_level.get("loading_mode"),
                "paper_boundary_condition": paper_level.get("boundary_condition"),
                "paper_test_temperature": paper_level.get("test_temperature"),
                "paper_loading_regime": paper_level.get("loading_regime"),
                "paper_loading_pattern": paper_level.get("loading_pattern"),
                "expected_specimen_count": paper_level.get("expected_specimen_count"),
                "specimen_label": specimen.get("specimen_label"),
                "section_shape": specimen.get("section_shape"),
                "loading_mode": specimen.get("loading_mode"),
                "boundary_condition": specimen.get("boundary_condition"),
                "fc_value": specimen.get("fc_value"),
                "fc_type": specimen.get("fc_type"),
                "fc_basis": specimen.get("fc_basis"),
                "fy": specimen.get("fy"),
                "r_ratio": specimen.get("r_ratio"),
                "steel_type": specimen.get("steel_type"),
                "concrete_type": specimen.get("concrete_type"),
                "b": specimen.get("b"),
                "h": specimen.get("h"),
                "t": specimen.get("t"),
                "r0": specimen.get("r0"),
                "L": specimen.get("L"),
                "e1": specimen.get("e1"),
                "e2": specimen.get("e2"),
                "n_exp": specimen.get("n_exp"),
                "source_evidence": specimen.get("source_evidence"),
                "quality_flags": "|".join(specimen.get("quality_flags", [])),
                "evidence_page": (specimen.get("evidence") or {}).get("page"),
                "evidence_table_id": (specimen.get("evidence") or {}).get("table_id"),
                "evidence_figure_id": (specimen.get("evidence") or {}).get("figure_id"),
                "evidence_table_image": (specimen.get("evidence") or {}).get("table_image"),
                "evidence_setup_image": (specimen.get("evidence") or {}).get("setup_image"),
            }
            flat.update(derive_features(specimen))
            rows.append(flat)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Export validated CFST outputs as unified CSV.")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing validated JSON outputs.")
    parser.add_argument("--output-csv", type=Path, required=True, help="Output CSV path.")
    parser.add_argument("--summary-json", type=Path, default=None, help="Optional summary JSON path.")
    args = parser.parse_args()

    if not args.input_dir.exists():
        print(f"[FAIL] Input directory not found: {args.input_dir}")
        return 1

    files = iter_output_files(args.input_dir)
    rows: list[dict[str, Any]] = []
    for path in files:
        payload = read_json(path)
        rows.extend(flatten_payload(payload))

    fieldnames = [
        "schema_version",
        "paper_id",
        "citation_tag",
        "title",
        "journal",
        "year",
        "is_valid",
        "is_ordinary_cfst",
        "include_in_dataset",
        "special_factors",
        "group_name",
        "paper_loading_mode",
        "paper_boundary_condition",
        "paper_test_temperature",
        "paper_loading_regime",
        "paper_loading_pattern",
        "expected_specimen_count",
        "specimen_label",
        "section_shape",
        "loading_mode",
        "boundary_condition",
        "fc_value",
        "fc_type",
        "fc_basis",
        "fy",
        "r_ratio",
        "steel_type",
        "concrete_type",
        "b",
        "h",
        "t",
        "r0",
        "L",
        "e1",
        "e2",
        "n_exp",
        "d_eq_geom_mm",
        "L_over_d_eq",
        "b_over_t",
        "h_over_t",
        "e_abs_max_mm",
        "e_over_d_eq",
        "source_evidence",
        "quality_flags",
        "evidence_page",
        "evidence_table_id",
        "evidence_figure_id",
        "evidence_table_image",
        "evidence_setup_image",
    ]

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "input_dir": str(args.input_dir),
            "paper_json_count": len(files),
            "specimen_row_count": len(rows),
            "output_csv": str(args.output_csv),
        }
        args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] Exported {len(rows)} specimen rows from {len(files)} paper JSON files.")
    print(f"[OK] CSV: {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
