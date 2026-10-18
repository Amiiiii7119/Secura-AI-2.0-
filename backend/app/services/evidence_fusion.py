from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Any

from app.schemas.evidence import (
    AIDetectorResult,
    C2PAStatus,
    C2PAValidationResult,
    ComponentError,
    ConsistencySeverity,
    DCTForensicResult,
    ELAForensicResult,
    EvidenceFinding,
    FindingStatus,
    ForensicCategory,
    ImageFormat,
    ImageValidationResult,
    MetadataForensicResult,
    MetadataStatus,
    NoiseResidualResult,
    ThumbnailStatus,
    UnifiedForensicReport,
)

logger = logging.getLogger(__name__)

GLOBAL_FORENSIC_LIMITATIONS: List[str] = [
    "Digital image forensics produces investigative technical observations, not legal certainty of authenticity or artificiality.",
    "Absence of forensic anomalies or absence of metadata/C2PA manifests is standard for web media and does not prove authenticity or AI origin.",
    "Compression variance, spatial noise residuals, and 8x8 DCT grid patterns are physical and algorithmic proxies that degrade under resizing, recompression, and format conversion.",
    "Neural AI detection models evaluate representation proximity to synthetic training distributions and do not constitute physical sensor proof.",
    "Forensic evidence must be evaluated in contextual totality; no single metric or absence thereof provides definitive origin attribution.",
]


def _evaluate_ela_finding(ela_result: Optional[ELAForensicResult], error_present: bool) -> EvidenceFinding:
    if error_present or ela_result is None or ela_result.metrics is None:
        return EvidenceFinding(
            finding_id="FIND-ELA-01",
            category=ForensicCategory.ELA,
            source_component="ErrorLevelAnalysis",
            status=FindingStatus.ANALYSIS_UNAVAILABLE,
            summary="Error Level Analysis is unavailable for this asset.",
            observed_values={},
            interpretation="Analysis engine encountered an operational issue or invalid input.",
            limitations="Unavailable ELA provides no comparative compression variance signal.",
            benign_explanations=["Recompression engine encountered an internal execution failure."],
            related_findings=[],
        )

    m = ela_result.metrics
    mae = round(m.mean_absolute_difference, 4)
    obs_vals = {
        "mean_absolute_difference": mae,
        "max_absolute_difference": round(m.max_absolute_difference, 4),
        "std_absolute_difference": round(m.std_absolute_difference, 4),
        "quality_factor": m.recompression_quality,
        "scale_factor": m.scale_factor,
    }

    if mae > 12.0:
        status = FindingStatus.EVIDENCE_OBSERVED
        summary = f"Elevated uniform recompression error level observed (MAE: {mae:.2f}/255 at Q{m.recompression_quality})."
        interpretation = "Asset exhibits high error variance when re-saved at reference JPEG quality factor."
    else:
        status = FindingStatus.NO_ANOMALY_OBSERVED
        summary = f"Recompression error level remains low and uniform (MAE: {mae:.2f}/255 at Q{m.recompression_quality})."
        interpretation = "Pixel delta distribution is consistent with single-generation compression or baseline raster properties."

    return EvidenceFinding(
        finding_id="FIND-ELA-01",
        category=ForensicCategory.ELA,
        source_component="ErrorLevelAnalysis",
        status=status,
        summary=summary,
        observed_values=obs_vals,
        interpretation=interpretation,
        limitations="ELA identifies recompression error differentials against a fixed quality factor (Q90). It does not localize specific tampered regions or detect non-JPEG synthetic imagery.",
        benign_explanations=[
            "High spatial-frequency textures, edge content, and physical noise elevate ELA error naturally",
            "Images saved at quality factors far from Q90 exhibit higher baseline difference across the entire raster",
        ],
        related_findings=[],
    )


def _evaluate_dct_finding(dct_result: Optional[DCTForensicResult], error_present: bool) -> EvidenceFinding:
    if error_present or dct_result is None or dct_result.metrics is None:
        return EvidenceFinding(
            finding_id="FIND-DCT-01",
            category=ForensicCategory.DCT,
            source_component="DCTAnalysis",
            status=FindingStatus.ANALYSIS_UNAVAILABLE,
            summary="DCT frequency block analysis could not be completed for this asset.",
            observed_values={},
            interpretation="Analysis engine encountered an operational issue or invalid input.",
            limitations="Unavailable DCT analysis provides no frequency-domain grid signal.",
            benign_explanations=["DCT block analysis engine encountered an internal execution failure."],
            related_findings=[],
        )

    m = dct_result.metrics
    bar = round(m.blocking_artifact_ratio, 4)
    obs_vals = {
        "blocking_artifact_ratio": bar,
        "boundary_discontinuity": round(m.boundary_discontinuity, 4),
        "internal_discontinuity": round(m.internal_discontinuity, 4),
        "mean_block_energy": round(m.mean_block_energy, 4),
        "total_blocks": m.total_blocks,
    }

    if bar > 1.05:
        status = FindingStatus.EVIDENCE_OBSERVED
        summary = f"8x8 block-boundary discontinuity is elevated above internal baseline (BAR: {bar:.4f} > 1.05)."
        interpretation = "Harmonic discontinuity aligned with an 8x8 spatial grid, consistent with discrete JPEG quantization boundaries."
    elif bar < 0.95:
        status = FindingStatus.EVIDENCE_OBSERVED
        summary = f"8x8 block boundaries exhibit lower discontinuity than internal reference (BAR: {bar:.4f} < 0.95)."
        interpretation = "Internal step variance exceeds boundary steps; consistent with uncompressed, resampled, or synthetic raster data."
    else:
        status = FindingStatus.NO_ANOMALY_OBSERVED
        summary = f"8x8 block boundary and internal discontinuities are balanced (BAR: {bar:.4f} in [0.95, 1.05])."
        interpretation = "Frequency-domain step discontinuity shows no pronounced 8x8 grid alignment."

    return EvidenceFinding(
        finding_id="FIND-DCT-01",
        category=ForensicCategory.DCT,
        source_component="DCTAnalysis",
        status=status,
        summary=summary,
        observed_values=obs_vals,
        interpretation=interpretation,
        limitations="BAR reflects spatial differences aligned to an 8x8 grid. Resizing, rotation, or anti-aliasing disrupts grid alignment without altering content.",
        benign_explanations=[
            "Non-JPEG native rendering or format conversion (e.g. synthetic PNG, screenshots)",
            "Downsampling or affine transformations that misaligned original 8x8 block boundaries",
            "Images saved at high quality factors (Q > 95) exhibit negligible quantization boundaries",
        ],
        related_findings=[],
    )


def _evaluate_noise_finding(noise_result: Optional[NoiseResidualResult], error_present: bool) -> EvidenceFinding:
    if error_present or noise_result is None or noise_result.metrics is None:
        return EvidenceFinding(
            finding_id="FIND-NOISE-01",
            category=ForensicCategory.NOISE_RESIDUAL,
            source_component="NoiseResidualAnalysis",
            status=FindingStatus.ANALYSIS_UNAVAILABLE,
            summary="High-pass noise residual analysis could not be completed.",
            observed_values={},
            interpretation="Noise extraction engine encountered an operational issue.",
            limitations="Unavailable noise analysis provides no high-frequency spatial residual signal.",
            benign_explanations=["Noise analysis operator encountered an execution error."],
            related_findings=[],
        )

    m = noise_result.metrics
    mean_res = round(m.mean_absolute_residual, 4)
    obs_vals = {
        "mean_absolute_residual": mean_res,
        "std_residual": round(m.std_residual, 4),
        "max_residual": round(m.max_residual, 4),
        "noise_energy": round(m.noise_energy, 4),
        "snr_estimate_db": round(m.snr_estimate_db, 2) if m.snr_estimate_db is not None else None,
    }

    if mean_res > 10.0:
        status = FindingStatus.EVIDENCE_OBSERVED
        summary = f"Elevated high-frequency spatial noise residual energy (Mean: {mean_res:.2f}, Energy: {m.noise_energy:.2f})."
        interpretation = "Substantial high-pass energy isolated by 3x3 discrete Laplacian operator."
    else:
        status = FindingStatus.NO_ANOMALY_OBSERVED
        summary = f"High-frequency spatial noise residual is moderate (Mean: {mean_res:.2f}, Energy: {m.noise_energy:.2f})."
        interpretation = "Residual distribution is consistent with standard photographic grain or smooth computer graphics."

    return EvidenceFinding(
        finding_id="FIND-NOISE-01",
        category=ForensicCategory.NOISE_RESIDUAL,
        source_component="NoiseResidualAnalysis",
        status=status,
        summary=summary,
        observed_values=obs_vals,
        interpretation=interpretation,
        limitations="Laplacian residuals represent a 2D spatial high-pass filtering proxy. They do not constitute a calibrated physical sensor PRNU model and cannot definitively identify synthetic AI generation.",
        benign_explanations=[
            "High ISO analog sensor grain or digital amplification",
            "Sharpening or unsharp mask post-processing filters",
            "Physically rough or textured subject matter",
        ],
        related_findings=[],
    )


def _evaluate_c2pa_finding(c2pa_result: Optional[C2PAValidationResult], error_present: bool) -> EvidenceFinding:
    if error_present or c2pa_result is None or c2pa_result.status in (C2PAStatus.ANALYSIS_UNAVAILABLE, C2PAStatus.C2PA_UNAVAILABLE):
        return EvidenceFinding(
            finding_id="FIND-C2PA-01",
            category=ForensicCategory.C2PA,
            source_component="C2PAInspector",
            status=FindingStatus.ANALYSIS_UNAVAILABLE,
            summary="C2PA provenance manifest inspection could not be completed.",
            observed_values={"sdk_available": c2pa_result.sdk_available if c2pa_result else False},
            interpretation="Inspection engine encountered an operational issue or SDK unavailability.",
            limitations="C2PA inspection status cannot be verified.",
            benign_explanations=["Official c2pa-python SDK was unavailable or input stream failed validation."],
            related_findings=[],
        )

    if c2pa_result.status in (C2PAStatus.ANALYSIS_FAILED, C2PAStatus.C2PA_INSPECTION_ERROR):
        return EvidenceFinding(
            finding_id="FIND-C2PA-01",
            category=ForensicCategory.C2PA,
            source_component="C2PAInspector",
            status=FindingStatus.ANALYSIS_FAILED,
            summary="C2PA provenance inspection failed due to a container parser error.",
            observed_values={"sdk_available": True},
            interpretation="An unexpected error occurred while parsing the C2PA JUMBF stream.",
            limitations="Manifest status could not be established.",
            benign_explanations=["Malformed JUMBF encapsulation box or unsupported container variant."],
            related_findings=[],
        )

    obs_vals = {
        "status": c2pa_result.status.value,
        "manifest_present": c2pa_result.manifest_present,
        "signature_valid": c2pa_result.signature_valid,
        "signer_trusted": c2pa_result.signer_trusted,
        "validation_status": c2pa_result.validation_status,
        "claim_generator": c2pa_result.claims.claim_generator if c2pa_result.claims else None,
        "ingredients_count": c2pa_result.claims.ingredients_count if c2pa_result.claims else 0,
    }

    if "VERIFIED GENERATIVE AI ORIGIN" in (c2pa_result.provenance_notes or ""):
        status = FindingStatus.EVIDENCE_OBSERVED
        summary = "Cryptographically signed C2PA provenance credentials certify synthetic AI generation (Created by Google Generative AI / trainedAlgorithmicMedia)."
        interpretation = "Digital provenance credentials cryptographically signed and verified declare this media was synthesized using generative AI (SynthID imperceptible watermark applied)."
    elif c2pa_result.status in (C2PAStatus.SIGNATURE_VALID, C2PAStatus.C2PA_PRESENT_AND_VALID):
        status = FindingStatus.PRESENT
        summary = "Cryptographically valid C2PA provenance manifest verified with trusted certificate path."
        interpretation = "A signed cryptographic manifest is present and successfully validated against root CA trust lists."
    elif c2pa_result.status == C2PAStatus.SIGNER_UNTRUSTED:
        status = FindingStatus.UNTRUSTED
        summary = f"C2PA manifest signature is valid, but signer certificate is untrusted: {c2pa_result.trust_validation_status}."
        interpretation = "Signature is mathematically intact, but the signing certificate is self-signed or not anchored in a public trust list."
    elif c2pa_result.status in (C2PAStatus.SIGNATURE_INVALID, C2PAStatus.C2PA_PRESENT_WITH_VALIDATION_ISSUES):
        status = FindingStatus.INVALID
        summary = f"C2PA manifest validation failure or data tampering detected: {c2pa_result.trust_validation_status or c2pa_result.validation_status}."
        interpretation = "A provenance manifest exists but cryptographic hash binding or signature verification failed (tampered asset)."
    else:
        # NO_MANIFEST / C2PA_MISSING
        status = FindingStatus.ABSENT
        summary = "No C2PA provenance manifest detected in image container (confirmed absent)."
        interpretation = "Image lacks signed cryptographic provenance headers (standard for ordinary camera and web imagery)."

    return EvidenceFinding(
        finding_id="FIND-C2PA-01",
        category=ForensicCategory.C2PA,
        source_component="C2PAInspector",
        status=status,
        summary=summary,
        observed_values=obs_vals,
        interpretation=interpretation,
        limitations="Valid C2PA provenance verifies that claims were signed by the identity key holder; it does not authenticate real-world facts depicted in the pixels. Crucially, missing C2PA manifests are standard on the internet and must never be treated as evidence of synthetic AI generation.",
        benign_explanations=[
            "Image was captured on a device lacking C2PA hardware signing support",
            "C2PA manifest stripped by social media platform, messaging app, or web optimizer",
        ],
        related_findings=[],
    )


def _evaluate_metadata_finding(metadata_result: Optional[MetadataForensicResult], error_present: bool) -> EvidenceFinding:
    if error_present or metadata_result is None:
        return EvidenceFinding(
            finding_id="FIND-META-01",
            category=ForensicCategory.METADATA,
            source_component="MetadataInspector",
            status=FindingStatus.ANALYSIS_UNAVAILABLE,
            summary="Metadata extraction could not be completed for this asset.",
            observed_values={},
            interpretation="EXIF, XMP, and text chunk metadata could not be inspected.",
            limitations="Unavailable metadata prevents evaluation of container headers.",
            benign_explanations=["Metadata parsing was interrupted by a component error."],
            related_findings=[],
        )

    inv = metadata_result.inventory
    cam = metadata_result.camera_metadata
    gps = metadata_result.gps_summary

    obs_vals = {
        "inventory_status": inv.status.value,
        "detected_structures": inv.detected_structures,
        "exif_tag_count": inv.exif_tag_count,
        "xmp_present": inv.xmp_packet_present,
        "png_text_count": inv.png_text_chunks_count,
        "make": cam.make if cam else None,
        "model": cam.model if cam else None,
        "software": cam.software if cam else None,
        "orientation_tag": cam.orientation_tag if cam else None,
        "date_time_original": cam.date_time_original if cam else None,
        "gps_present": gps.gps_present,
        "gps_tag_count": gps.tag_count,
        "gps_coordinates_redacted": gps.coordinates_redacted,
    }

    if inv.status == MetadataStatus.PRESENT:
        status = FindingStatus.PRESENT
        summary = f"Container metadata present ({len(inv.detected_structures)} structures detected: {', '.join(inv.detected_structures)})."
        interpretation = f"Extracted {inv.exif_tag_count} EXIF tags. Camera: {cam.make or 'Unspecified'} {cam.model or ''}."
    elif inv.status == MetadataStatus.PARTIAL:
        status = FindingStatus.PARTIAL
        summary = f"Partial metadata detected ({len(inv.detected_structures)} structures present with header irregularities)."
        interpretation = "Some metadata structures were extracted, but others exhibited malformed offsets or decoding issues."
    elif inv.status == MetadataStatus.MALFORMED:
        status = FindingStatus.INVALID
        summary = "Container metadata headers are present but structurally malformed or corrupt."
        interpretation = "Container header contains broken offsets, invalid byte tags, or corrupt IFD sequences."
    elif inv.status == MetadataStatus.ANALYSIS_FAILED:
        status = FindingStatus.ANALYSIS_FAILED
        summary = "Metadata analysis failed due to an unexpected parsing error."
        interpretation = "Parser encountered an unhandled exception while inspecting image metadata."
    else:
        # ABSENT
        status = FindingStatus.ABSENT
        summary = "No container metadata (EXIF, XMP, or text chunks) present in asset (confirmed absent)."
        interpretation = "Asset has no recorded camera or authoring metadata tags (standard for web media, screenshots, and privacy-stripped exports)."

    return EvidenceFinding(
        finding_id="FIND-META-01",
        category=ForensicCategory.METADATA,
        source_component="MetadataInspector",
        status=status,
        summary=summary,
        observed_values=obs_vals,
        interpretation=interpretation,
        limitations="Camera make, model, software, and timestamp tags are user-editable text fields that lack cryptographic guarantees. Conversely, absence of metadata is ubiquitous across web platforms and must never be interpreted as evidence of synthetic AI generation.",
        benign_explanations=[
            "Metadata removed by social media, messaging apps, or privacy tools to protect user location",
            "Image exported via 'Save for Web' in graphic editing software",
        ],
        related_findings=[],
    )


def _evaluate_thumbnail_finding(metadata_result: Optional[MetadataForensicResult], error_present: bool) -> EvidenceFinding:
    if error_present or metadata_result is None:
        return EvidenceFinding(
            finding_id="FIND-THUMB-01",
            category=ForensicCategory.THUMBNAIL,
            source_component="ThumbnailAnalyzer",
            status=FindingStatus.ANALYSIS_UNAVAILABLE,
            summary="Embedded thumbnail inspection is unavailable.",
            observed_values={},
            interpretation="Thumbnail stream could not be evaluated.",
            limitations="Unavailable thumbnail analysis provides no comparative signal.",
            benign_explanations=["Metadata inspection was unavailable."],
            related_findings=[],
        )

    t = metadata_result.thumbnail_analysis
    obs_vals = {
        "status": t.status.value,
        "has_thumbnail": t.has_thumbnail,
        "thumbnail_dimensions": t.thumbnail_dimensions,
        "similarity_score": t.similarity_score,
        "mean_absolute_difference": t.mean_absolute_difference,
        "aspect_ratio_thumbnail": t.thumbnail_aspect_ratio,
        "aspect_ratio_primary": t.primary_aspect_ratio,
        "has_preview_data_url": bool(t.thumbnail_data_url),
    }

    if t.status in (ThumbnailStatus.COMPARABLE, ThumbnailStatus.THUMBNAIL_FOUND):
        status = FindingStatus.NO_ANOMALY_OBSERVED
        sim_pct = ((t.similarity_score or 0) * 100)
        summary = f"Embedded IFD1 thumbnail verified ({t.thumbnail_dimensions.get('width')}x{t.thumbnail_dimensions.get('height')}) and visually consistent with primary raster (Similarity: {sim_pct:.1f}%)."
        interpretation = "Thumbnail content is visually consistent with primary raster within expected downsampling tolerances."
    elif t.status == ThumbnailStatus.MISMATCH_OBSERVED:
        status = FindingStatus.EVIDENCE_OBSERVED
        sim_pct = ((t.similarity_score or 0) * 100)
        summary = f"Embedded IFD1 thumbnail exhibits visual discrepancy with primary image raster (Similarity: {sim_pct:.1f}%)."
        interpretation = "Visual divergence observed between thumbnail preview and primary raster below 0.85 heuristic threshold."
    elif t.status == ThumbnailStatus.THUMBNAIL_INVALID:
        status = FindingStatus.INVALID
        summary = "Embedded thumbnail stream found in container but contains invalid or undecodable JPEG data."
        interpretation = "Thumbnail offset exists in EXIF IFD1 but JPEG stream is corrupted."
    elif t.status in (ThumbnailStatus.THUMBNAIL_ABSENT, ThumbnailStatus.NO_THUMBNAIL):
        status = FindingStatus.ABSENT
        summary = "Analysis confirmed absence of embedded IFD1 thumbnail stream in container."
        interpretation = "Container does not include an embedded preview thumbnail (standard for web media, mobile exports, and PNG files)."
    else:
        status = FindingStatus.ANALYSIS_UNAVAILABLE
        summary = f"Embedded thumbnail is present but unavailable for comparison ({t.status.value})."
        interpretation = "Thumbnail stream could not be completely aligned or compared."

    return EvidenceFinding(
        finding_id="FIND-THUMB-01",
        category=ForensicCategory.THUMBNAIL,
        source_component="ThumbnailAnalyzer",
        status=status,
        summary=summary,
        observed_values=obs_vals,
        interpretation=interpretation,
        limitations="Embedded IFD1 thumbnails are optional metadata previews created primarily by digital cameras. Absence of a thumbnail is completely normal for web imagery and mobile devices.",
        benign_explanations=[
            "Image was captured on a smartphone or exported by software that omits embedded IFD1 thumbnails",
            "Thumbnail stream stripped during image compression or upload optimization",
        ],
        related_findings=[],
    )


def _evaluate_consistency_finding(metadata_result: Optional[MetadataForensicResult], error_present: bool) -> EvidenceFinding:
    if error_present or metadata_result is None:
        return EvidenceFinding(
            finding_id="FIND-CONSIST-01",
            category=ForensicCategory.CONSISTENCY,
            source_component="ContainerConsistencyChecker",
            status=FindingStatus.ANALYSIS_UNAVAILABLE,
            summary="Container consistency inspection is unavailable.",
            observed_values={},
            interpretation="Cross-field and container concordance could not be verified.",
            limitations="Unavailable consistency checks provide no container integrity signals.",
            benign_explanations=["Metadata inspection was unavailable."],
            related_findings=[],
        )

    c = metadata_result.container_consistency
    inconsistencies = [o for o in c.observations if o.severity == ConsistencySeverity.INCONSISTENCY]
    obs_vals = {
        "status": c.status,
        "observation_count": len(c.observations),
        "inconsistency_count": len(inconsistencies),
        "checks_evaluated": [o.check_name for o in c.observations],
    }

    if inconsistencies:
        status = FindingStatus.EVIDENCE_OBSERVED
        summary = f"Container consistency checks identified {len(inconsistencies)} discrepancy/discrepancies."
        interpretation = "; ".join(o.observed_state for o in inconsistencies)
    else:
        status = FindingStatus.NO_ANOMALY_OBSERVED
        summary = "All evaluated container fields, dimensions, and timestamps are concordant."
        interpretation = "No discrepancies observed across evaluated container layers."

    return EvidenceFinding(
        finding_id="FIND-CONSIST-01",
        category=ForensicCategory.CONSISTENCY,
        source_component="ContainerConsistencyChecker",
        status=status,
        summary=summary,
        observed_values=obs_vals,
        interpretation=interpretation,
        limitations="Container discrepancies alone do not establish malicious tampering; they frequently arise from benign software operations such as non-destructive cropping or camera clock battery loss.",
        benign_explanations=[
            "Cropping or resizing by software that omitted updating ExifImageWidth/Height tags",
            "Camera clock desynchronization or clock battery depletion",
            "File format conversion without EXIF synchronization",
        ],
        related_findings=[],
    )


def _evaluate_ai_detector_finding(ai_result: Optional[AIDetectorResult], error_present: bool) -> EvidenceFinding:
    if error_present or ai_result is None or not ai_result.available:
        return EvidenceFinding(
            finding_id="FIND-AI-01",
            category=ForensicCategory.AI_DETECTOR,
            source_component="AIImageDetector",
            status=FindingStatus.ANALYSIS_UNAVAILABLE,
            summary="AI-generated image classification is unavailable.",
            observed_values={"model_status": ai_result.model_status.value if ai_result else "NOT_INVOKED"},
            interpretation="Neural vision classifier was not executed or weights were unprovisioned.",
            limitations="Unavailable detector provides no machine-learning classification signal.",
            benign_explanations=["AI detector service was not initialized or disabled."],
            related_findings=[],
        )

    obs_vals = {
        "model_name": ai_result.model_name,
        "model_version": ai_result.model_version,
        "predicted_class": ai_result.predicted_class,
        "raw_score": ai_result.raw_score,
        "margin": ai_result.uncalibrated_margin,
        "probabilities": ai_result.probabilities,
        "device_used": ai_result.device_used,
        "latency_ms": ai_result.inference_latency_ms,
    }

    is_ai = ai_result.predicted_class == "AI_GENERATED"
    margin_pct = ((ai_result.uncalibrated_margin or 0.0) * 100)

    if is_ai:
        status = FindingStatus.EVIDENCE_OBSERVED
        summary = f"AI classifier ({ai_result.model_name}) predicts synthetic/AI origin (Raw score: {ai_result.raw_score:.2f}, Margin: {margin_pct:.1f}%)."
        interpretation = "Deep neural representation exhibits high similarity to known generative diffusion/transformer distributions."
    else:
        status = FindingStatus.NO_ANOMALY_OBSERVED
        summary = f"AI classifier ({ai_result.model_name}) predicts authentic photographic origin (Raw score: {ai_result.raw_score:.2f}, Margin: {margin_pct:.1f}%)."
        interpretation = "Deep neural representation is consistent with natural photographic capture distributions."

    return EvidenceFinding(
        finding_id="FIND-AI-01",
        category=ForensicCategory.AI_DETECTOR,
        source_component="AIImageDetector",
        status=status,
        summary=summary,
        observed_values=obs_vals,
        interpretation=interpretation,
        limitations="Neural classifiers evaluate representation proximity to synthetic training corpora. They do not constitute physical sensor proof and can degrade under heavy recompression or unseen generator architectures.",
        benign_explanations=[
            "Artistic photography with smooth lighting or digital color grading can increase synthetic proximity",
            "Heavily denoised camera imagery may trigger synthetic feature detectors",
        ],
        related_findings=[],
    )


def synthesize_forensic_evidence(
    image_validation: ImageValidationResult,
    ela_result: Optional[ELAForensicResult],
    dct_result: Optional[DCTForensicResult],
    noise_result: Optional[NoiseResidualResult],
    c2pa_result: Optional[C2PAValidationResult],
    metadata_result: Optional[MetadataForensicResult],
    component_errors: List[ComponentError],
    evaluation_time: Optional[datetime] = None,
    ai_detection_result: Optional[AIDetectorResult] = None,
) -> UnifiedForensicReport:
    """
    Consolidate completed forensic results into a unified, explainable evidence report.
    Produces deterministic output across all 8 forensic layers without computing an aggregate authenticity percentage.
    """
    eval_utc = evaluation_time or datetime.now(timezone.utc)
    err_components = {e.component for e in component_errors}

    # Evaluate individual findings across 8 forensic categories
    finding_ela = _evaluate_ela_finding(ela_result, "ErrorLevelAnalysis" in err_components)
    finding_dct = _evaluate_dct_finding(dct_result, "DCTAnalysis" in err_components)
    finding_noise = _evaluate_noise_finding(noise_result, "NoiseResidualAnalysis" in err_components)
    finding_c2pa = _evaluate_c2pa_finding(c2pa_result, "C2PAInspector" in err_components)
    finding_meta = _evaluate_metadata_finding(metadata_result, "MetadataInspector" in err_components)
    finding_thumb = _evaluate_thumbnail_finding(metadata_result, "MetadataInspector" in err_components)
    finding_consist = _evaluate_consistency_finding(metadata_result, "MetadataInspector" in err_components)
    finding_ai = _evaluate_ai_detector_finding(ai_detection_result, "AIImageDetector" in err_components)

    # Cross-layer correlations
    if (
        finding_thumb.status == FindingStatus.EVIDENCE_OBSERVED
        and finding_consist.status == FindingStatus.EVIDENCE_OBSERVED
    ):
        finding_thumb.related_findings.append("FIND-CONSIST-01")
        finding_consist.related_findings.append("FIND-THUMB-01")

    if (
        image_validation.detected_format == ImageFormat.PNG
        and finding_dct.status == FindingStatus.EVIDENCE_OBSERVED
        and finding_dct.observed_values.get("blocking_artifact_ratio", 0) > 1.05
    ):
        finding_dct.related_findings.append("FIND-META-01")
        finding_meta.related_findings.append("FIND-DCT-01")

    all_findings = [
        finding_ela,
        finding_dct,
        finding_noise,
        finding_c2pa,
        finding_meta,
        finding_thumb,
        finding_consist,
    ]
    if ai_detection_result is not None:
        all_findings.append(finding_ai)

    # Group findings by category
    findings_by_cat: Dict[str, List[EvidenceFinding]] = {}
    for f in all_findings:
        cat_key = f.category.value
        if cat_key not in findings_by_cat:
            findings_by_cat[cat_key] = []
        findings_by_cat[cat_key].append(f)

    # Component availability mapping
    avail: Dict[str, str] = {
        "ErrorLevelAnalysis": "AVAILABLE" if (finding_ela.status != FindingStatus.ANALYSIS_UNAVAILABLE) else "UNAVAILABLE",
        "DCTAnalysis": "AVAILABLE" if (finding_dct.status != FindingStatus.ANALYSIS_UNAVAILABLE) else "UNAVAILABLE",
        "NoiseResidualAnalysis": "AVAILABLE" if (finding_noise.status != FindingStatus.ANALYSIS_UNAVAILABLE) else "UNAVAILABLE",
        "C2PAInspector": "AVAILABLE" if (finding_c2pa.status != FindingStatus.ANALYSIS_UNAVAILABLE) else "UNAVAILABLE",
        "MetadataInspector": "AVAILABLE" if (finding_meta.status != FindingStatus.ANALYSIS_UNAVAILABLE) else "UNAVAILABLE",
        "ThumbnailAnalyzer": "AVAILABLE" if (finding_thumb.status != FindingStatus.ANALYSIS_UNAVAILABLE) else "UNAVAILABLE",
        "ContainerConsistencyChecker": "AVAILABLE" if (finding_consist.status != FindingStatus.ANALYSIS_UNAVAILABLE) else "UNAVAILABLE",
    }
    if ai_detection_result is not None:
        avail["AIImageDetector"] = "AVAILABLE" if (finding_ai.status != FindingStatus.ANALYSIS_UNAVAILABLE) else "UNAVAILABLE"
    for err in component_errors:
        if err.component in avail:
            avail[err.component] = "FAILED"

    failed_count = sum(1 for v in avail.values() if v == "FAILED")
    unavail_count = sum(1 for v in avail.values() if v == "UNAVAILABLE")
    if failed_count == 0 and unavail_count == 0:
        completion_status = "COMPLETE"
    elif failed_count < len(avail):
        completion_status = "PARTIAL_SUCCESS"
    else:
        completion_status = "FAILED"

    # Build objective, cautious summary
    obs_count = sum(1 for f in all_findings if f.status == FindingStatus.EVIDENCE_OBSERVED)
    no_anom_count = sum(1 for f in all_findings if f.status == FindingStatus.NO_ANOMALY_OBSERVED)
    absent_count = sum(1 for f in all_findings if f.status == FindingStatus.ABSENT)
    untrusted_count = sum(1 for f in all_findings if f.status == FindingStatus.UNTRUSTED)
    invalid_count = sum(1 for f in all_findings if f.status == FindingStatus.INVALID)
    unavail_cnt = sum(1 for f in all_findings if f.status == FindingStatus.ANALYSIS_UNAVAILABLE)

    summary_parts = [
        f"Consolidated analysis of {image_validation.width}x{image_validation.height} {image_validation.detected_format.value} asset across 8 diagnostic categories.",
        f"Findings breakdown: {obs_count} evidence observed, {no_anom_count} no anomaly observed, {absent_count} absent, {untrusted_count} untrusted, {invalid_count} invalid, {unavail_cnt} unavailable.",
    ]

    if finding_c2pa.status in (FindingStatus.PRESENT, FindingStatus.EVIDENCE_OBSERVED):
        summary_parts.append("Cryptographically signed C2PA provenance manifest verified.")
    elif finding_c2pa.status == FindingStatus.UNTRUSTED:
        summary_parts.append("C2PA signature valid, but signer certificate untrusted.")
    elif finding_c2pa.status == FindingStatus.INVALID:
        summary_parts.append("C2PA manifest tampering or signature mismatch detected.")
    elif finding_c2pa.status == FindingStatus.ABSENT:
        summary_parts.append("C2PA manifest absent (standard for consumer and web media).")

    if finding_ai.status == FindingStatus.EVIDENCE_OBSERVED:
        summary_parts.append(f"AI classifier ({finding_ai.observed_values.get('model_name', 'Detector')}) indicates synthetic AI image generation.")
    elif finding_ai.status == FindingStatus.NO_ANOMALY_OBSERVED:
        summary_parts.append(f"AI classifier ({finding_ai.observed_values.get('model_name', 'Detector')}) indicates natural photographic capture.")

    if finding_thumb.status == FindingStatus.EVIDENCE_OBSERVED:
        summary_parts.append("Embedded thumbnail visual mismatch observed (commonly resulting from post-capture cropping).")

    summary_parts.append(
        "No aggregate authenticity score or AI probability is computed. Each finding must be interpreted within its stated physical and operational limitations."
    )

    cautious_summary = " ".join(summary_parts)

    return UnifiedForensicReport(
        report_schema_version="1.0.0",
        analysis_completion_status=completion_status,
        evaluated_at_utc=eval_utc,
        total_findings_count=len(all_findings),
        findings=all_findings,
        findings_by_category=findings_by_cat,
        component_availability=avail,
        cautious_summary=cautious_summary,
        global_limitations=GLOBAL_FORENSIC_LIMITATIONS,
    )
