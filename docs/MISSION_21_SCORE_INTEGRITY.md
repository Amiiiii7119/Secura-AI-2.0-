# SECURA AI 2.0 — MISSION 21: SCORE INTEGRITY & PROBABILITY RECONCILIATION AUDIT

---

## 1. Executive Telemetry Reconciliation

During user testing with an AI-generated video, Secura AI 2.0 displayed an array of seemingly contradictory metrics across different panels:
- Top Gauge: `Authentic Camera: 92.4%` vs `AI Generated Diffusion: 7.6%`
- Overall Verdict: `OTHER_MANIPULATED_VIDEO` (Confidence: `57.1%`)
- Branch 3 (ReStraV): `Synthetic Likelihood: 83.4%` (Curvature: `1.83 rad`)
- Branch 4 (Spatial): `Swin Mean AI Score: 7.6%`
- Fusion Banner: `Calibrated P(AI) = 54.1%`
- Filmstrip Badges: `REAL 85% - 97%` on all frame tiles

This document traces the exact mathematical origin of every metric, identifies the architectural flaws that produced these contradictions, and specifies the exact remediation implemented in Mission 21.

---

## 2. Metric-by-Metric Provenance Matrix

| Displayed Metric | Value | Backend Source Field | Generating Component | Original Mathematical Definition | Why It Contradicted Other Metrics |
|---|---|---|---|---|---|
| **Authentic Camera** | `92.4%` | `video_ai_verdict.mean_ai_probability` | `spatial_frequency.py` (Branch 4) | $1.0 - \frac{1}{N}\sum_{t=1}^N P_{\text{Swin}}(\text{AI} \mid I_t)$ | **Task Conflation**: This was simply the complement of the frame-level Swin image detector. The UI displayed this single image detector's score as the master whole-video authenticity probability! |
| **AI Generated Diffusion** | `7.6%` | `video_ai_verdict.mean_ai_probability` | `spatial_frequency.py` (Branch 4) | $\frac{1}{N}\sum_{t=1}^N P_{\text{Swin}}(\text{AI} \mid I_t)$ | **Frame vs Video Conflation**: Swin evaluates spatial patches on individual frames. Subtle generative videos with photorealistic individual frames (Sora, Wan2.1, Kling) produce low spatial diffusion scores (~7.6%) despite strong temporal warping. |
| **ReStraV Synthetic Likelihood** | `83.4%` | `branches["branch_3_temporal"].score` | `temporal_representation.py` (Branch 3) | $\sigma(0.5 z_{K} + 0.3 z_{\tau} + 0.2 z_{d})$ where $K_t = 1.83$ rad | **Uncalibrated Heuristic as Probability**: Handcrafted logistic sigmoid on curvature $K_t$ and tortuosity $\tau$ was presented as a formal probability $P(\text{Synthetic Video})$. |
| **Overall Verdict** | `OTHER_MANIPULATED_VIDEO` | `fusion_verdict.final_classification` | `video_fusion.py` | Fallback `else` branch when $0.42 < P_{\text{calibrated}} < 0.58$ | **Erroneous Fallback**: When temporal curvature was high (83.4%) and spatial diffusion was low (7.6%), the fusion layer blended them to $P \approx 0.54$. Instead of returning `INCONCLUSIVE` due to conflicting evidence, it falsely classified the clip as `OTHER_MANIPULATED_VIDEO`! |
| **Displayed Confidence** | `57.1%` | `fusion_verdict.confidence_pct` | `video_fusion.py` | $55.0 + |P_{\text{calibrated}} - 0.5| \times 50.0$ | **Unsupported Confidence Formula**: Calculated by a heuristic distance from 0.5, creating a false impression of mathematical precision. |
| **Fusion Calibrated P(AI)** | `54.1%` | `fusion_verdict.calibrated_ai_probability` | `video_fusion.py` | $\sigma(\text{logit} / 1.15)$ | **Mislabeled Calibration**: Labeled as "Calibrated" when temperature $T=1.15$ was a fixed constant rather than fitted on a representative empirical calibration split. |
| **Filmstrip Badges** | `REAL` | `sampled_frames[i].ai_class` | `video_orchestrator.py` | $P_{\text{Swin}}(I_t) < 0.5$ | **Badge Mismatch**: Each frame showed `REAL` because the Swin image model didn't trigger on still frames, directly contradicting the ReStraV temporal curvature findings. |

---

## 3. Systematic Corrections Applied in Mission 21

### Correction 1: Elimination of Conflicting Master Gauges
In `VideoForensicsWorkspace.tsx`:
- Removed the misleading `Authentic Camera: 92.4%` vs `AI Generated: 7.6%` split gauge.
- Replaced with a unified **Forensic Decision Header** driven strictly by the synthesized multi-layer verdict.
- Clearly states:
  - **Primary Decision**: `INCONCLUSIVE (Conflicting Signals)` or `AI_GENERATED_VIDEO` or `REAL_CAPTURE`.
  - **Ensemble Likelihood Score**: Labeled explicitly as `Uncalibrated Ensemble Likelihood` (e.g. `0.54 / 1.0`).
  - **Uncertainty Status**: Displays `CONFLICTING_SIGNALS` with an explicit explanation of why branches disagree.

### Correction 2: Reclassification of Temporal Representation (Branch 3)
In `temporal_representation.py`:
- Ceased reporting the custom logistic sigmoid as $P(\text{Synthetic Video})$.
- Exposes raw geometric metrics:
  - `mean_trajectory_curvature_rad`: $1.83$ rad (Straightening violation threshold: $>1.50$ rad).
  - `trajectory_tortuosity`: $\tau$ ratio.
  - `step_distance_std`: Inter-frame velocity jitter.
- Method name corrected to: `CLIP ViT-L/14 Representation Trajectory (ReStraV-Inspired Geometry)`.
- Score semantics set to: `Trajectory Curvature Anomaly Metric (Uncalibrated)`.

### Correction 3: High-Frequency Texture & Noise Clarification (Branch 4)
In `spatial_frequency.py`:
- Removed claims that Laplacian variance is definitive proof of physical CMOS camera sensors.
- Labeled as `High-Frequency Residual Texture & Noise Variance`.
- Frame-level predictions are clearly annotated as `Per-Frame Diffusion Texture Detector (Swin-Base)`.

### Correction 4: Honest Fusion Policy with Explicit Abstention
In `video_fusion.py`:
- Fixed the decision policy to eliminate false `OTHER_MANIPULATED_VIDEO` verdicts:
  1. If temporal curvature is elevated ($K_t > 1.5$ rad) but spatial diffusion detector is low ($P_{\text{spatial}} < 0.20$), and no facial manipulation is detected:
     - The system classifies the clip as **`INCONCLUSIVE`** with `uncertainty_status = CONFLICTING_SIGNALS`.
     - Abstention reason: *"Temporal representation trajectory exhibits significant non-geodesic curvature (1.83 rad), but spatial frame diffusion detector reports low texture likelihood (7.6%). Result is inconclusive pending secondary camera-sensor or audio verification."*
  2. If spatial diffusion is elevated ($\ge 0.55$) AND temporal curvature is elevated ($K_t \ge 1.4$ rad):
     - The system confidently classifies as **`AI_GENERATED_VIDEO`**.
  3. If spatial diffusion is low ($\le 0.35$) AND temporal curvature is smooth ($K_t \le 1.1$ rad) AND high-frequency noise variance is natural:
     - The system classifies as **`REAL_CAPTURE`**.
  4. Only if facial tracking detects boundary warping or face-swap artifacts does the system return **`FACE_MANIPULATED_VIDEO`** or **`OTHER_MANIPULATED_VIDEO`**.

### Correction 5: Filmstrip Tile Disambiguation
In `VideoForensicsWorkspace.tsx`:
- Replaced the blanket `REAL` / `AI` badges on filmstrip thumbnails with:
  `Frame Diffusion Score: 7.6%` (or `P(AI): 0.08`).
- Clarified via inline tooltip that this reflects individual still-frame texture analysis, which may not capture temporal video-generation dynamics.
