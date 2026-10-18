from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class ImageFormat(str, Enum):
    JPEG = "JPEG"
    PNG = "PNG"


class C2PAStatus(str, Enum):
    C2PA_MISSING = "C2PA_MISSING"
    C2PA_PRESENT_AND_VALID = "C2PA_PRESENT_AND_VALID"
    C2PA_PRESENT_WITH_VALIDATION_ISSUES = "C2PA_PRESENT_WITH_VALIDATION_ISSUES"
    C2PA_UNAVAILABLE = "C2PA_UNAVAILABLE"
    C2PA_INSPECTION_ERROR = "C2PA_INSPECTION_ERROR"
    SIGNER_UNTRUSTED = "SIGNER_UNTRUSTED"
    TRUST_VALIDATION_UNAVAILABLE = "TRUST_VALIDATION_UNAVAILABLE"

    # Mission 16 aliases
    NO_MANIFEST = "C2PA_MISSING"
    MANIFEST_FOUND = "C2PA_PRESENT_AND_VALID"
    SIGNATURE_VALID = "C2PA_PRESENT_AND_VALID"
    SIGNATURE_INVALID = "C2PA_PRESENT_WITH_VALIDATION_ISSUES"
    ANALYSIS_UNAVAILABLE = "C2PA_UNAVAILABLE"
    ANALYSIS_FAILED = "C2PA_INSPECTION_ERROR"

class ComponentError(BaseModel):
    component: str = Field(..., description="Name of the component that encountered an issue")
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Sanitized human-readable error explanation")


class ImageValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Whether the image passed all validation checks")
    detected_format: ImageFormat = Field(..., description="Format verified by magic bytes and Pillow decoder")
    width: int = Field(..., ge=1, description="Image width in pixels")
    height: int = Field(..., ge=1, description="Image height in pixels")
    pixel_count: int = Field(..., ge=1, description="Total number of pixels (width * height)")
    color_mode: str = Field(..., description="Color space mode (e.g. RGB, RGBA, L)")
    file_size_bytes: int = Field(..., ge=1, description="Byte size of uploaded payload")
    mime_type: str = Field(..., description="Canonical MIME type matching detected format")


# --- Error Level Analysis (ELA) ---
class ELAMetrics(BaseModel):
    recompression_quality: int = Field(..., ge=1, le=100, description="JPEG quality factor used for recompression")
    scale_factor: float = Field(..., gt=0.0, description="Multiplier applied to differences for visual normalization")
    mean_absolute_difference: float = Field(..., ge=0.0, description="Mean absolute error across all channels and pixels")
    max_absolute_difference: float = Field(..., ge=0.0, description="Maximum absolute error across all channels and pixels")
    std_absolute_difference: float = Field(..., ge=0.0, description="Standard deviation of absolute pixel error")


class ELAForensicResult(BaseModel):
    status: str = Field(default="SUCCESS", description="Status of the ELA computation (SUCCESS or ERROR)")
    metrics: Optional[ELAMetrics] = Field(default=None, description="Statistical metrics from error level analysis")
    heatmap_data_url: Optional[str] = Field(default=None, description="Data URL with Base64-encoded PNG heatmap visualization")
    analysis_notes: str = Field(..., description="Forensic notes detailing the methodology and interpretation constraints")


# --- Engine A: DCT / Block-Artifact Analysis ---
class DCTMetrics(BaseModel):
    block_size: int = Field(default=8, description="Spatial block size in pixels (JPEG standard is 8x8)")
    analyzed_width: int = Field(..., ge=0, description="Width of analyzed block grid")
    analyzed_height: int = Field(..., ge=0, description="Height of analyzed block grid")
    total_blocks: int = Field(..., ge=0, description="Total number of 8x8 blocks evaluated")
    boundary_discontinuity: float = Field(..., ge=0.0, description="Mean absolute step discontinuity across 8x8 block boundaries")
    internal_discontinuity: float = Field(..., ge=0.0, description="Mean absolute step discontinuity across internal non-boundary pixels")
    blocking_artifact_ratio: float = Field(..., ge=0.0, description="Ratio of boundary to internal discontinuity (values > 1.0 indicate block grid alignment)")
    mean_block_energy: float = Field(..., ge=0.0, description="Mean AC frequency energy per 8x8 DCT block")


class DCTForensicResult(BaseModel):
    status: str = Field(default="SUCCESS", description="Status of DCT analysis (SUCCESS, UNAVAILABLE, or ERROR)")
    metrics: Optional[DCTMetrics] = Field(default=None, description="Quantitative block boundary and frequency metrics")
    visualization_data_url: Optional[str] = Field(default=None, description="Data URL with Base64-encoded PNG block-artifact map")
    analysis_notes: str = Field(..., description="Technical notes and contextual forensic interpretation")


# --- Engine B: High-Pass Noise Residual Analysis ---
class NoiseResidualMetrics(BaseModel):
    filter_type: str = Field(default="3x3 Laplacian High-Pass Operator", description="High-pass filter operator used to extract noise residuals")
    mean_absolute_residual: float = Field(..., ge=0.0, description="Mean absolute magnitude of high-frequency noise residual")
    std_residual: float = Field(..., ge=0.0, description="Standard deviation of the noise residual distribution")
    max_residual: float = Field(..., ge=0.0, description="Maximum absolute noise residual value observed")
    noise_energy: float = Field(..., ge=0.0, description="Average squared energy (variance) of the high-frequency residual")
    snr_estimate_db: Optional[float] = Field(
        default=None,
        description="Spatial high-pass SNR proxy in decibels: 10*log10(Var(signal)/Var(residual)). Not a calibrated physical sensor PRNU model."
    )


class NoiseResidualResult(BaseModel):
    status: str = Field(default="SUCCESS", description="Status of noise residual analysis (SUCCESS, UNAVAILABLE, or ERROR)")
    metrics: Optional[NoiseResidualMetrics] = Field(default=None, description="Quantitative noise residual statistical metrics")
    visualization_data_url: Optional[str] = Field(default=None, description="Data URL with Base64-encoded PNG residual map")
    analysis_notes: str = Field(..., description="Technical notes and contextual forensic interpretation")


# --- C2PA Provenance ---
class C2PAManifestClaim(BaseModel):
    title: Optional[str] = None
    claim_generator: Optional[str] = None
    format: Optional[str] = None
    instance_id: Optional[str] = None
    thumbnail_present: bool = False
    ingredients_count: int = 0
    assertions: List[Dict[str, Any]] = Field(default_factory=list)


class C2PAValidationResult(BaseModel):
    status: C2PAStatus = Field(..., description="High-level provenance status from c2pa-python SDK")
    sdk_available: bool = Field(..., description="Whether the official c2pa-python SDK is installed and operational")
    manifest_present: bool = Field(..., description="Whether a C2PA/JUMBF manifest was found in the media")
    validation_status: Optional[str] = Field(default=None, description="SDK internal validation state")
    manifest_data: Optional[Dict[str, Any]] = Field(default=None, description="Parsed manifest JSON if available")
    claims: Optional[C2PAManifestClaim] = Field(default=None, description="Structured claims summary extracted from manifest")
    signature_valid: Optional[bool] = Field(default=None, description="Whether cryptographic signature over the manifest is valid")
    signer_trusted: Optional[bool] = Field(default=None, description="Whether signer certificate chains to a trusted trust-list root")
    trust_validation_status: Optional[str] = Field(default=None, description="Trust-list or certificate-chain validation explanation")
    provenance_notes: str = Field(..., description="Guidance on interpreting C2PA presence/absence")


# --- Mission 09: EXIF, Metadata & Container Forensics ---
class MetadataStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    MALFORMED = "MALFORMED"
    UNSUPPORTED = "UNSUPPORTED"
    PARTIAL = "PARTIAL"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"


class ThumbnailStatus(str, Enum):
    NO_THUMBNAIL = "NO_THUMBNAIL"
    COMPARABLE = "COMPARABLE"
    MISMATCH_OBSERVED = "MISMATCH_OBSERVED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"

    # Mission 16 aliases
    THUMBNAIL_FOUND = "COMPARABLE"
    THUMBNAIL_ABSENT = "NO_THUMBNAIL"
    THUMBNAIL_INVALID = "UNAVAILABLE"
    THUMBNAIL_UNSUPPORTED = "UNAVAILABLE"
    ANALYSIS_FAILED = "ERROR"

class ConsistencySeverity(str, Enum):
    INFO = "INFO"
    INCONSISTENCY = "INCONSISTENCY"
    WARNING = "WARNING"


class ConsistencyObservation(BaseModel):
    check_name: str = Field(..., description="Identifier of the consistency check")
    severity: ConsistencySeverity = Field(..., description="Severity of the observation")
    observed_state: str = Field(..., description="Concise summary of the observed state or discrepancy")
    benign_explanation: str = Field(..., description="Legitimate non-malicious reasons for this discrepancy")


class DeviceMetadataStatus(str, Enum):
    PRESENT = "PRESENT"
    MANUFACTURER_ONLY = "MANUFACTURER_ONLY"
    SOFTWARE_ONLY = "SOFTWARE_ONLY"
    ABSENT = "ABSENT"
    MALFORMED = "MALFORMED"


class CameraMetadata(BaseModel):
    make: Optional[str] = Field(default=None, description="Camera manufacturer / make")
    model: Optional[str] = Field(default=None, description="Camera model name or number")
    device_status: DeviceMetadataStatus = Field(default=DeviceMetadataStatus.ABSENT, description="Device identification status")
    device_display_text: str = Field(default="Device information not present in file", description="Truthful human-readable device display text")
    provenance_note: str = Field(default="Metadata can be edited or stripped; presence of camera tags does not establish legal authenticity.", description="Truthful device provenance disclaimer")
    lens_model: Optional[str] = Field(default=None, description="Lens model information if present")
    software: Optional[str] = Field(default=None, description="Software / firmware string in EXIF or PNG text chunk")
    orientation_tag: Optional[int] = Field(default=None, description="EXIF orientation tag integer (1-8)")
    orientation_description: Optional[str] = Field(default=None, description="Human-readable interpretation of orientation")
    date_time_original: Optional[str] = Field(default=None, description="Original capture timestamp string (preserves timezone ambiguity)")
    date_time_digitized: Optional[str] = Field(default=None, description="Digitization timestamp string if recorded")
    date_time_modified: Optional[str] = Field(default=None, description="Image modification timestamp string")
    offset_time: Optional[str] = Field(default=None, description="EXIF OffsetTime / UTC timezone offset if explicitly recorded")
    metadata_dimensions: Optional[Dict[str, int]] = Field(default=None, description="Dimensions recorded in EXIF (ExifImageWidth, ExifImageHeight)")


class GPSMetadataSummary(BaseModel):
    gps_present: bool = Field(default=False, description="Whether GPS metadata tags were detected in the container")
    gps_status: str = Field(default="ABSENT", description="GPS status: ABSENT, DETECTED_AND_REDACTED, DETECTED_AND_EXTRACTED")
    tag_count: int = Field(default=0, description="Number of GPS tags present")
    coordinates_redacted: bool = Field(default=True, description="Indicates precise latitude/longitude are redacted for privacy")
    latitude: Optional[float] = Field(default=None, description="Precise latitude (only populated if explicitly opted-in)")
    longitude: Optional[float] = Field(default=None, description="Precise longitude (only populated if explicitly opted-in)")
    privacy_notice: str = Field(
        default="GPS coordinates are redacted by default to protect individual privacy. Detection indicates only that geolocation tags exist.",
        description="Privacy statement regarding GPS metadata"
    )


class ThumbnailAnalysisResult(BaseModel):
    status: ThumbnailStatus = Field(..., description="Thumbnail status: NO_THUMBNAIL, COMPARABLE, MISMATCH_OBSERVED, UNAVAILABLE, ERROR")
    has_thumbnail: bool = Field(default=False, description="Whether an embedded thumbnail was successfully extracted")
    thumbnail_format: Optional[str] = Field(default=None, description="Format of the extracted thumbnail (e.g. JPEG)")
    thumbnail_dimensions: Optional[Dict[str, int]] = Field(default=None, description="Thumbnail width and height in pixels")
    primary_dimensions: Optional[Dict[str, int]] = Field(default=None, description="Primary image width and height in pixels")
    thumbnail_aspect_ratio: Optional[float] = Field(default=None, description="Aspect ratio of thumbnail (w/h)")
    primary_aspect_ratio: Optional[float] = Field(default=None, description="Aspect ratio of primary image (w/h)")
    similarity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Normalized similarity metric (1.0 = identical content, 0.0 = completely dissimilar)")
    mean_absolute_difference: Optional[float] = Field(default=None, ge=0.0, description="Mean absolute pixel difference between aligned thumbnail and resized primary image")
    thumbnail_data_url: Optional[str] = Field(default=None, description="Data URL (base64 image/jpeg) of genuine extracted thumbnail preview")
    comparison_notes: str = Field(..., description="Forensic context explaining thumbnail alignment, aspect ratio, and benign divergence causes")


class ContainerConsistencyResult(BaseModel):
    status: str = Field(default="CONSISTENT", description="Overall consistency summary (CONSISTENT, DISCREPANCIES_OBSERVED, or NOT_EVALUATED)")
    observations: List[ConsistencyObservation] = Field(default_factory=list, description="Specific container and metadata consistency observations")
    notes: str = Field(..., description="Contextual guidance emphasizing that discrepancies alone do not prove tampering")


class MetadataInventory(BaseModel):
    status: MetadataStatus = Field(..., description="Overall metadata presence/parsing status")
    detected_structures: List[str] = Field(default_factory=list, description="Detected structures (e.g. EXIF, XMP, PNG_TEXT)")
    exif_tag_count: int = Field(default=0, description="Total number of valid EXIF tags extracted")
    xmp_packet_present: bool = Field(default=False, description="Whether an XMP metadata packet was found")
    png_text_chunks_count: int = Field(default=0, description="Number of text chunks found in PNG container")


class MetadataForensicResult(BaseModel):
    inventory: MetadataInventory = Field(..., description="Inventory of detected metadata structures and tag counts")
    camera_metadata: Optional[CameraMetadata] = Field(default=None, description="Camera, lens, software, and timestamp metadata")
    gps_summary: GPSMetadataSummary = Field(..., description="Privacy-aware GPS metadata assessment")
    thumbnail_analysis: ThumbnailAnalysisResult = Field(..., description="Embedded thumbnail extraction and comparison result")
    container_consistency: ContainerConsistencyResult = Field(..., description="Container and cross-field consistency evaluation")
    analysis_notes: str = Field(..., description="Forensic interpretation guidelines and evidentiary limitations")




# --- Mission 10: Evidence Fusion & Explainability ---
class ForensicCategory(str, Enum):
    ELA = "ELA"
    DCT = "DCT"
    NOISE_RESIDUAL = "NOISE_RESIDUAL"
    C2PA = "C2PA"
    METADATA = "METADATA"
    THUMBNAIL = "THUMBNAIL"
    CONSISTENCY = "CONSISTENCY"
    AI_DETECTOR = "AI_DETECTOR"


class FindingStatus(str, Enum):
    EVIDENCE_OBSERVED = "EVIDENCE_OBSERVED"
    NO_ANOMALY_OBSERVED = "NO_ANOMALY_OBSERVED"
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    INVALID = "INVALID"
    UNTRUSTED = "UNTRUSTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    ANALYSIS_UNAVAILABLE = "ANALYSIS_UNAVAILABLE"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    UNSUPPORTED = "UNSUPPORTED"
    PARTIAL = "PARTIAL"


class EvidenceFinding(BaseModel):
    finding_id: str = Field(..., description="Stable, deterministic finding identifier (e.g. FIND-ELA-01)")
    category: ForensicCategory = Field(..., description="Forensic category of the finding")
    source_component: str = Field(..., description="Exact engine or check that produced the finding")
    status: FindingStatus = Field(..., description="Categorical finding state: EVIDENCE_OBSERVED, NO_ANOMALY_OBSERVED, INCONCLUSIVE, or ANALYSIS_UNAVAILABLE")
    summary: str = Field(..., description="Concise human-readable explanation of the finding")
    observed_values: Dict[str, Any] = Field(default_factory=dict, description="Structured quantitative measurements without raw binaries or coordinates")
    interpretation: str = Field(..., description="Objective explanation of what the observation may indicate")
    limitations: str = Field(..., description="Explicit statement of what this finding does NOT establish")
    benign_explanations: List[str] = Field(default_factory=list, description="Plausible non-malicious causes for this observation")
    related_findings: List[str] = Field(default_factory=list, description="Identifiers of genuinely related findings, if any")


class UnifiedForensicReport(BaseModel):
    report_schema_version: str = Field(default="1.0.0", description="Version of the unified evidence fusion schema")
    analysis_completion_status: str = Field(..., description="Overall completion state: COMPLETE, PARTIAL_SUCCESS, or FAILED")
    evaluated_at_utc: datetime = Field(..., description="UTC timestamp of evidence consolidation")
    total_findings_count: int = Field(..., ge=0, description="Total number of discrete evidence findings evaluated")
    findings: List[EvidenceFinding] = Field(default_factory=list, description="All evaluated evidence findings across all categories")
    findings_by_category: Dict[str, List[EvidenceFinding]] = Field(default_factory=dict, description="Findings indexed by forensic category")
    component_availability: Dict[str, str] = Field(default_factory=dict, description="Operational status per forensic component")
    cautious_summary: str = Field(..., description="Objective, non-probabilistic synthesis of observed evidence")
    global_limitations: List[str] = Field(default_factory=list, description="Platform-level forensic limitations and evidentiary boundaries")

# --- Unified Evidence Response Schema ---

# --- AI-Generated Image Detection Schemas (Mission 11) ---

class AIDetectionStatus(str, Enum):
    LOADED = 'LOADED'
    UNAVAILABLE = 'UNAVAILABLE'
    INFERENCE_FAILED = 'INFERENCE_FAILED'
    WEIGHTS_MISSING = 'WEIGHTS_MISSING'


class AIDetectionDecision(str, Enum):
    AI_GENERATED_CLASS = 'AI_GENERATED_CLASS'
    REAL_IMAGE_CLASS = 'REAL_IMAGE_CLASS'
    INCONCLUSIVE = 'INCONCLUSIVE'
    UNAVAILABLE = 'UNAVAILABLE'


class AIDetectorResult(BaseModel):
    available: bool = Field(..., description='Whether inference was performed successfully')
    model_name: str = Field(default='UniversalFakeDetect CVPR 2023', description='Identity of the selected detector')
    model_version: str = Field(default='1.0.0-cvpr2023', description='Model architecture or revision identifier')
    model_status: AIDetectionStatus = Field(..., description='Operational status of the detector')
    raw_score: Optional[float] = Field(default=None, description='Uncalibrated model output logit z')
    uncalibrated_margin: Optional[float] = Field(default=None, description='Sigmoid margin in [0, 1]; not a calibrated probability')
    score_semantics: str = Field(..., description='Documented mathematical meaning of the raw score')
    predicted_class: Optional[str] = Field(default=None, description='Model output class: artificial vs human')
    decision_status: AIDetectionDecision = Field(..., description='Cautious decision classification based on model output')
    preprocessing: str = Field(..., description='Applied image preprocessing steps: bicubic resize to 224x224, center crop 224x224, CLIP normalization')
    device_used: str = Field(default='cpu', description='Execution device: cuda or cpu')
    limitations: List[str] = Field(default_factory=list, description='Model-specific constraints and degradation factors')
    error_code: Optional[str] = Field(default=None, description='Safe structured error code if inference could not complete')
    error_message: Optional[str] = Field(default=None, description='Sanitized human-readable error description')
    inference_ready: bool = Field(default=True, description="Whether inference model executed successfully")
    probabilities: Optional[Dict[str, float]] = Field(default=None, description="Class probabilities if calibrated or normalized")
    inference_latency_ms: Optional[float] = Field(default=None, description="Elapsed forward pass latency in milliseconds")
    scientific_disclaimer: str = Field(
        default='This is a model-based assessment, not proof of image origin. Performance may vary across generators, image processing, and domains.',
        description='Mandatory model assessment limitation notice'
    )


class ModelLifecycleState(str, Enum):
    READY = "READY"
    LOADING = "LOADING"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"
    INCOMPATIBLE = "INCOMPATIBLE"


class ModelProbeMetadata(BaseModel):
    head_id: str = Field(..., description="Unique identifier of the probe head")
    model_name: str = Field(..., description="Human-readable model name")
    version: str = Field(..., description="Model head version")
    filename: str = Field(..., description="Weights file path or name")
    expected_sha256: Optional[str] = Field(default=None, description="Expected SHA-256 checksum if verified")
    actual_sha256: Optional[str] = Field(default=None, description="Computed SHA-256 checksum of weights")
    weights_loaded: bool = Field(..., description="Whether weights buffer is loaded in memory")
    weights_shape: Optional[List[int]] = Field(default=None, description="Shape of linear weight matrix")
    head_state: ModelLifecycleState = Field(..., description="Lifecycle state of the classification head")
    operational_state: ModelLifecycleState = Field(..., description="End-to-end operational state factoring in backbone")
    description: str = Field(..., description="Probe head architecture and training summary")


class BackboneMetadata(BaseModel):
    backbone_id: str = Field(..., description="Backbone identifier")
    name: str = Field(..., description="Human-readable backbone name")
    architecture: str = Field(..., description="Backbone model architecture")
    expected_dim: int = Field(default=768, description="Expected feature embedding dimension")
    loaded: bool = Field(..., description="Whether backbone weights are currently loaded into memory")
    device: str = Field(default="cpu", description="Target execution device")
    state: ModelLifecycleState = Field(..., description="Backbone lifecycle state")
    reason: str = Field(..., description="Detailed status reason or unavailable cause")


class ModelRegistryStatusResponse(BaseModel):
    status: str = Field(default="ok", description="Overall registry status")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    active_head_id: str = Field(..., description="Currently active classification head ID")
    inference_ready: bool = Field(..., description="Whether end-to-end inference from raw image is ready")
    device_available: str = Field(..., description="Host hardware execution device")
    cuda_driver_available: bool = Field(..., description="Whether host NVIDIA GPU driver/CUDA is present")
    vram_total_mb: Optional[float] = Field(default=None, description="Total GPU VRAM in megabytes if detected")
    backbone: BackboneMetadata = Field(..., description="Shared feature extractor backbone status")
    registered_heads: List[ModelProbeMetadata] = Field(..., description="List of registered linear classification probes")


class SynthIDStateEnum(str, Enum):
    WATERMARK_DETECTED = "WATERMARK_DETECTED"
    WATERMARK_NOT_DETECTED = "WATERMARK_NOT_DETECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SCREENSHOT_FALLBACK_ACTIVE = "SCREENSHOT_FALLBACK_ACTIVE"


class SynthIDProvenanceResult(BaseModel):
    state: SynthIDStateEnum = Field(..., description="SynthID provenance verification state")
    watermark_present: bool = Field(default=False, description="Whether an imperceptible digital watermark signature was detected")
    confidence: float = Field(default=0.0, description="Verification confidence [0.0, 1.0]")
    algorithm: str = Field(default="SynthID Spatial and Frequency Domain Analysis", description="Detection algorithm identifier")
    screenshot_resilience_active: bool = Field(default=True, description="Whether intrinsic forensics active due to stripped metadata or screenshot")
    is_probable_screenshot: bool = Field(default=False, description="Heuristic detection of screen capture or screenshot")
    geotag_status: str = Field(default="NOT_PRESENT", description="Status of GPS or geotag metadata in asset container")
    explanation: str = Field(..., description="Forensic explanation of watermark and screenshot handling")
    audit_notes: List[str] = Field(default_factory=list, description="Forensic provenance audit notes")


class CanonicalBinaryVerdict(BaseModel):
    predicted_label: str = Field(..., description="Canonical binary decision label: 'AI_GENERATED' or 'NOT_AI_GENERATED'")
    display_label: str = Field(..., description="Consumer headline display label: 'AI GENERATED' or 'NOT AI GENERATED'")
    model_score: float = Field(..., description="Numeric model output score [0.0 - 1.0] with documented semantics")
    calibrated_probability: Optional[float] = Field(default=None, description="Empirically validated calibrated probability; null if calibration is not demonstrated")
    decision_threshold: float = Field(default=0.50, description="Calibrated or operational decision threshold applied")
    inference_time_ms: float = Field(default=0.0, description="Total inference execution time in milliseconds")
    model_version: str = Field(..., description="Active detector model version")
    evidence_summary: str = Field(..., description="Concise explanation of strongest evidence")
    warnings: List[str] = Field(default_factory=list, description="Genuine input or processing limitations")
    methodology_note: str = Field(
        default="Result determined via deep vision transformer representation and multi-layer forensic analysis. AI detectors may make mistakes.",
        description="Consumer limitation and methodology note"
    )


class Milestone1Response(BaseModel):
    request_id: str = Field(..., description="Unique UUID for this analysis request")
    timestamp_utc: datetime = Field(..., description="ISO 8601 UTC timestamp of the analysis")
    image_validation: ImageValidationResult = Field(..., description="Image geometry and file verification result")
    ela_forensics: Optional[ELAForensicResult] = Field(default=None, description="Error Level Analysis result")
    dct_analysis: Optional[DCTForensicResult] = Field(default=None, description="DCT block-artifact analysis result")
    noise_residual: Optional[NoiseResidualResult] = Field(default=None, description="High-pass noise residual analysis result")
    c2pa_provenance: C2PAValidationResult = Field(..., description="C2PA metadata and validation result")
    metadata_forensics: Optional[MetadataForensicResult] = Field(default=None, description="EXIF, container consistency, and thumbnail forensics result")
    unified_report: Optional[UnifiedForensicReport] = Field(default=None, description="Unified, explainable evidence-fusion report consolidating all forensic signals")
    ai_detection: Optional[AIDetectorResult] = Field(default=None, description='Dedicated AI-generated image detection result')
    synthid_provenance: Optional[SynthIDProvenanceResult] = Field(default=None, description="SynthID imperceptible watermark and screenshot resilience forensics")
    canonical_verdict: Optional[CanonicalBinaryVerdict] = Field(default=None, description="Mission 22 Consumer-First Canonical Binary Decision")
    component_errors: List[ComponentError] = Field(default_factory=list, description="Non-fatal component-level errors if any")
    disclaimer: str = Field(
        default=(
            "DISCLAIMER: Error Level Analysis (ELA), DCT block-artifact analysis, high-pass noise residuals, "
            "metadata/container inspection, and C2PA provenance are investigative technical signals. "
            "ELA detects compression variance; DCT analysis quantifies 8x8 block-boundary discontinuities; "
            "noise residuals estimate high-frequency spatial residual proxies; metadata and thumbnail analysis "
            "inspect container consistency and camera tags. None of these signals constitute definitive proof "
            "of synthetic AI generation or localized editing. Missing or stripped metadata is ubiquitous on "
            "social media platforms and web services. The system does not compute an aggregate authenticity "
            "probability or binary real/fake verdict."
        ),
        description="Mandatory forensic limitation disclaimer"
    )

class VideoMetadata(BaseModel):
    filename: str = Field(..., description="Original video filename")
    width: int = Field(..., description="Frame pixel width")
    height: int = Field(..., description="Frame pixel height")
    fps: float = Field(..., description="Nominal frame rate in frames per second")
    duration_sec: float = Field(..., description="Total video duration in seconds")
    total_frames: int = Field(..., description="Estimated total frame count in stream")
    aspect_ratio: float = Field(..., description="Aspect ratio width / height")
    codec_fourcc: str = Field(..., description="Video stream codec fourcc code")


class RGBFrameSample(BaseModel):
    sample_index: int = Field(..., description="Sequential index of the sample")
    frame_index: int = Field(..., description="Underlying decoded stream frame index")
    timestamp_sec: float = Field(..., description="Stream timestamp in seconds")
    r_mean: float = Field(..., description="Normalized mean Red channel intensity [0, 1]")
    g_mean: float = Field(..., description="Normalized mean Green channel intensity [0, 1]")
    b_mean: float = Field(..., description="Normalized mean Blue channel intensity [0, 1]")
    r_std: float = Field(..., description="Normalized Red channel standard deviation")
    g_std: float = Field(..., description="Normalized Green channel standard deviation")
    b_std: float = Field(..., description="Normalized Blue channel standard deviation")
    delta_prev_frame: float = Field(..., description="L1 norm difference from preceding sample")
    thumbnail_data_url: Optional[str] = Field(default=None, description="Low-res thumbnail JPEG data URL")
    ai_probability: Optional[float] = Field(default=None, description="Per-frame neural AI probability [0, 1]")
    ai_class: Optional[str] = Field(default=None, description="'AI_GENERATED' or 'LIKELY_REAL'")
    sensor_noise_variance: Optional[float] = Field(default=None, description="High-frequency Laplacian sensor noise proxy")


class RGBSummary(BaseModel):
    mean_red: float = Field(..., description="Global average Red intensity")
    mean_green: float = Field(..., description="Global average Green intensity")
    mean_blue: float = Field(..., description="Global average Blue intensity")
    rg_correlation: float = Field(..., description="Pearson correlation between Red and Green channels")
    gb_correlation: float = Field(..., description="Pearson correlation between Green and Blue channels")
    temporal_jitter_index: float = Field(..., description="Normalized frame-to-frame variance metric")
    dominant_pulse_hz: Optional[float] = Field(default=None, description="Estimated temporal frequency harmonic in Hz if observable")


class VideoAIVerdict(BaseModel):
    decision: str = Field(..., description="'AI_GENERATED_VIDEO', 'AUTHENTIC_CAMERA_VIDEO', or 'SUSPICIOUS_OR_HYBRID'")
    confidence_pct: float = Field(..., description="Calibrated confidence percentage (0 to 100)")
    mean_ai_probability: float = Field(..., description="Mean probability of AI generation across sampled frames")
    peak_ai_probability: float = Field(..., description="Peak AI probability in any single frame")
    ai_frame_ratio: float = Field(..., description="Proportion of sampled frames classified as AI generated")
    ai_frames_detected: int = Field(..., description="Count of frames with AI probability > 0.5")
    total_frames_analyzed: int = Field(..., description="Number of frames evaluated by the neural classifier")
    model_name: str = Field(..., description="Model architecture used for video inference")
    verdict_summary: str = Field(..., description="Human-readable forensic synthesis of the video verdict")
    evidence_breakdown: List[str] = Field(default_factory=list, description="Bullet points detailing specific evidentiary observations")



# --- MISSION 18: MULTI-LAYER VIDEO FORENSICS SCHEMAS ---

class VideoAnalyzerStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ANALYSIS_UNAVAILABLE = "ANALYSIS_UNAVAILABLE"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class VideoTaskClassification(str, Enum):
    REAL_CAPTURE = "REAL_CAPTURE"
    AI_GENERATED_VIDEO = "AI_GENERATED_VIDEO"
    FACE_MANIPULATED_VIDEO = "FACE_MANIPULATED_VIDEO"
    OTHER_MANIPULATED_VIDEO = "OTHER_MANIPULATED_VIDEO"
    UNKNOWN_OR_OUT_OF_DISTRIBUTION = "UNKNOWN_OR_OUT_OF_DISTRIBUTION"
    INCONCLUSIVE = "INCONCLUSIVE"


class VideoSamplingPreset(str, Enum):
    FAST = "fast"          # 12-16 sampled frames
    STANDARD = "standard"  # 24-32 sampled frames
    DEEP = "deep"          # 60 sampled frames


class BranchForensicResult(BaseModel):
    analyzer_id: str = Field(..., description="Unique branch identifier e.g. branch_1_rgb, branch_3_temporal")
    status: VideoAnalyzerStatus = Field(..., description="Branch execution status")
    method: str = Field(..., description="Scientific algorithm or model architecture applied")
    frames_analyzed: int = Field(..., description="Total frame count processed by this branch")
    timestamps_analyzed: List[float] = Field(default_factory=list, description="Video timestamps sampled for this branch")
    raw_metrics: Dict[str, Any] = Field(default_factory=dict, description="Computed numeric metrics and statistical moments")
    score: Optional[float] = Field(default=None, description="Standardized score [0.0, 1.0] if meaningfully applicable")
    score_semantics: str = Field(..., description="Semantic meaning of score, e.g. 'P(AI)', 'Jitter Index', 'Curvature'")
    model_version: Optional[str] = Field(default=None, description="Version or name of visual backbone / classifier")
    checkpoint_hash: Optional[str] = Field(default=None, description="Cryptographic SHA256 of weights if applicable")
    runtime_ms: float = Field(..., description="Measured CPU/GPU runtime in milliseconds")
    warnings: List[str] = Field(default_factory=list, description="Operational or environmental warnings")
    limitations: List[str] = Field(default_factory=list, description="Known methodological boundaries and false-positive drivers")
    evidence_summary: str = Field(..., description="Human-readable summary of this branch's findings")


class SuspiciousTemporalInterval(BaseModel):
    start_timestamp: float = Field(..., description="Interval onset in seconds")
    end_timestamp: float = Field(..., description="Interval termination in seconds")
    frame_indices: List[int] = Field(default_factory=list, description="Sampled frame indices spanning the interval")
    branch: str = Field(..., description="Forensic branch originating this flag")
    measured_metric: str = Field(..., description="Observed anomaly e.g. Step Distance Spike d=0.42")
    threshold_or_basis: str = Field(..., description="Decision threshold or statistical baseline")
    explanation: str = Field(..., description="Forensic interpretation of the anomaly")
    confidence_semantics: str = Field(..., description="Confidence rating or anomaly severity")
    caveats: str = Field(..., description="Alternative natural explanations (e.g. rapid camera pan or cut)")


class VideoFusionResult(BaseModel):
    final_classification: VideoTaskClassification = Field(..., description="Authoritative 5-class or inconclusive verdict")
    calibrated_ai_probability: Optional[float] = Field(default=None, description="Calibrated probability [0.0, 1.0] of AI generation")
    raw_model_score: float = Field(..., description="Uncalibrated ensemble/classifier score")
    confidence_pct: float = Field(..., description="Calibrated confidence percentage (0 to 100)")
    uncertainty_interval: Tuple[float, float] = Field(..., description="95% confidence/credible interval (lower, upper)")
    score_semantics: str = Field(default="Uncalibrated Ensemble Likelihood", description="Explicit semantics of raw_model_score and probability")
    uncertainty_status: str = Field(default="UNSPECIFIED", description="EXPLICIT: HIGH_CONFIDENCE, MODERATE_CONFIDENCE, CONFLICTING_SIGNALS, BORDERLINE, INSUFFICIENT_DATA")
    supporting_evidence: List[str] = Field(default_factory=list, description="Points corroborating the classification")
    contradictory_evidence: List[str] = Field(default_factory=list, description="Points weighing against the classification")
    unavailable_analyzers: List[str] = Field(default_factory=list, description="Branches that were skipped or unavailable")
    known_limitations: List[str] = Field(default_factory=list, description="Scientific limitations of the determination")
    abstention_reason: Optional[str] = Field(default=None, description="Reason for returning INCONCLUSIVE if applicable")


class VideoForensicResult(BaseModel):
    request_id: str = Field(..., description="Unique analysis request UUID")
    timestamp_utc: datetime = Field(..., description="ISO 8601 UTC timestamp of video inspection")
    video_metadata: VideoMetadata = Field(..., description="Video stream and container properties")
    sampled_frames: List[RGBFrameSample] = Field(..., description="Chronological sequence of extracted frame samples")
    rgb_summary: RGBSummary = Field(..., description="Aggregated chromatic and temporal statistics")
    anomaly_timestamps: List[float] = Field(default_factory=list, description="Timestamps with statistically significant frame transitions")
    video_ai_verdict: Optional[VideoAIVerdict] = Field(default=None, description="Unified video AI generation verdict based on multi-frame temporal consensus")
    analysis_notes: str = Field(..., description="Methodological notes explaining the video analysis")
    scientific_disclaimer: str = Field(
        default=(
            "DISCLAIMER: RGB temporal channel analysis and frame-to-frame delta metrics reflect statistical "
            "color distributions across decoded video frames. They provide descriptive measurements of temporal "
            "dynamics and potential transition anomalies; they do NOT constitute medical heartbeat measurements, "
            "remote photoplethysmography (rPPG) biometrics, or definitive proof of deepfake/AI video generation."
        ),
        description="Mandatory video forensic limitation disclaimer"
    )
    branches: Optional[Dict[str, BranchForensicResult]] = Field(default=None, description="Independent multi-layer branch results")
    suspicious_intervals: Optional[List[SuspiciousTemporalInterval]] = Field(default=None, description="Flagged temporal intervals with timestamps and evidence")
    fusion_verdict: Optional[VideoFusionResult] = Field(default=None, description="Multi-layer calibrated fusion decision")
    runtime_breakdown_ms: Optional[Dict[str, float]] = Field(default=None, description="Measured execution time per branch and decoder")
    canonical_verdict: Optional[CanonicalBinaryVerdict] = Field(default=None, description="Mission 22 Consumer-First Canonical Binary Decision")
