# SECURA AI 2.0 — MISSION 21: BASELINE & REPOSITORY AUDIT
**Forensic Intelligence Correction + Premium Cream, Orange & Mustard UI + Cinematic Motion Design**

---

## 1. Executive Baseline & Mission Objectives

Secura AI 2.0 is an advanced digital forensics platform supporting multi-layer image and video verification. While previous missions established core feature extractors, the platform suffers from:
1. **Contradictory and Unreconciled Scoring Metrics**: The UI displays conflicting signals (e.g. "Authentic Camera: 92.4%" alongside "ReStraV synthetic likelihood: 83.4%" and "Overall verdict: OTHER_MANIPULATED_VIDEO (57.1%)") without mathematical reconciliation or clear score semantics.
2. **Uncalibrated Heuristics Masked as Probabilities**: The temporal representation branch uses handcrafted logistic mappings on trajectory curvature and tortuosity, but labels them as formal probabilities $P(\text{Synthetic Video})$.
3. **Task & Class Conflation**: An image-level diffusion detector (Swin Transformer) run on extracted video frames is presented at the video level as if it measures whole-video authenticity.
4. **Visual Design Inconsistency**: The application is currently styled with an unpolished dark UI rather than the required warm editorial luxury aesthetic (cream, burnt terracotta, light mustard).

Mission 21 executes a complete transformation: repairing forensic score integrity, establishing transparent multi-layer decision logic, and overhauling the frontend into a premium, responsive, accessible design system.

---

## 2. Forensic Failure Reproduction & Signal Dissection

### The Observed Contradictory Telemetry
On user upload of an AI-generated video, the interface presented the following mutually incompatible outputs:
- **Overall Verdict**: `OTHER_MANIPULATED_VIDEO` (Confidence: `57.1%`)
- **Top Gauge**: `Authentic Camera: 92.4%` vs `AI Generated Diffusion: 7.6%`
- **Branch 3 (ReStraV)**: `Synthetic Likelihood: 83.4%` (Mean curvature: `1.83 rad`)
- **Branch 4 (Spatial)**: `Swin Mean AI Score: 7.6%`
- **Fusion Banner**: `Calibrated P(AI) = 54.1%`
- **Filmstrip**: All frame badges labeled `REAL` with `85% - 97%` values
- **Suspicious Intervals**: Six curvature anomaly flags derived from a single branch

### Root Cause Tracing
1. **Origin of `Authentic Camera: 92.4%` / `AI Generated: 7.6%`**:
   In `VideoForensicsWorkspace.tsx`, lines 373 & 376:
   ```typescript
   Authentic Camera: {((1 - videoResult.video_ai_verdict.mean_ai_probability) * 100).toFixed(1)}%
   AI Generated Diffusion: {(videoResult.video_ai_verdict.mean_ai_probability * 100).toFixed(1)}%
   ```
   `video_ai_verdict` was merely the legacy still-image detector averaged over frames. When Swin evaluated each frame independently, its mean AI probability was $0.076$ ($7.6\%$). The frontend displayed this single image detector's complement ($1 - 0.076 = 92.4\%$) as the master banner for the entire video!
2. **Origin of `ReStraV: 83.4%`**:
   In `temporal_representation.py`, a heuristic logistic function was evaluated on curvature $K_t = 1.83$ rad:
   ```python
   logit = 0.5 * curvature_signal + 0.3 * tortuosity_signal + 0.2 * step_signal
   restrav_ai_prob = float(1.0 / (1.0 + np.exp(-logit)))
   ```
   This yielded $0.834$ ($83.4\%$). Calling this an empirical probability without a trained calibration classifier violated scientific integrity.
3. **Origin of `OTHER_MANIPULATED_VIDEO (57.1%)` and `P(AI) = 54.1%`**:
   In `video_fusion.py`:
   The weighted ensemble combined $0.50 \times 0.834 + 0.40 \times 0.076 = 0.4474$.
   Temperature scaling ($T = 1.15$) yielded $\approx 0.541$ ($54.1\%$).
   Because $0.42 < 0.541 < 0.58$, the fusion module hit its default `else` fallback:
   `classification = VideoTaskClassification.OTHER_MANIPULATED_VIDEO` with confidence $57.1\%$.
   This was a classification blunder: an unresolved conflict between temporal curvature and spatial diffusion was falsely classified as "other manipulation" (such as face-swapping or splicing) instead of `INCONCLUSIVE`!
4. **Origin of Filmstrip `REAL` Badges**:
   Each thumbnail showed `REAL` because the Swin image detector on individual frames did not trigger on subtle temporal generation artifacts.

---

## 3. Current System Component Matrix

| Subsystem | Source Path | Underlying Technology | Current Status | Issues to Remediate |
|---|---|---|---|---|
| **API Schemas** | `backend/app/schemas/evidence.py` | Pydantic v2 | Functional | Add explicit fields: `raw_score`, `score_semantics`, `uncertainty_status`, separate frame vs video tasks. |
| **Video Sampler** | `backend/app/services/video_sampler.py` | OpenCV VideoCapture | Functional | Works in single-pass; maintain deterministic sampling. |
| **Branch 1 (RGB)** | `backend/.../rgb_chromatic.py` | NumPy Vectorized | Functional | Descriptive only; ensure not conflated with AI generation probability. |
| **Branch 2 (Motion)** | `backend/.../optical_flow.py` | OpenCV Farnebäck | Functional | Descriptive motion fields; clarify that cuts and pans are not deepfakes. |
| **Branch 3 (Temporal)** | `backend/.../temporal_representation.py` | CLIP ViT-L/14 | Functional | Stop claiming custom logistic is official ReStraV; expose curvature as descriptive manifold anomaly. |
| **Branch 4 (Spatial)** | `backend/.../spatial_frequency.py` | Swin Base + Laplacian | Functional | Rename CMOS "proof" to high-frequency noise variance; clarify frame vs video scope. |
| **Branch 6 (Face)** | `backend/.../face_consistency.py` | Haar / Tracking | Safe N/A | Return NOT_APPLICABLE honestly when no faces present. |
| **Branch 7 (Container)** | `backend/.../container_provenance.py` | FourCC / C2PA | Functional | C2PA absence must not imply AI generation. |
| **Evidence Fusion** | `backend/app/services/video_fusion.py` | Bayesian Ensemble | Defective | Replace broken `OTHER_MANIPULATED_VIDEO` fallback with explicit `INCONCLUSIVE` abstention. |
| **Frontend Workspace** | `frontend/src/.../VideoForensicsWorkspace.tsx` | React 18, TypeScript | Working | Remove contradictory duplicate gauges; implement unified evidence dashboard. |
| **Design System** | `frontend/src/index.css` | Vanilla CSS | Dark theme | Transform into warm editorial luxury: cream (`#FFFDF8`), burnt terracotta (`#D96B35`), light mustard (`#E8C86A`). |

---

## 4. Remediation Plan (Phases 1–10)

1. **Phase 1 (Complete)**: Baseline audit, failure reproduction, and telemetry tracing.
2. **Phase 2**: Reconcile all scores in backend schemas, `temporal_representation.py`, and `video_fusion.py`.
3. **Phase 3**: Remove unsupported claims (CMOS proof, custom ReStraV probability claims).
4. **Phase 4**: Implement honest fusion policy with `INCONCLUSIVE` abstention and add pytest regression tests.
5. **Phase 5**: Establish the cream, burnt-orange, and mustard design tokens in `index.css`.
6. **Phase 6**: Rebuild landing page, navigation header, image workstation, and video workstation.
7. **Phase 7**: Implement refined motion transitions, responsive layout across all breakpoints, and data-bound RGB-heart polish.
8. **Phase 8**: Measure and verify performance and memory footprints.
9. **Phase 9**: Execute full test suites (`pytest`, `npm run build`), browser verification, and screenshot captures.
10. **Phase 10**: Publish full technical documentation under `docs/`.
