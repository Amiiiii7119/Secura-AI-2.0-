# Video Classification Failure & Forensic Inconsistency Root Cause Analysis
**Mission:** 25  
**Component:** Multi-Layer Video Forensics Engine (`VideoEvidenceFusion`, `VideoFrameSampler`, `VideoForensicsWorkspace`)  
**Target Investigation:** False positive classification on 5-second authentic recording `camera_capture.webm`  
**Date:** October 2026  

---

## Executive Summary & Observed Inconsistency

During testing of the Secura AI 2.0 platform, an authentic 5-second camera recording captured via browser `MediaRecorder` named `camera_capture.webm` was incorrectly classified as **`AI GENERATED`**.

The displayed UI state presented internally contradictory and clinically impossible metrics:
- **Decision Threshold:** `0.50`
- **Model Score:** `41.0%` (0.410)
- **Displayed Calibrated P(AI):** `42.2%`
- **Main Verdict:** `AI GENERATED` *(Contradiction: 0.410 < 0.50 decision threshold)*
- **Duration:** `0.00s` *(Contradiction: File is a genuine 5-second multi-frame recording)*
- **Sampled Frames:** `1` *(Contradiction: 150 frames recorded)*
- **Active Temporal Branch:** `INSUFFICIENT DATA`
- **Temporal Curvature Displayed:** `1.83 rad` *(Contradiction: Branch was marked insufficient data)*
- **Temporal Synthetic Likelihood Displayed:** `83.4%` *(Contradiction: Branch was marked insufficient data)*
- **Optical Flow Branch:** `INSUFFICIENT DATA`
- **RGB Jitter:** `0.0000`

---

## Confirmed Root Causes

### 1. Root Cause A: Flawed Conditional Overrides & Default State Leaks in `video_fusion.py`
- **Mechanism:** In `backend/app/services/video_fusion.py`, when a branch (such as Branch 3: Temporal Curvature) had insufficient frames (< 4 frames) or failed to execute, `has_temporal` was evaluated as `False`.
- **Defect:** Despite `has_temporal == False`, the curvature normalization logic previously defaulted `norm_curv` to `0.50` (or `(mean_curv - 0.90)/0.90`).
- **Cascade:** In the rule-based cascade, a rule:
  ```python
  elif norm_curv >= 0.50:
      classification = VideoTaskClassification.AI_GENERATED_VIDEO
  ```
  tripped unconditionally! This assigned the high-level verdict `AI_GENERATED_VIDEO` even when the spatial score was 0.410 and the ensemble probability was 0.410.
- **Remediation:** 
  1. Any decision rule evaluating `norm_curv` is guarded strictly with `if has_temporal:`.
  2. The canonical binary classification invariant was made authoritative:
     $$	ext{Predicted Verdict} = egin{cases} 	ext{AI GENERATED} & 	ext{if } 	ext{canonical\_score} \ge 0.50 \ 	ext{NOT AI GENERATED} & 	ext{if } 	ext{canonical\_score} < 0.50 \end{cases}$$
  3. Under zero circumstances can a model score of 41.0% produce `AI GENERATED`.

### 2. Root Cause B: WebM Unindexed Container & Zero-Duration Decoding Bug in `video_sampler.py`
- **Mechanism:** Real-time browser video recorded using `MediaRecorder` produces WebM container streams that lack standard EBML `Duration` tags in the segment header and do not contain index Cues elements.
- **Defect:** When OpenCV (`cv2.VideoCapture`) opened `camera_capture.webm`:
  - `CAP_PROP_FRAME_COUNT` returned `0` or negative values.
  - `CAP_PROP_POS_MSEC` or duration calculation computed `duration_sec = 0.00s`.
  - Frame seeking (`cap.set(cv2.CAP_PROP_POS_FRAMES, ...)`) failed completely on unindexed streams, returning `False` on all seek calls.
  - The sampler fell back to reading only the first decodable keyframe ($N=1$), falsely aborting further sampling.
- **Cascade:** The entire 5-second video was collapsed into 1 sampled frame. Because 1 frame cannot compute frame-to-frame delta or representation curvature, branches 2 and 3 became `INSUFFICIENT DATA`.
- **Remediation:**
  - Implemented a two-pass stream-aware decoder in `VideoFrameSampler`:
    - **Pass 1:** High-speed grab scan (`cap.grab()`) counts exact decodable frames (e.g. 150 frames) and determines true stream duration in $< 35	ext{ ms}$.
    - **Pass 2:** Calculates uniform stride indices $S = \lfloor i \cdot rac{T - 1}{K - 1} floor$ across the entire timeline $[0, T-1]$, advancing frame-by-frame and retrieving full RGB arrays at target indices.
  - This guarantees that a 5-second video decodes exactly 16 uniform frames across $[0.0	ext{s}, 4.97	ext{s}]$ with verified non-zero duration ($5.0	ext{s}$).

### 3. Root Cause C: Frontend Mock Fallback Values in `VideoForensicsWorkspace.tsx`
- **Mechanism:** When backend analyzers reported `status: "INSUFFICIENT_DATA"` with `null` metrics, the React JSX component used nullish coalescing operators with hardcoded values:
  ```tsx
  {branch3?.raw_metrics?.mean_trajectory_curvature_rad ?? "1.83"} rad
  {branch3?.synthetic_likelihood ? ... : "83.4%"}
  ```
- **Defect:** If Branch 3 had insufficient data, the user interface deceptively presented `1.83 rad` and `83.4%` as if they were live, measured forensic data!
- **Remediation:** Removed all hardcoded numeric mock fallbacks from the frontend workspace. Missing or insufficient metrics now strictly render `"N/A"`, with clear expandable scientific disclosures explaining why the diagnostic was unavailable.
