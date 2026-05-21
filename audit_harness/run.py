"""CLI entry point for the Zenlo audit harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

import pandas as pd

from config import DATA_DIR, OUTPUT_DIR
from audit_harness.classifiers.pattern import detect_pattern_cohort
from audit_harness.loaders.nhanes import (
    biomarker_available,
    biomarker_unavailable_reason,
    cycle_data_dir,
    expected_files_for_cycle,
    filter_cohort,
    load_nhanes_cycle,
    pattern_available,
)
from audit_harness.reporters.markdown import write_json, write_report
from audit_harness.tests.agreement import agreement_for_biomarker
from audit_harness.tests.distribution import distribution_for_biomarker, distribution_for_pattern
from audit_harness.tests.fairness import fairness_for_biomarker, fairness_for_pattern

DEFAULT_CYCLE = "2015-2016"

BIOMARKERS = [
    "HSCRP",
    "GLU",
    "INSULIN",
    "CALCIUM",
    "FERRITIN",
    "TG",
    "HDL",
    "HBA1C",
    "TOTAL_CHOL",
    "LDL",
]
PATTERNS = ["inflammation", "insulin_resistance", "metabolic_syndrome"]


def _git_commit() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _file_hashes(data_dir: Path, cycle: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    cycle_dir = cycle_data_dir(data_dir, cycle)
    for stem in expected_files_for_cycle(cycle):
        for ext in (".XPT", ".xpt"):
            path = cycle_dir / f"{stem}{ext}"
            if path.exists():
                hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                break
    return hashes


def _package_versions() -> dict[str, str]:
    packages = ["pandas", "pyreadstat", "numpy", "scipy", "jinja2", "pytest"]
    versions: dict[str, str] = {}
    for pkg in packages:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = "not installed"
    return versions


def build_manifest(cycle: str, data_dir: Path, unit_id: str) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "unit_id": unit_id,
        "cycle": cycle,
        "python_version": sys.version,
        "platform": platform.platform(),
        "package_versions": _package_versions(),
        "data_dir": str(data_dir),
        "cycle_data_dir": str(cycle_data_dir(data_dir, cycle)),
        "input_file_hashes_sha256": _file_hashes(data_dir, cycle),
        "git_commit": _git_commit(),
    }


def _unavailable_result(
    unit_type: str,
    unit_id: str,
    cycle: str,
    message: str,
    *,
    n_total: int = 0,
) -> dict[str, Any]:
    return {
        "unit_type": unit_type,
        "unit_id": unit_id,
        "cycle": cycle,
        "status": "DATA_UNAVAILABLE",
        "status_message": message,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort": {"n_total": n_total},
        "distribution": {"note": message},
        "agreement": {"note": message},
        "fairness": {"note": message},
    }


def run_biomarker(code: str, cycle: str, data_dir: Path, df: pd.DataFrame) -> dict[str, Any]:
    code = code.upper()
    reason = biomarker_unavailable_reason(code, cycle)
    if reason or not biomarker_available(df, code):
        msg = reason or f"Biomarker {code} column has no usable values in loaded cohort"
        return _unavailable_result("biomarker", code, cycle, msg, n_total=len(df))

    dist = distribution_for_biomarker(df, code)
    agree = agreement_for_biomarker(df, code)
    fair = fairness_for_biomarker(df, code)

    return {
        "unit_type": "biomarker",
        "unit_id": code,
        "cycle": cycle,
        "status": "OK",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort": {"n_total": len(df), "n_valid": dist["n_valid"]},
        "distribution": dist,
        "agreement": agree,
        "fairness": fair,
    }


def run_pattern(slug: str, cycle: str, data_dir: Path, df: pd.DataFrame) -> dict[str, Any]:
    slug = slug.lower()
    ok, reason = pattern_available(df, slug, cycle)
    if not ok:
        return _unavailable_result(
            "pattern", slug, cycle, reason or "Pattern data unavailable", n_total=len(df)
        )

    df = detect_pattern_cohort(df, slug)
    detected_col = f"pattern_{slug}_detected"

    dist = distribution_for_pattern(df, slug, detected_col)
    fair = fairness_for_pattern(df, slug, detected_col)

    return {
        "unit_type": "pattern",
        "unit_id": slug,
        "cycle": cycle,
        "status": "OK",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort": {"n_total": len(df), "n_detected": dist["n_detected"]},
        "distribution": dist,
        "agreement": {
            "note": "Production comparison not yet wired; pattern prevalence only.",
        },
        "fairness": fair,
    }


def persist_results(results: dict[str, Any], manifest: dict[str, Any]) -> tuple[Path, Path]:
    unit_id = results["unit_id"].upper() if results["unit_type"] == "biomarker" else results["unit_id"]
    base = OUTPUT_DIR / f"{unit_id}_results"
    json_path = Path(f"{base}.json")
    md_path = Path(f"{base}_report.md")

    payload = {"results": results, "manifest": manifest}
    write_json(payload, json_path)
    write_report(results, md_path)
    write_json(manifest, OUTPUT_DIR / "manifest.json")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Zenlo Labs independent audit harness")
    parser.add_argument("--biomarker", type=str, help="Biomarker code e.g. HSCRP")
    parser.add_argument("--pattern", type=str, help="Pattern slug e.g. inflammation")
    parser.add_argument("--cycle", type=str, default=DEFAULT_CYCLE, help="NHANES cycle label")
    parser.add_argument("--all", action="store_true", help="Run all biomarkers and patterns")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help=f"NHANES root directory (default: {DATA_DIR}); XPT files live in <data-dir>/<cycle>/",
    )
    args = parser.parse_args(argv)

    data_dir = args.data_dir or DATA_DIR

    if not args.biomarker and not args.pattern and not args.all:
        parser.error("Specify --biomarker, --pattern, or --all")

    units: list[tuple[str, str]] = []
    if args.all:
        units.extend(("biomarker", b) for b in BIOMARKERS)
        units.extend(("pattern", p) for p in PATTERNS)
    else:
        if args.biomarker:
            units.append(("biomarker", args.biomarker.upper()))
        if args.pattern:
            units.append(("pattern", args.pattern.lower()))

    df = filter_cohort(load_nhanes_cycle(args.cycle, data_dir), min_age=18)
    load_warnings = df.attrs.get("load_warnings", [])
    if load_warnings:
        print(f"Load warnings ({len(load_warnings)}):")
        for w in load_warnings:
            print(f"  - {w}")

    for unit_type, unit_id in units:
        manifest = build_manifest(args.cycle, data_dir, unit_id)
        if unit_type == "biomarker":
            results = run_biomarker(unit_id, args.cycle, data_dir, df)
        else:
            results = run_pattern(unit_id, args.cycle, data_dir, df)
        json_path, md_path = persist_results(results, manifest)
        status = results.get("status", "OK")
        print(f"[{status}] Wrote {json_path}")
        print(f"[{status}] Wrote {md_path}")
        print(f"Manifest: {OUTPUT_DIR / 'manifest.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
