
export type CanonicalBinaryLabel = "AI_GENERATED" | "NOT_AI_GENERATED";
export type CanonicalDisplayLabel = "AI GENERATED" | "NOT AI GENERATED";

export interface CanonicalBinaryVerdict {
  predicted_label: CanonicalBinaryLabel;
  display_label: CanonicalDisplayLabel;
  model_score: number;
  calibrated_probability?: number | null;
  decision_threshold: number;
  inference_time_ms: number;
  model_version: string;
  evidence_summary: string;
  warnings?: string[];
  methodology_note?: string;
}

export type ImageFormat = "JPEG" | "PNG";

export type C2PAStatus =
  | "C2PA_PRESENT_AND_VALID"
  | "C2PA_PRESENT_WITH_VALIDATION_ISSUES"
  | "C2PA_MISSING"
  | "C2PA_UNAVAILABLE"
  | "C2PA_INSPECTION_ERROR"
  | "NO_MANIFEST"
  | "MANIFEST_FOUND"
  | "SIGNATURE_VALID"
  | "SIGNATURE_INVALID"
  | "SIGNER_UNTRUSTED"
  | "TRUST_VALIDATION_UNAVAILABLE"
  | "ANALYSIS_UNAVAILABLE"
  | "ANALYSIS_FAILED";

export type MetadataStatus = "PRESENT" | "ABSENT" | "MALFORMED" | "UNSUPPORTED" | "PARTIAL" | "ANALYSIS_FAILED";

export type ThumbnailStatus =
  | "NO_THUMBNAIL"
  | "COMPARABLE"
  | "MISMATCH_OBSERVED"
  | "UNAVAILABLE"
  | "ERROR"
  | "THUMBNAIL_FOUND"
  | "THUMBNAIL_ABSENT"
  | "THUMBNAIL_INVALID"
  | "THUMBNAIL_UNSUPPORTED"
  | "ANALYSIS_FAILED";

export type ConsistencySeverity = "INFO" | "INCONSISTENCY" | "WARNING";

export interface ComponentError {
  component: string;
  error_code: string;
  message: string;
}

export interface ImageValidationResult {
  is_valid: boolean;
  detected_format: ImageFormat;
  width: number;
  height: number;
  pixel_count: number;
  color_mode: string;
  file_size_bytes: number;
  mime_type: string;
}

export interface ELAMetrics {
  recompression_quality: number;
  scale_factor: number;
  mean_absolute_difference: number;
  max_absolute_difference: number;
  std_absolute_difference: number;
}

export interface ELAForensicResult {
  status: string;
  metrics?: ELAMetrics;
  heatmap_data_url?: string;
  analysis_notes: string;
}

export interface DCTMetrics {
  block_size: number;
  analyzed_width: number;
  analyzed_height: number;
  total_blocks: number;
  boundary_discontinuity: number;
  internal_discontinuity: number;
  blocking_artifact_ratio: number;
  mean_block_energy: number;
}

export interface DCTForensicResult {
  status: string;
  metrics?: DCTMetrics;
  visualization_data_url?: string;
  analysis_notes: string;
}

export interface NoiseResidualMetrics {
  filter_type: string;
  mean_absolute_residual: number;
  std_residual: number;
  max_residual: number;
  noise_energy: number;
  snr_estimate_db?: number;
}

export interface NoiseResidualResult {
  status: string;
  metrics?: NoiseResidualMetrics;
  visualization_data_url?: string;
  analysis_notes: string;
}

export interface C2PAManifestClaim {
  title?: string;
  claim_generator?: string;
  format?: string;
  instance_id?: string;
  thumbnail_present: boolean;
  ingredients_count: number;
  assertions: Array<{ label: string; data: unknown }>;
}

export interface C2PAValidationResult {
  status: C2PAStatus;
  sdk_available: boolean;
  manifest_present: boolean;
  validation_status?: string;
  manifest_data?: Record<string, unknown>;
  claims?: C2PAManifestClaim;
  signature_valid?: boolean | null;
  signer_trusted?: boolean | null;
  trust_validation_status?: string | null;
  provenance_notes: string;
}

export interface ConsistencyObservation {
  check_name: string;
  severity: ConsistencySeverity;
  observed_state: string;
  benign_explanation: string;
}

export interface CameraMetadata {
  device_status?: 'PRESENT' | 'MANUFACTURER_ONLY' | 'SOFTWARE_ONLY' | 'ABSENT' | 'MALFORMED';
  device_display_text?: string;
  provenance_note?: string;
  make?: string;
  model?: string;
  lens_model?: string;
  software?: string;
  orientation_tag?: number;
  orientation_description?: string;
  date_time_original?: string;
  date_time_digitized?: string;
  date_time_modified?: string;
  offset_time?: string;
  metadata_dimensions?: { width: number; height: number };
}

export interface GPSMetadataSummary {
  gps_present: boolean;
  gps_status: string;
  tag_count: number;
  coordinates_redacted: boolean;
  latitude?: number;
  longitude?: number;
  privacy_notice: string;
}

export interface ThumbnailAnalysisResult {
  status: ThumbnailStatus;
  has_thumbnail: boolean;
  thumbnail_format?: string;
  thumbnail_dimensions?: { width: number; height: number };
  primary_dimensions?: { width: number; height: number };
  thumbnail_aspect_ratio?: number;
  primary_aspect_ratio?: number;
  similarity_score?: number;
  mean_absolute_difference?: number;
  thumbnail_data_url?: string | null;
  comparison_notes: string;
}

export interface ContainerConsistencyResult {
  status: string;
  observations: ConsistencyObservation[];
  notes: string;
}

export interface MetadataInventory {
  status: MetadataStatus;
  detected_structures: string[];
  exif_tag_count: number;
  xmp_packet_present: boolean;
  png_text_chunks_count: number;
}

export interface MetadataForensicResult {
  inventory: MetadataInventory;
  camera_metadata?: CameraMetadata;
  gps_summary: GPSMetadataSummary;
  thumbnail_analysis: ThumbnailAnalysisResult;
  container_consistency: ContainerConsistencyResult;
  analysis_notes: string;
}

export type ForensicCategory =
  | "ELA"
  | "DCT"
  | "NOISE_RESIDUAL"
  | "C2PA"
  | "METADATA"
  | "THUMBNAIL"
  | "CONSISTENCY"
  | "AI_DETECTOR";

export type FindingStatus =
  | "EVIDENCE_OBSERVED"
  | "NO_ANOMALY_OBSERVED"
  | "PRESENT"
  | "ABSENT"
  | "INVALID"
  | "UNTRUSTED"
  | "INCONCLUSIVE"
  | "ANALYSIS_UNAVAILABLE"
  | "ANALYSIS_FAILED"
  | "UNSUPPORTED"
  | "PARTIAL";

export interface EvidenceFinding {
  finding_id: string;
  category: ForensicCategory;
  source_component: string;
  status: FindingStatus;
  summary: string;
  observed_values: Record<string, unknown>;
  interpretation: string;
  limitations: string;
  benign_explanations: string[];
  related_findings: string[];
}

export interface UnifiedForensicReport {
  report_schema_version: string;
  analysis_completion_status: string;
  evaluated_at_utc: string;
  total_findings_count: number;
  findings: EvidenceFinding[];
  findings_by_category: Record<string, EvidenceFinding[]>;
  component_availability: Record<string, string>;
  cautious_summary: string;
  global_limitations: string[];
}

export type AIDetectionStatus = 'LOADED' | 'UNAVAILABLE' | 'INFERENCE_FAILED' | 'WEIGHTS_MISSING';
export type AIDetectionDecision = 'AI_GENERATED_CLASS' | 'REAL_IMAGE_CLASS' | 'INCONCLUSIVE' | 'UNAVAILABLE';

export interface AIDetectorResult {
  available: boolean;
  model_name: string;
  model_version: string;
  model_status: AIDetectionStatus;
  raw_score?: number | null;
  uncalibrated_margin?: number | null;
  score_semantics: string;
  predicted_class?: string | null;
  decision_status: AIDetectionDecision;
  preprocessing: string;
  device_used: string;
  limitations: string[];
  error_code?: string | null;
  error_message?: string | null;
  inference_ready?: boolean;
  probabilities?: Record<string, number> | null;
  inference_latency_ms?: number | null;
  scientific_disclaimer: string;
}

export type SynthIDState =
  | "WATERMARK_DETECTED"
  | "WATERMARK_NOT_DETECTED"
  | "INSUFFICIENT_EVIDENCE"
  | "SCREENSHOT_FALLBACK_ACTIVE";

export interface SynthIDProvenanceResult {
  state: SynthIDState;
  watermark_present: boolean;
  confidence: number;
  algorithm: string;
  screenshot_resilience_active: boolean;
  is_probable_screenshot: boolean;
  geotag_status: string;
  explanation: string;
  audit_notes: string[];
}

export interface Milestone1Response {
  request_id: string;
  timestamp_utc: string;
  image_validation: ImageValidationResult;
  ela_forensics?: ELAForensicResult;
  dct_analysis?: DCTForensicResult;
  noise_residual?: NoiseResidualResult;
  c2pa_provenance: C2PAValidationResult;
  metadata_forensics?: MetadataForensicResult;
  unified_report?: UnifiedForensicReport;
  ai_detection?: AIDetectorResult | null;
  synthid_provenance?: SynthIDProvenanceResult | null;
  canonical_verdict?: CanonicalBinaryVerdict;
  component_errors: ComponentError[];
  disclaimer: string;
}

export interface ApiErrorDetail {
  error_code: string;
  message: string;
}

export type ModelLifecycleState = 'READY' | 'LOADING' | 'UNAVAILABLE' | 'FAILED' | 'INCOMPATIBLE';

export interface ModelProbeMetadata {
  head_id: string;
  model_name: string;
  version: string;
  filename: string;
  expected_sha256?: string | null;
  actual_sha256?: string | null;
  weights_loaded: boolean;
  weights_shape?: number[] | null;
  head_state: ModelLifecycleState;
  operational_state: ModelLifecycleState;
  description: string;
}

export interface BackboneMetadata {
  backbone_id: string;
  name: string;
  architecture: string;
  expected_dim: number;
  loaded: boolean;
  device: string;
  state: ModelLifecycleState;
  reason: string;
}

export interface ModelRegistryStatusResponse {
  status: string;
  timestamp_utc: string;
  active_head_id: string;
  inference_ready: boolean;
  device_available: string;
  cuda_driver_available: boolean;
  vram_total_mb?: number | null;
  backbone: BackboneMetadata;
  registered_heads: ModelProbeMetadata[];
}

export interface UserSession {
  authenticated: boolean;
  username?: string | null;
  role?: string | null;
  expires_at?: string | null;
}

export interface LoginResponse {
  success: boolean;
  token: string;
  username: string;
  role: string;
  expires_at: string;
}

export interface VideoMetadata {
  filename: string;
  width: number;
  height: number;
  fps: number;
  duration_sec: number;
  total_frames: number;
  aspect_ratio: number;
  codec_fourcc: string;
}

export interface RGBFrameSample {
  sample_index: number;
  frame_index: number;
  timestamp_sec: number;
  r_mean: number;
  g_mean: number;
  b_mean: number;
  r_std: number;
  g_std: number;
  b_std: number;
  delta_prev_frame: number;
  thumbnail_data_url?: string | null;
  thumbnail_b64?: string | null;
  heart_rate_bpm?: number | null;
  ai_probability?: number | null;
  ai_class?: string | null;
  sensor_noise_variance?: number | null;
}

export interface RGBSummary {
  mean_red: number;
  mean_green: number;
  mean_blue: number;
  rg_correlation: number;
  gb_correlation: number;
  temporal_jitter_index: number;
  dominant_pulse_hz?: number | null;
  estimated_heart_rate_bpm?: number | null;
  spectral_entropy?: number | null;
}

export interface VideoAIVerdict {
  decision: "AI_GENERATED_VIDEO" | "AUTHENTIC_CAMERA_VIDEO" | "SUSPICIOUS_OR_HYBRID" | string;
  confidence_pct: number;
  mean_ai_probability: number;
  peak_ai_probability: number;
  ai_frame_ratio: number;
  ai_frames_detected: number;
  total_frames_analyzed: number;
  model_name: string;
  verdict_summary: string;
  evidence_breakdown: string[];
}

export interface VideoForensicResult {
  request_id: string;
  timestamp_utc: string;
  video_metadata: VideoMetadata;
  sampled_frames: RGBFrameSample[];
  rgb_summary: RGBSummary;
  anomaly_timestamps: number[];
  video_ai_verdict?: VideoAIVerdict | null;
  analysis_notes: string;
  scientific_disclaimer: string;
  branches?: Record<string, BranchForensicResult>;
  suspicious_intervals?: SuspiciousTemporalInterval[];
  fusion_verdict?: VideoFusionResult | null;
  runtime_breakdown_ms?: Record<string, number>;
  canonical_verdict?: CanonicalBinaryVerdict | null;
}


export type VideoAnalyzerStatus = 'COMPLETED' | 'NOT_APPLICABLE' | 'ANALYSIS_UNAVAILABLE' | 'ANALYSIS_FAILED' | 'INSUFFICIENT_DATA';
export type VideoTaskClassification = 'REAL_CAPTURE' | 'AI_GENERATED_VIDEO' | 'FACE_MANIPULATED_VIDEO' | 'OTHER_MANIPULATED_VIDEO' | 'INCONCLUSIVE';

export interface BranchForensicResult {
  analyzer_id: string;
  status: VideoAnalyzerStatus;
  method: string;
  frames_analyzed: number;
  timestamps_analyzed: number[];
  raw_metrics: Record<string, any>;
  score?: number | null;
  score_semantics: string;
  model_version?: string | null;
  checkpoint_hash?: string | null;
  runtime_ms: number;
  warnings: string[];
  limitations: string[];
  evidence_summary: string;
}

export interface SuspiciousTemporalInterval {
  start_sec?: number;
  end_sec?: number;
  start_timestamp?: number;
  end_timestamp?: number;
  frame_indices?: number[];
  branch: string;
  measured_metric?: string;
  value?: number;
  threshold?: number;
  threshold_or_basis?: string;
  explanation: string;
  confidence_semantics?: string;
  caveats?: string;
}

export interface VideoFusionResult {
  final_classification: VideoTaskClassification;
  calibrated_ai_probability?: number | null;
  raw_model_score: number;
  confidence_pct: number;
  uncertainty_interval?: [number, number] | null;
  score_semantics?: string;
  uncertainty_status?: string;
  supporting_evidence: string[];
  contradictory_evidence: string[];
  unavailable_analyzers: string[];
  known_limitations: string[];
  abstention_reason?: string | null;
}
