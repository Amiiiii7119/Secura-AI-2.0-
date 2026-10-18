#!/usr/bin/env python3
"""Secura AI 2.0 ? Forensic Evaluation & Validation Harness.

Executes controlled evaluation across deterministic synthetic fixtures and optional
labelled known-origin manifests without duplicating engine implementations.
Generates machine-readable JSON and CSV reports with strict in-memory privacy.
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.evaluation.fixtures import generate_all_fixtures, SyntheticFixture
from app.services.image_validation import ImageValidationError, validate_image_payload
from app.services.ela import perform_error_level_analysis
from app.services.dct_analysis import perform_dct_analysis
from app.services.noise_residual import perform_noise_residual_analysis
from app.services.c2pa_inspector import inspect_c2pa_manifest


def evaluate_fixture(fixture: SyntheticFixture) -> Dict[str, Any]:
    """Execute all forensic engines directly on a fixture and collect quantitative metrics."""
    record: Dict[str, Any] = {
        "fixture_id": fixture.fixture_id,
        "name": fixture.name,
        "description": fixture.description,
        "construction_method": fixture.construction_method,
        "intended_test_property": fixture.intended_test_property,
        "format": fixture.format_name,
        "category": "synthetic_controlled",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PROCESSED",
        "timings_ms": {},
        "validation": {},
        "ela": {},
        "dct": {},
        "noise": {},
        "c2pa": {},
        "errors": []
    }

    # Step 1: Payload Validation if raw bytes exist
    pil_img = fixture.pil_image
    if fixture.raw_bytes is not None:
        t0 = time.perf_counter()
        try:
            val_res, decoded_img = validate_image_payload(
                fixture.raw_bytes,
                declared_filename=f"{fixture.fixture_id.lower()}.{fixture.format_name.lower()}"
            )
            record["timings_ms"]["validation"] = round((time.perf_counter() - t0) * 1000, 2)
            record["validation"] = {
                "is_valid": True,
                "detected_format": val_res.detected_format.value,
                "width": val_res.width,
                "height": val_res.height,
                "pixel_count": val_res.pixel_count,
                "file_size_bytes": val_res.file_size_bytes
            }
            pil_img = decoded_img
        except ImageValidationError as ive:
            record["timings_ms"]["validation"] = round((time.perf_counter() - t0) * 1000, 2)
            record["validation"] = {"is_valid": False, "error_code": ive.error_code, "message": ive.message}
            record["status"] = "REJECTED_AS_EXPECTED" if fixture.format_name == "CORRUPT" else "VALIDATION_FAILED"
            record["errors"].append(f"Validation: {ive.message}")
            return record

    if pil_img is None:
        record["status"] = "SKIPPED_NO_DECODABLE_IMAGE"
        return record

    w, h = pil_img.size
    record["dimensions"] = {"width": w, "height": h, "pixel_count": w * h}

    # Step 2: Error Level Analysis (ELA)
    t0 = time.perf_counter()
    try:
        is_png = fixture.format_name == "PNG"
        ela_res = perform_error_level_analysis(pil_img, is_png=is_png)
        record["timings_ms"]["ela"] = round((time.perf_counter() - t0) * 1000, 2)
        record["ela"] = {
            "status": ela_res.status,
            "mean_absolute_difference": ela_res.metrics.mean_absolute_difference if ela_res.metrics else None,
            "max_absolute_difference": ela_res.metrics.max_absolute_difference if ela_res.metrics else None,
            "std_absolute_difference": ela_res.metrics.std_absolute_difference if ela_res.metrics else None,
            "quality": ela_res.metrics.recompression_quality if ela_res.metrics else None,
            "notes": ela_res.analysis_notes
        }
    except Exception as exc:
        record["timings_ms"]["ela"] = round((time.perf_counter() - t0) * 1000, 2)
        record["ela"] = {"status": "ERROR", "error": str(exc)}
        record["errors"].append(f"ELA: {str(exc)}")

    # Step 3: DCT / Block-Artifact Analysis
    t0 = time.perf_counter()
    try:
        dct_res = perform_dct_analysis(pil_img)
        record["timings_ms"]["dct"] = round((time.perf_counter() - t0) * 1000, 2)
        record["dct"] = {
            "status": dct_res.status,
            "blocking_artifact_ratio": dct_res.metrics.blocking_artifact_ratio if dct_res.metrics else None,
            "boundary_discontinuity": dct_res.metrics.boundary_discontinuity if dct_res.metrics else None,
            "internal_discontinuity": dct_res.metrics.internal_discontinuity if dct_res.metrics else None,
            "total_blocks": dct_res.metrics.total_blocks if dct_res.metrics else None,
            "mean_block_energy": dct_res.metrics.mean_block_energy if dct_res.metrics else None,
            "notes": dct_res.analysis_notes
        }
    except Exception as exc:
        record["timings_ms"]["dct"] = round((time.perf_counter() - t0) * 1000, 2)
        record["dct"] = {"status": "ERROR", "error": str(exc)}
        record["errors"].append(f"DCT: {str(exc)}")

    # Step 4: High-Pass Noise Residual Analysis
    t0 = time.perf_counter()
    try:
        noise_res = perform_noise_residual_analysis(pil_img)
        record["timings_ms"]["noise"] = round((time.perf_counter() - t0) * 1000, 2)
        record["noise"] = {
            "status": noise_res.status,
            "mean_absolute_residual": noise_res.metrics.mean_absolute_residual if noise_res.metrics else None,
            "std_residual": noise_res.metrics.std_residual if noise_res.metrics else None,
            "max_residual": noise_res.metrics.max_residual if noise_res.metrics else None,
            "noise_energy": noise_res.metrics.noise_energy if noise_res.metrics else None,
            "snr_estimate_db": noise_res.metrics.snr_estimate_db if noise_res.metrics else None,
            "notes": noise_res.analysis_notes
        }
    except Exception as exc:
        record["timings_ms"]["noise"] = round((time.perf_counter() - t0) * 1000, 2)
        record["noise"] = {"status": "ERROR", "error": str(exc)}
        record["errors"].append(f"Noise: {str(exc)}")

    # Step 5: C2PA Inspection (if raw bytes available)
    if fixture.raw_bytes is not None:
        t0 = time.perf_counter()
        try:
            c2pa_res = inspect_c2pa_manifest(
                fixture.raw_bytes,
                mime_type="image/jpeg" if fixture.format_name == "JPEG" else "image/png"
            )
            record["timings_ms"]["c2pa"] = round((time.perf_counter() - t0) * 1000, 2)
            record["c2pa"] = {
                "status": c2pa_res.status.value,
                "manifest_present": c2pa_res.manifest_present,
                "notes": c2pa_res.provenance_notes
            }
        except Exception as exc:
            record["timings_ms"]["c2pa"] = round((time.perf_counter() - t0) * 1000, 2)
            record["c2pa"] = {"status": "ERROR", "error": str(exc)}
            record["errors"].append(f"C2PA: {str(exc)}")

    # Step 6: Metadata & Container Forensics (Mission 09)
    if fixture.raw_bytes is not None:
        t0 = time.perf_counter()
        try:
            from app.schemas.evidence import ImageFormat, ImageValidationResult
            from app.services.metadata_inspector import inspect_metadata
            fmt = ImageFormat.JPEG if fixture.format_name == "JPEG" else ImageFormat.PNG
            val_dummy = ImageValidationResult(
                is_valid=True,
                detected_format=fmt,
                width=w,
                height=h,
                pixel_count=w * h,
                color_mode="RGB",
                file_size_bytes=len(fixture.raw_bytes),
                mime_type="image/jpeg" if fmt == ImageFormat.JPEG else "image/png"
            )
            meta_res = inspect_metadata(pil_img, fixture.raw_bytes, val_dummy)
            record["timings_ms"]["metadata"] = round((time.perf_counter() - t0) * 1000, 2)
            record["metadata"] = {
                "inventory_status": meta_res.inventory.status.value,
                "detected_structures": meta_res.inventory.detected_structures,
                "gps_present": meta_res.gps_summary.gps_present,
                "thumbnail_status": meta_res.thumbnail_analysis.status.value,
                "thumbnail_similarity_score": meta_res.thumbnail_analysis.similarity_score,
                "consistency_status": meta_res.container_consistency.status,
                "observation_count": len(meta_res.container_consistency.observations),
            }
        except Exception as exc:
            record["timings_ms"]["metadata"] = round((time.perf_counter() - t0) * 1000, 2)
            record["metadata"] = {"status": "ERROR", "error": str(exc)}
            record["errors"].append(f"Metadata: {str(exc)}")

    # Step 7: Unified Evidence Fusion (Mission 10)
    t0 = time.perf_counter()
    try:
        from app.services.evidence_fusion import synthesize_forensic_evidence
        from app.schemas.evidence import ImageFormat, ImageValidationResult
        val_eval = ImageValidationResult(
            is_valid=True,
            detected_format=ImageFormat.JPEG if fixture.format_name == "JPEG" else ImageFormat.PNG,
            width=w,
            height=h,
            pixel_count=w * h,
            color_mode="RGB",
            file_size_bytes=len(fixture.raw_bytes) if fixture.raw_bytes else 1000,
            mime_type="image/jpeg" if fixture.format_name == "JPEG" else "image/png"
        )
        report = synthesize_forensic_evidence(
            image_validation=val_eval,
            ela_result=locals().get("ela_res"),
            dct_result=locals().get("dct_res"),
            noise_result=locals().get("noise_res"),
            c2pa_result=locals().get("c2pa_res"),
            metadata_result=locals().get("meta_res"),
            component_errors=[],
        )
        record["timings_ms"]["fusion"] = round((time.perf_counter() - t0) * 1000, 2)
        record["fusion"] = {
            "status": report.analysis_completion_status,
            "total_findings": report.total_findings_count,
            "evidence_observed_count": sum(1 for f in report.findings if f.status.value == "EVIDENCE_OBSERVED"),
            "no_anomaly_count": sum(1 for f in report.findings if f.status.value == "NO_ANOMALY_OBSERVED"),
            "inconclusive_count": sum(1 for f in report.findings if f.status.value == "INCONCLUSIVE"),
        }
    except Exception as exc:
        record["timings_ms"]["fusion"] = round((time.perf_counter() - t0) * 1000, 2)
        record["fusion"] = {"status": "ERROR", "error": str(exc)}
        record["errors"].append(f"Fusion: {str(exc)}")

    return record


def compute_feature_separability(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute grouped statistical distributions across evaluation categories.
    
    Forensic Limitation:
    Differences in summary metrics across synthetic or small sample sets do NOT imply
    generalizable separability in real-world scenarios. No classifier is trained or deployed.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        if r.get("status") == "PROCESSED":
            cat = r.get("category", "synthetic_controlled")
            groups.setdefault(cat, []).append(r)

    def stats_for_field(items: List[Dict[str, Any]], path: List[str]) -> Dict[str, Any]:
        vals = []
        for it in items:
            cur = it
            for p in path:
                if isinstance(cur, dict):
                    cur = cur.get(p)
                else:
                    cur = None
                    break
            if cur is not None and isinstance(cur, (int, float)):
                vals.append(float(cur))
        if not vals:
            return {"count": 0, "mean": None, "std": None, "min": None, "max": None}
        return {
            "count": len(vals),
            "mean": round(float(sum(vals) / len(vals)), 4),
            "std": round(float((sum((v - sum(vals)/len(vals))**2 for v in vals) / len(vals))**0.5), 4),
            "min": round(float(min(vals)), 4),
            "max": round(float(max(vals)), 4)
        }

    analysis: Dict[str, Any] = {
        "limitation_disclaimer": (
            "STATISTICAL LIMITATION NOTICE: Descriptive metrics across synthetic test fixtures or "
            "small convenience sets demonstrate numerical behavior under controlled conditions. "
            "They do not establish classification separability, open-world accuracy, or AI detection "
            "capabilities. No machine learning model or binary decision boundary has been evaluated."
        ),
        "groups": {}
    }

    for group_name, items in groups.items():
        analysis["groups"][group_name] = {
            "sample_count": len(items),
            "ela_mean_difference": stats_for_field(items, ["ela", "mean_absolute_difference"]),
            "dct_blocking_artifact_ratio": stats_for_field(items, ["dct", "blocking_artifact_ratio"]),
            "dct_mean_block_energy": stats_for_field(items, ["dct", "mean_block_energy"]),
            "noise_mean_absolute_residual": stats_for_field(items, ["noise", "mean_absolute_residual"]),
            "noise_energy": stats_for_field(items, ["noise", "noise_energy"]),
            "noise_snr_proxy_db": stats_for_field(items, ["noise", "snr_estimate_db"])
        }

    return analysis


def export_evaluation_results(
    records: List[Dict[str, Any]],
    separability: Dict[str, Any],
    output_dir: Path
) -> Tuple[Path, Path, Path]:
    """Export structured evaluation records to JSON, CSV, and separability analysis."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evaluation_summary.json"
    csv_path = output_dir / "evaluation_metrics.csv"
    sep_path = output_dir / "feature_separability.json"

    # Export Summary JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata": {
                    "generated_utc": datetime.now(timezone.utc).isoformat(),
                    "total_samples": len(records),
                    "successful_evaluations": sum(1 for r in records if r["status"] == "PROCESSED"),
                    "controlled_rejections": sum(1 for r in records if r["status"] == "REJECTED_AS_EXPECTED")
                },
                "records": records
            },
            f,
            indent=2
        )

    # Export Metrics CSV
    csv_columns = [
        "fixture_id", "name", "category", "format", "width", "height", "pixel_count",
        "status", "ela_status", "ela_mean_diff", "ela_max_diff", "ela_std_diff",
        "dct_status", "dct_bar", "dct_boundary_disc", "dct_internal_disc", "dct_ac_energy",
        "noise_status", "noise_mean_res", "noise_std_res", "noise_energy", "noise_snr_db",
        "c2pa_status", "c2pa_present", "meta_status", "thumb_status", "thumb_sim_score", "consistency_status", "fusion_status",
        "total_time_ms"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for r in records:
            dims = r.get("dimensions", {})
            ela = r.get("ela", {})
            dct = r.get("dct", {})
            noise = r.get("noise", {})
            c2pa = r.get("c2pa", {})
            timings = r.get("timings_ms", {})
            total_t = sum(timings.values()) if timings else 0.0

            writer.writerow({
                "fixture_id": r["fixture_id"],
                "name": r["name"],
                "category": r.get("category", "synthetic"),
                "format": r.get("format", ""),
                "width": dims.get("width", ""),
                "height": dims.get("height", ""),
                "pixel_count": dims.get("pixel_count", ""),
                "status": r.get("status", ""),
                "ela_status": ela.get("status", ""),
                "ela_mean_diff": ela.get("mean_absolute_difference", ""),
                "ela_max_diff": ela.get("max_absolute_difference", ""),
                "ela_std_diff": ela.get("std_absolute_difference", ""),
                "dct_status": dct.get("status", ""),
                "dct_bar": dct.get("blocking_artifact_ratio", ""),
                "dct_boundary_disc": dct.get("boundary_discontinuity", ""),
                "dct_internal_disc": dct.get("internal_discontinuity", ""),
                "dct_ac_energy": dct.get("mean_block_energy", ""),
                "noise_status": noise.get("status", ""),
                "noise_mean_res": noise.get("mean_absolute_residual", ""),
                "noise_std_res": noise.get("std_residual", ""),
                "noise_energy": noise.get("noise_energy", ""),
                "noise_snr_db": noise.get("snr_estimate_db", ""),
                "c2pa_status": c2pa.get("status", ""),
                "c2pa_present": c2pa.get("manifest_present", ""),
                "meta_status": r.get("metadata", {}).get("inventory_status", ""),
                "thumb_status": r.get("metadata", {}).get("thumbnail_status", ""),
                "thumb_sim_score": r.get("metadata", {}).get("thumbnail_similarity_score", ""),
                "consistency_status": r.get("metadata", {}).get("consistency_status", ""),
                "fusion_status": r.get("fusion", {}).get("status", ""),
                "total_time_ms": round(total_t, 2)
            })

    # Export Separability JSON
    with open(sep_path, "w", encoding="utf-8") as f:
        json.dump(separability, f, indent=2)

    return json_path, csv_path, sep_path


def print_evaluation_summary(records: List[Dict[str, Any]]):
    """Print readable ASCII summary table to stdout."""
    print("\n" + "=" * 90)
    print("SECURA AI 2.0 ? FORENSIC EVALUATION SUMMARY")
    print("=" * 90)
    print(f"{'Fixture ID':<28} {'Status':<16} {'ELA Mean':<10} {'DCT BAR':<10} {'Noise Mean':<12} {'Time (ms)'}")
    print("-" * 90)
    for r in records:
        f_id = r["fixture_id"]
        status = r["status"]
        ela_m = r.get("ela", {}).get("mean_absolute_difference")
        ela_str = f"{ela_m:.3f}" if ela_m is not None else "-"
        bar = r.get("dct", {}).get("blocking_artifact_ratio")
        bar_str = f"{bar:.3f}" if bar is not None else "-"
        noise_m = r.get("noise", {}).get("mean_absolute_residual")
        noise_str = f"{noise_m:.3f}" if noise_m is not None else "-"
        total_t = sum(r.get("timings_ms", {}).values())
        print(f"{f_id:<28} {status:<16} {ela_str:<10} {bar_str:<10} {noise_str:<12} {total_t:>7.1f} ms")
    print("=" * 90 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Secura AI 2.0 Forensic Evaluation Harness")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/evaluation",
        help="Target directory for output JSON and CSV reports (default: docs/evaluation)"
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Optional path to user-supplied JSON or CSV manifest of real-world labelled images"
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    output_dir = project_root / args.output_dir

    print(f"[*] Initializing Secura AI 2.0 Forensic Evaluation Harness...")
    print(f"[*] Project root: {project_root}")
    print(f"[*] Generating in-memory deterministic synthetic fixtures...")

    fixtures = generate_all_fixtures()
    print(f"[+] Loaded {len(fixtures)} synthetic fixtures.")

    records = []
    for idx, f in enumerate(fixtures, 1):
        print(f"  [{idx}/{len(fixtures)}] Evaluating {f.fixture_id} ({f.name})...")
        rec = evaluate_fixture(f)
        records.append(rec)

    # Process external manifest if supplied
    if args.manifest:
        manifest_path = Path(args.manifest)
        if manifest_path.exists():
            print(f"[*] Manifest provided: {manifest_path}. Checking samples...")
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    manifest_data = json.load(mf)
                sample_entries = manifest_data.get("samples", [])
                print(f"[*] Manifest contains {len(sample_entries)} entries.")
                # Verify if sample files actually exist
                for entry in sample_entries:
                    sample_path = Path(entry.get("file_path", ""))
                    if not sample_path.is_absolute():
                        sample_path = project_root / sample_path
                    if sample_path.exists() and sample_path.is_file():
                        # Read file bytes in memory
                        with open(sample_path, "rb") as f_in:
                            sample_bytes = f_in.read()
                        ext_fixture = SyntheticFixture(
                            fixture_id=entry.get("sample_id", "EXT-SAMPLE"),
                            name=entry.get("sample_id", "External Sample"),
                            description=entry.get("origin_description", "External labelled sample"),
                            construction_method=entry.get("transformation_history", "Real-world file"),
                            intended_test_property=f"Category: {entry.get('ground_truth_category')}",
                            format_name=entry.get("original_format", "UNKNOWN"),
                            raw_bytes=sample_bytes
                        )
                        ext_rec = evaluate_fixture(ext_fixture)
                        ext_rec["category"] = entry.get("ground_truth_category", "unknown_origin")
                        records.append(ext_rec)
                    else:
                        print(f"  [-] Template/unresolved sample path '{entry.get('file_path')}' not found on disk. Skipped.")
            except Exception as m_err:
                print(f"[!] Error processing manifest: {m_err}")
        else:
            print(f"[!] Warning: Specified manifest '{args.manifest}' does not exist.")
    else:
        print(f"[*] Note: No external labelled manifest provided. Evaluating synthetic fixtures only.")

    separability = compute_feature_separability(records)
    json_path, csv_path, sep_path = export_evaluation_results(records, separability, output_dir)
    print(f"[+] Exported JSON report: {json_path}")
    print(f"[+] Exported CSV metrics: {csv_path}")
    print(f"[+] Exported Separability: {sep_path}")

    print_evaluation_summary(records)


if __name__ == "__main__":
    main()
