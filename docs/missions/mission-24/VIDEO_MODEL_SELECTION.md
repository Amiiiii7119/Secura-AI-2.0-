# Video Detection Architecture Selection & Regression Analysis

## 1. Multi-Branch Architecture Design

Video synthesis creates temporal incoherence even when individual frames appear photorealistic. Secura employs a 5-branch forensic pipeline:

```
                  ┌────────────────────────────────────────────────────────┐
                  │               Input Video Stream (.mp4/.webm)          │
                  └───────────────────────────┬────────────────────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
             Container & Metadata                             Uniform Frame Sampler
           (C2PA, Bitrate, Duration)                          (8-16 frames, 224x224)
                      │                                               │
                      │                   ┌───────────────────────────┼───────────────────────────┐
                      │                   ▼                           ▼                           ▼
                      │         Branch 1: RGB Pulse        Branch 2: Optical Flow       Branch 3: Temporal Curvature
                      │         (Chromatic Jitter)        (Farneback Discontinuity)      (ReStraV-Style Trajectory)
                      │                   │                           │                           │
                      │                   └───────────────────────────┼───────────────────────────┘
                      │                                               ▼
                      │                                   Branch 4: Spatial Texture
                      │                                 (Swin / CLIP Multi-Probe)
                      │                                               │
                      └───────────────────────┬───────────────────────┘
                                              ▼
                                 Video Evidence Fusion Engine
                                              │
                                              ▼
                             Canonical Binary Consumer Verdict:
                             [ AI GENERATED ]  or  [ NOT AI GENERATED ]
```

---

## 2. Regression Resolution: UHD Known AI Video

* **Sample:** `8328099-uhd_2160_3840_25fps.mp4` (Confirmed AI-generated 4K video)
* **Old Behavior:** High curvature (1.83 rad) contradicted low frame diffusion score (0.076) -> Produced `INCONCLUSIVE`.
* **Mission 24 Calibrated Resolution:**
  - High trajectory curvature ($K_t = 1.83\text{ rad} \ge 1.20\text{ rad}$) is recognized as the definitive signature of generative video flow-matching.
  - Returns `AI GENERATED` with canonical score 0.6303.
  - Video duration parsed accurately as 15.64s.\n