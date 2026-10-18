# MISSION 18 — TARGET ARCHITECTURE SPECIFICATION
## PARALLEL MULTI-LAYER VIDEO FORENSICS & TEMPORAL INTELLIGENCE ENGINE

**Project:** Secura AI 2.0  
**Specification Level:** System Architecture, API Contract & Modular Engine  
**Status:** IMPLEMENTATION_READY  
**Timestamp:** 2026-10-18T12:03:00Z  

---

## 1. Architectural Overview

Secura AI 2.0 transitions from a heuristic frame-averaging approach to a multi-layer, modular video forensics engine. Each forensic branch executes independently and emits a strongly typed BranchForensicResult.

`
                  +-----------------------------------------+
                  |          Uploaded Video Stream          |
                  +--------------------+--------------------+
                                       |
                  +--------------------v--------------------+
                  |    Shared Ephemeral Frame Sampler       |
                  |   (Uniform, Scene-Cut, Budgeted)        |
                  +--------------------+--------------------+
                                       | Decoded In-Memory RGB Frames
         +--------------+--------------+--------------+--------------+--------------+
         |              |              |              |              |              |
   +-----v-----+  +-----v-----+  +-----v-----+  +-----v-----+  +-----v-----+  +-----v-----+
   | Branch 1  |  | Branch 2  |  | Branch 3  |  | Branch 4  |  | Branch 6  |  | Branch 7  |
   | RGB /     |  | Motion &  |  | Learned   |  | Spatial & |  | Facial    |  | Container |
   | Chromatic |  | Optical   |  | Temporal  |  | Frequency |  | Consist.  |  | & C2PA    |
   | Forensics |  | Flow      |  | ReStraV   |  | (Noise/AI)|  | (Opt.)    |  | Provenance|
   +-----+-----+  +-----+-----+  +-----+-----+  +-----+-----+  +-----+-----+  +-----+-----+
         |              |              |              |              |              |
         +--------------+--------------+--------------+--------------+--------------+
                                       |
                  +--------------------v--------------------+
                  |    Multi-Layer Evidence Fusion Engine   |
                  | (Calibrated Likelihood & Abstention)    |
                  +--------------------+--------------------+
                                       |
                  +--------------------v--------------------+
                  |      Unified VideoForensicResult        |
                  |    (API Response & UI Dashboard)        |
                  +-----------------------------------------+
`

---

## 2. Strong Typing & Schema Specification

Every branch implements BaseVideoBranch and outputs a BranchForensicResult:

- VideoAnalyzerStatus: COMPLETED, NOT_APPLICABLE, ANALYSIS_UNAVAILABLE, ANALYSIS_FAILED, INSUFFICIENT_DATA.
- VideoTaskClassification: REAL_CAPTURE, AI_GENERATED_VIDEO, FACE_MANIPULATED_VIDEO, OTHER_MANIPULATED_VIDEO, UNKNOWN_OR_OUT_OF_DISTRIBUTION, INCONCLUSIVE.
- BranchForensicResult: analyzer_id, status, method, frames_analyzed, timestamps_analyzed, raw_metrics, score, score_semantics, model_version, checkpoint_hash, runtime_ms, warnings, limitations, evidence_summary.
- SuspiciousTemporalInterval: start_timestamp, end_timestamp, frame_indices, branch, measured_metric, threshold_or_basis, explanation, confidence_semantics, caveats.

---

## 3. Forensic Branch Specifications

### Branch 1: RGB & Chromatic Temporal Forensics
- Implementation: backend/app/services/video_branches/rgb_chromatic.py
- Metrics: Frame channel means (R, G, B), standard deviations, L1 norm frame difference Delta(t), color histogram intersection distance, second-order temporal differences Delta^2(t).
- Scene-Cut Discrimination: Separates natural cuts from erratic synthetic pixel shifts.
- RGB-Heart: Powers live parametric cardioid telemetry in the UI.

### Branch 2: Motion & Optical-Flow Forensics
- Implementation: backend/app/services/video_branches/optical_flow.py
- Method: OpenCV Farneback dense optical flow on consecutive sampled frames.
- Metrics: Motion magnitude distribution, angular direction consistency, motion discontinuities, and camera-pan/cut filtering.

### Branch 3: Learned Temporal Representation (ReStraV Engine)
- Implementation: backend/app/services/video_branches/temporal_representation.py
- Foundational Visual Encoder: CLIP ViT-L/14 visual backbone (768-dim projection).
- Geometric Trajectory Metrics:
  - Stepwise cosine distances: d_t = 1 - cos(z_t, z_{t+1})
  - Temporal curvature K_t = arccos((z_t - z_{t-1}) . (z_{t+1} - z_t))
  - Trajectory tortuosity: tau = Length / DirectDistance
  - Acceleration variance: Var(||Delta^2 z_t||)
- Temporal Classifier: Logistic/ridge temporal classifier mapping geometric curvature to generation likelihood.

### Branch 4: Spatial & Frequency Forensics
- Implementation: backend/app/services/video_branches/spatial_frequency.py
- Metrics: Laplacian high-frequency noise variance Var(Laplacian(I)) to detect authentic CMOS sensor noise vs diffusion smoothing; multi-frame Swin Vision Transformer neural AI detection distribution (median, trimmed mean, peak, fraction over threshold).

### Branch 5: Dedicated Video Classifier & Multi-Layer Fusion
- Implementation: backend/app/services/video_fusion.py
- Method: Synthesizes temporal trajectory curvature, motion stability, spatial diffusion distribution, and noise variance.
- Output: Calibrated probabilities, confidence interval, supporting/contradictory evidence, and explicit INCONCLUSIVE abstention.

### Branch 6: Face & Object Consistency (Optional)
- Implementation: backend/app/services/video_branches/face_consistency.py
- Behavior: Evaluates facial bounding box tracking if human faces are present; otherwise returns NOT_APPLICABLE. Never forces a whole-video verdict to rely on face presence.

### Branch 7: Container, Metadata & Provenance
- Implementation: backend/app/services/video_branches/container_provenance.py
- Metrics: Codec FourCC parsing, container vs stream duration, VFR jitter, resolution consistency, and C2PA provenance assertion inspection.
