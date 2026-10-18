# SECURA AI 2.0 — FORENSIC DETECTOR SYSTEM ARCHITECTURE

## 1. System Overview & Problem Statement

Prior to this recovery mission, the Secura AI 2.0 video forensic pipeline suffered from catastrophic misclassification:
1. **AI Video False Negatives**: Modern generative video synthesis (e.g., UHD latent diffusion models like Sora, CogVideo, SVD, and VGen) generates high-fidelity individual frames that successfully deceive single-frame 2D spatial diffusion classifiers (scoring $P(\text{AI}) \approx 0.05 - 0.08$).
2. **Real Camera Video False Positives**: Authentic camera panning and handheld camera jitter across sparse linspace frames generated artificial step jumps, misleading uncalibrated heuristic scoring.
3. **Singleton State Mutation**: Sub-analyzer branches mutated shared model state via `switch_head`, leading to thread race conditions and unrepeatable predictions.

To solve this fundamentally and permanently, Secura AI 2.0 incorporates **NeurIPS 2025 ReStraV (Representation Straightening for Video Generation Forensics)** sequence modeling, combines it with spatial neural diffusion (Swin Transformer) and physics-based residual shot noise analysis, and enforces strict mathematical invariants.

---

## 2. Multi-Branch Forensic Architecture

```
                                  [ Video Input Stream ]
                                            │
                                            ▼
                              [ VideoFrameSampler ]
                         ┌──────────────────┴──────────────────┐
                         │                                     │
           [ Continuous Consecutive Frames ]         [ Timeline Uniform Frames ]
               (24 frames, step = 1)                 (Uniform linspace + Scene Cuts)
                         │                                     │
                         ▼                                     ▼
        ┌────────────────────────────────┐         ┌───────────────────────────────┐
        │  Branch 3: Learned Temporal    │         │  Branch 4: Spatial Neural     │
        │  Representation (ReStraV)      │         │  Diffusion (Swin-Base)        │
        │  - DINOv2 self-supervised      │         │  - Sensor Shot Noise Variance │
        │    token trajectory            │         │  - FFT Frequency Artifacts    │
        │  - Turning Angle Curvature     │         └───────────────┬───────────────┘
        │  - Calibrated ReStraV MLP      │                         │
        └────────────────┬───────────────┘                         │
                         │                                         │
                         ▼                                         ▼
        ┌────────────────────────────────┐         ┌───────────────────────────────┐
        │  Branch 2: Optical Flow Motion │         │  Branch 7: Container          │
        │  - Farneback Coherence         │         │  Provenance & C2PA Metadata   │
        │  - Discontinuity Index         │         └───────────────┬───────────────┘
        └────────────────┬───────────────┘                         │
                         │                                         │
                         └──────────────────┬──────────────────────┘
                                            │
                                            ▼
                          [ Multi-Layer Evidence Fusion Engine ]
                                  (video_fusion.py)
                                            │
                                            ▼
                           [ Canonical Consumer-First Verdict ]
                         - Model Score P(AI) in [0.00, 1.00]
                         - Strict Decision Threshold: 0.50
                         - Supporting / Contradictory Evidence Ledger
                         - Explicit Confidence & Uncertainty Interval
```

---

## 3. Branch 3: NeurIPS 2025 ReStraV Temporal Sequence Modeling

### Theoretical Foundation
In the human visual cortex and deep self-supervised visual representation models (specifically DINOv2 ViT), natural physical camera motion and object movement follow **perceptually straightened geodesics**: the trajectory of representations bends smoothly, maintaining turning angles predominantly in the range of $40^\circ - 95^\circ$.

In contrast, generative video diffusion models iteratively denoise latent spatial volumes across temporal attention layers. This introduces subtle, unnatural manifold deviations, semantic drift, and high-dimensional trajectory kinks ($> 110^\circ - 125^\circ$), even when individual frames look photorealistic.

### Mathematical Formulation
Given continuous consecutive frames $\{x_0, x_1, \dots, x_{T-1}\}$ ($T=24$, step=1):
1. **DINOv2 Feature Projection**:
   $$z_t = \text{DINOv2}(x_t) \in \mathbb{R}^{D} \quad (D = 98,688)$$
2. **Representation Velocity Vectors**:
   $$\Delta z_t = z_{t+1} - z_t, \quad t \in \{0, \dots, T-2\}$$
3. **Step Distances**:
   $$d_t = \|\Delta z_t\|_2$$
4. **Turning Angles (Curvature)**:
   $$\theta_t = \arccos\left(\frac{\Delta z_t \cdot \Delta z_{t+1}}{\|\Delta z_t\|_2 \|\Delta z_{t+1}\|_2}\right) \in [0, \pi]$$
5. **Geometry Trajectory Feature Vector (21 Dimensions)**:
   $$f = [d_0, \dots, d_6, \; \theta_0, \dots, \theta_5, \; \mu_d, \min(d), \max(d), \sigma_d^2, \; \mu_\theta, \min(\theta), \max(\theta), \sigma_\theta^2]$$
6. **ReStraV Classification**:
   $$z_{\text{norm}} = \frac{f - \mu}{\sigma}$$
   $$\text{logit} = \text{MLP}(z_{\text{norm}})$$
   $$P(\text{AI})_{\text{temporal}} = \sigma(\text{logit})$$

Weights and standardization statistics are permanently frozen in:
`backend/models/weights/restrav_temporal/restrav_mlp.pt`
`backend/models/weights/restrav_temporal/mean.npy`
`backend/models/weights/restrav_temporal/std.npy`

---

## 4. Branch 4: Spatial Frequency & Noise Residuals

- Evaluates sampled keyframes using Swin Transformer (`predict_frame_swin`) without modifying global singleton model state.
- Computes per-frame sensor photon shot noise variance:
  $$\sigma_{\text{noise}}^2 = \text{Var}(I - \text{MedianFilter}(I))$$
  Natural physical sensors exhibit photon shot noise variance typically $> 100 - 500$, whereas latent diffusion decoders produce unnaturally smooth pixel floors ($\sigma^2 < 15$).

---

## 5. Multi-Layer Evidence Fusion & Mathematical Guarantees

### Fusion Formulation
When temporal sequence and spatial branches are available:
$$S_{\text{raw}} = w_{\text{temporal}} \cdot P(\text{AI})_{\text{temporal}} + w_{\text{spatial}} \cdot P(\text{AI})_{\text{spatial}} + w_{\text{motion}} \cdot S_{\text{motion}} + w_{\text{noise}} \cdot S_{\text{noise}}$$
Where:
- $w_{\text{temporal}} = 0.75$ (Primary anchor sequence discriminator)
- $w_{\text{spatial}} = 0.10$
- $w_{\text{motion}} = 0.10$
- $w_{\text{noise}} = 0.05$

### Strict Invariants
1. **Threshold Adherence**:
   $$\text{Predicted Verdict} = \begin{cases} \text{AI\_GENERATED} & \text{if } S_{\text{raw}} \ge 0.50 \\ \text{NOT\_AI\_GENERATED} & \text{if } S_{\text{raw}} < 0.50 \end{cases}$$
2. **Confidence Calibration**:
   $$\text{Confidence} = \begin{cases} S_{\text{raw}} \times 100\% & \text{if } \text{AI\_GENERATED} \\ (1.0 - S_{\text{raw}}) \times 100\% & \text{if } \text{NOT\_AI\_GENERATED} \end{cases}$$
3. **No Singleton State Mutation**: Zero mutation of shared detector heads; thread-safe and re-entrant.
4. **Honest Abstention**: When fewer than 2 primary analyzers succeed, returns `INCONCLUSIVE` with explicit uncertainty interval and abstention reason.
