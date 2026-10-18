from datetime import datetime, timezone
import pytest

from app.schemas.evidence import (
    C2PAStatus,
    C2PAValidationResult,
    CameraMetadata,
    ComponentError,
    ConsistencyObservation,
    ConsistencySeverity,
    ContainerConsistencyResult,
    DCTForensicResult,
    DCTMetrics,
    ELAForensicResult,
    ELAMetrics,
    FindingStatus,
    ForensicCategory,
    GPSMetadataSummary,
    ImageFormat,
    ImageValidationResult,
    MetadataForensicResult,
    MetadataInventory,
    MetadataStatus,
    NoiseResidualMetrics,
    NoiseResidualResult,
    ThumbnailAnalysisResult,
    ThumbnailStatus,
)
from app.services.evidence_fusion import synthesize_forensic_evidence


def _dummy_validation(fmt=ImageFormat.JPEG, w=200, h=150) -> ImageValidationResult:
    return ImageValidationResult(
        is_valid=True,
        detected_format=fmt,
        width=w,
        height=h,
        pixel_count=w * h,
        color_mode="RGB",
        file_size_bytes=5000,
        mime_type="image/jpeg" if fmt == ImageFormat.JPEG else "image/png",
    )


def _dummy_ela(mean_err=3.5) -> ELAForensicResult:
    return ELAForensicResult(
        status="SUCCESS",
        metrics=ELAMetrics(
            recompression_quality=90,
            scale_factor=15.0,
            mean_absolute_difference=mean_err,
            max_absolute_difference=25.0,
            std_absolute_difference=3.0,
        ),
        heatmap_data_url="data:image/png;base64,FAKE",
        analysis_notes="Test ELA notes",
    )


def _dummy_dct(bar=1.12) -> DCTForensicResult:
    return DCTForensicResult(
        status="SUCCESS",
        metrics=DCTMetrics(
            block_size=8,
            analyzed_width=200,
            analyzed_height=144,
            total_blocks=450,
            boundary_discontinuity=4.5,
            internal_discontinuity=4.0,
            blocking_artifact_ratio=bar,
            mean_block_energy=16.0,
        ),
        visualization_data_url="data:image/png;base64,FAKE",
        analysis_notes="Test DCT notes",
    )


def _dummy_noise(mean_res=1.8) -> NoiseResidualResult:
    return NoiseResidualResult(
        status="SUCCESS",
        metrics=NoiseResidualMetrics(
            filter_type="3x3 Discrete Laplacian",
            mean_absolute_residual=mean_res,
            std_residual=2.2,
            max_residual=15.0,
            noise_energy=4.84,
            snr_estimate_db=26.5,
        ),
        visualization_data_url="data:image/png;base64,FAKE",
        analysis_notes="Test noise notes",
    )


def _dummy_c2pa(status=C2PAStatus.C2PA_MISSING) -> C2PAValidationResult:
    return C2PAValidationResult(
        status=status,
        sdk_available=True,
        manifest_present=(status == C2PAStatus.C2PA_PRESENT_AND_VALID),
        validation_status="NO_MANIFEST" if status == C2PAStatus.C2PA_MISSING else "VALID",
        manifest_data=None,
        claims=None,
        provenance_notes="Test C2PA notes",
    )


def _dummy_metadata(
    meta_status=MetadataStatus.PRESENT,
    thumb_status=ThumbnailStatus.COMPARABLE,
    has_inconsistency=False,
) -> MetadataForensicResult:
    obs = []
    if has_inconsistency:
        obs.append(
            ConsistencyObservation(
                check_name="dimension_concordance",
                severity=ConsistencySeverity.INCONSISTENCY,
                observed_state="Decoded 200x150 differs from EXIF 400x300",
                benign_explanation="Cropped in editor without rewriting header",
            )
        )

    return MetadataForensicResult(
        inventory=MetadataInventory(
            status=meta_status,
            detected_structures=["EXIF"] if meta_status == MetadataStatus.PRESENT else [],
            exif_tag_count=15 if meta_status == MetadataStatus.PRESENT else 0,
            xmp_packet_present=False,
            png_text_chunks_count=0,
        ),
        camera_metadata=CameraMetadata(
            make="Nikon" if meta_status == MetadataStatus.PRESENT else None,
            model="Z8" if meta_status == MetadataStatus.PRESENT else None,
            software="Adobe Photoshop" if meta_status == MetadataStatus.PRESENT else None,
        ),
        gps_summary=GPSMetadataSummary(
            gps_present=True,
            gps_status="DETECTED_AND_REDACTED",
            tag_count=3,
            coordinates_redacted=True,
            latitude=None,
            longitude=None,
        ),
        thumbnail_analysis=ThumbnailAnalysisResult(
            status=thumb_status,
            has_thumbnail=(thumb_status in [ThumbnailStatus.COMPARABLE, ThumbnailStatus.MISMATCH_OBSERVED]),
            thumbnail_format="JPEG" if thumb_status != ThumbnailStatus.NO_THUMBNAIL else None,
            thumbnail_dimensions={"width": 40, "height": 30} if thumb_status != ThumbnailStatus.NO_THUMBNAIL else None,
            primary_dimensions={"width": 200, "height": 150},
            similarity_score=0.98 if thumb_status == ThumbnailStatus.COMPARABLE else 0.55 if thumb_status == ThumbnailStatus.MISMATCH_OBSERVED else None,
            mean_absolute_difference=4.0 if thumb_status == ThumbnailStatus.COMPARABLE else 45.0 if thumb_status == ThumbnailStatus.MISMATCH_OBSERVED else None,
            comparison_notes="Test thumbnail notes",
        ),
        container_consistency=ContainerConsistencyResult(
            status="DISCREPANCIES_OBSERVED" if has_inconsistency else "CONSISTENT",
            observations=obs,
            notes="Test consistency notes",
        ),
        analysis_notes="Test notes",
    )


def test_fusion_all_components_successful():
    val = _dummy_validation()
    ela = _dummy_ela()
    dct = _dummy_dct()
    noise = _dummy_noise()
    c2pa = _dummy_c2pa(C2PAStatus.C2PA_PRESENT_AND_VALID)
    meta = _dummy_metadata()

    report = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=ela,
        dct_result=dct,
        noise_result=noise,
        c2pa_result=c2pa,
        metadata_result=meta,
        component_errors=[],
    )

    assert report.report_schema_version == "1.0.0"
    assert report.analysis_completion_status == "COMPLETE"
    assert report.total_findings_count == 7
    assert len(report.findings) == 7
    assert len(report.global_limitations) == 5

    # Check findings by category
    assert ForensicCategory.ELA.value in report.findings_by_category
    assert ForensicCategory.DCT.value in report.findings_by_category
    assert ForensicCategory.NOISE_RESIDUAL.value in report.findings_by_category
    assert ForensicCategory.C2PA.value in report.findings_by_category
    assert ForensicCategory.METADATA.value in report.findings_by_category
    assert ForensicCategory.THUMBNAIL.value in report.findings_by_category
    assert ForensicCategory.CONSISTENCY.value in report.findings_by_category

    # Check component availability
    for comp, avail in report.component_availability.items():
        assert avail == "AVAILABLE"

    # Verify no fabricated authenticity score or AI probability
    dump = report.model_dump()
    assert "probability" not in dump
    assert "confidence_score" not in dump
    assert "authenticity_score" not in dump
    assert "verdict" not in dump


def test_fusion_single_component_failure_isolated():
    val = _dummy_validation()
    # ELA failed
    err = ComponentError(
        component="ErrorLevelAnalysis",
        error_code="ELA_MATRIX_FAULT",
        message="Simulated matrix allocation fault",
    )

    report = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=None,
        dct_result=_dummy_dct(),
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(),
        metadata_result=_dummy_metadata(),
        component_errors=[err],
    )

    assert report.analysis_completion_status == "PARTIAL_SUCCESS"
    assert report.component_availability["ErrorLevelAnalysis"] == "FAILED"
    assert report.component_availability["DCTAnalysis"] == "AVAILABLE"

    # ELA finding is marked unavailable
    ela_finding = next(f for f in report.findings if f.category == ForensicCategory.ELA)
    assert ela_finding.status == FindingStatus.ANALYSIS_UNAVAILABLE
    assert "unavailable" in ela_finding.summary.lower()


def test_fusion_missing_c2pa_is_inconclusive_not_ai_claim():
    val = _dummy_validation()
    report = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=_dummy_ela(),
        dct_result=_dummy_dct(),
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(C2PAStatus.C2PA_MISSING),
        metadata_result=_dummy_metadata(),
        component_errors=[],
    )

    c2pa_finding = next(f for f in report.findings if f.category == ForensicCategory.C2PA)
    assert c2pa_finding.status in (FindingStatus.ABSENT, FindingStatus.INCONCLUSIVE)
    assert "No C2PA provenance manifest detected" in c2pa_finding.summary
    assert "must never be treated as evidence of synthetic AI generation" in c2pa_finding.limitations


def test_fusion_missing_metadata_is_inconclusive():
    val = _dummy_validation()
    meta_absent = _dummy_metadata(meta_status=MetadataStatus.ABSENT, thumb_status=ThumbnailStatus.NO_THUMBNAIL)

    report = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=_dummy_ela(),
        dct_result=_dummy_dct(),
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(),
        metadata_result=meta_absent,
        component_errors=[],
    )

    meta_finding = next(f for f in report.findings if f.category == ForensicCategory.METADATA)
    assert meta_finding.status in (FindingStatus.ABSENT, FindingStatus.INCONCLUSIVE)
    assert "No container metadata" in meta_finding.summary

    thumb_finding = next(f for f in report.findings if f.category == ForensicCategory.THUMBNAIL)
    assert thumb_finding.status in (FindingStatus.ABSENT, FindingStatus.INCONCLUSIVE)


def test_fusion_correlation_linking_thumbnail_and_consistency():
    val = _dummy_validation()
    # Mismatched thumbnail with container inconsistency
    meta = _dummy_metadata(thumb_status=ThumbnailStatus.MISMATCH_OBSERVED, has_inconsistency=True)

    report = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=_dummy_ela(),
        dct_result=_dummy_dct(),
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(),
        metadata_result=meta,
        component_errors=[],
    )

    thumb_f = next(f for f in report.findings if f.category == ForensicCategory.THUMBNAIL)
    consist_f = next(f for f in report.findings if f.category == ForensicCategory.CONSISTENCY)

    assert thumb_f.status == FindingStatus.EVIDENCE_OBSERVED
    assert consist_f.status == FindingStatus.EVIDENCE_OBSERVED
    assert "FIND-CONSIST-01" in thumb_f.related_findings
    assert "FIND-THUMB-01" in consist_f.related_findings


def test_fusion_correlation_linking_png_with_dct_artifacts():
    val_png = _dummy_validation(fmt=ImageFormat.PNG)
    dct_with_bar = _dummy_dct(bar=1.18)

    report = synthesize_forensic_evidence(
        image_validation=val_png,
        ela_result=_dummy_ela(),
        dct_result=dct_with_bar,
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(),
        metadata_result=_dummy_metadata(),
        component_errors=[],
    )

    dct_f = next(f for f in report.findings if f.category == ForensicCategory.DCT)
    meta_f = next(f for f in report.findings if f.category == ForensicCategory.METADATA)

    assert "FIND-META-01" in dct_f.related_findings
    assert "FIND-DCT-01" in meta_f.related_findings


def test_fusion_deterministic_output():
    val = _dummy_validation()
    fixed_time = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)

    r1 = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=_dummy_ela(),
        dct_result=_dummy_dct(),
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(),
        metadata_result=_dummy_metadata(),
        component_errors=[],
        evaluation_time=fixed_time,
    )

    r2 = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=_dummy_ela(),
        dct_result=_dummy_dct(),
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(),
        metadata_result=_dummy_metadata(),
        component_errors=[],
        evaluation_time=fixed_time,
    )

    assert r1.model_dump() == r2.model_dump()


def test_fusion_privacy_no_gps_coordinates_in_findings():
    val = _dummy_validation()
    report = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=_dummy_ela(),
        dct_result=_dummy_dct(),
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(),
        metadata_result=_dummy_metadata(),
        component_errors=[],
    )

    json_str = report.model_dump_json()
    assert "latitude" not in json_str or '"latitude":null' in json_str
    assert "longitude" not in json_str or '"longitude":null' in json_str

    meta_f = next(f for f in report.findings if f.category == ForensicCategory.METADATA)
    assert meta_f.observed_values.get("gps_coordinates_redacted") is True
    assert "latitude" not in meta_f.observed_values
    assert "longitude" not in meta_f.observed_values


def test_fusion_no_binary_data_leakage():
    val = _dummy_validation()
    report = synthesize_forensic_evidence(
        image_validation=val,
        ela_result=_dummy_ela(),
        dct_result=_dummy_dct(),
        noise_result=_dummy_noise(),
        c2pa_result=_dummy_c2pa(),
        metadata_result=_dummy_metadata(),
        component_errors=[],
    )

    json_str = report.model_dump_json()
    assert "data:image/png;base64" not in json_str
