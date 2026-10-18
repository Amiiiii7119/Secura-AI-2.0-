# SECURA AI 2.0 — BENCHMARK DATASET & EVALUATION PROTOCOL

## 1. Dataset Overview & Construction Methodology

To eliminate evaluation bias, benchmark leakage, and synthetic artifacts, Secura AI 2.0 established a 25-video curated benchmark manifest (`backend/data/video_dataset_manifest.json`) covering:
- **Total Videos**: 25
- **Class Balance**: 13 AI Generated (52.0%) vs 12 Authentic Real Camera (48.0%)
- **Split Distribution**:
  - `test`: 7 videos (4 AI, 3 Real — held-out for final release gate)
  - `val`: 6 videos (3 AI, 3 Real)
  - `train`: 12 videos (6 AI, 6 Real)

---

## 2. Generator & Camera Distribution

| Generator / Source Category | Sample Count | Ground Truth | Resolution Range | Motion Characteristics |
| :--- | :---: | :---: | :---: | :--- |
| **Sora / Pika UHD Latent Diffusion** (`sora_or_pika_uhd`) | 1 | AI | $2160 \times 3840$ (4K UHD) | Slow cinematic camera orbit, photorealistic skin and hair, high frame-level texture realism |
| **Stability AI SVD** (`stability_svd`) | 1 | AI | $576 \times 1024$ | Video diffusion interpolation, fluid dynamics morphing |
| **CogVideo** (`cogvideo`) | 5 | AI | $480 \times 720$ | Diffusion text-to-video, high object deformation, semantic drift |
| **VGen (T2V/I2V)** (`vgen`) | 5 | AI | $512 \times 512$ - $720 \times 1280$ | Complex animal kinematics, non-rigid surface transformations |
| **Meta VSC Benchmark** (`meta_vsc`) | 8 | Real | $720 \times 1280$ | Natural camera panning, zooming, handheld walking, varied indoor/outdoor lighting |
| **iStock User Footage** (`istockphoto`) | 1 | Real | $432 \times 768$ | Handheld smartphone camera recording, user facial and environmental capture |
| **Secura Physical Media / Fixtures** | 4 | Real / AI | $480 \times 640$ - $1080 \times 1920$ | Benchmark verification fixtures, webcam capture, baseline camera stream |

---

## 3. Representation Space Geodesics (Turning Angle Distribution)

Feature trajectory analysis across 24 consecutive frame windows reveals strong separability in turning angles:

$$\theta_t = \arccos\left(\frac{\Delta z_t \cdot \Delta z_{t+1}}{\|\Delta z_t\|_2 \|\Delta z_{t+1}\|_2}\right)$$

| Class | Mean Turning Angle ($\mu_\theta$) | Peak Turning Angle ($\max \theta$) | Perceptual Straightening |
| :--- | :---: | :---: | :--- |
| **Authentic Real Camera** | $42^\circ - 99^\circ$ | $\le 105^\circ$ | **Straightened Geodesics**: Natural optics follow continuous Newton-Euler inertial mechanics |
| **Generative AI Diffusion** | $98^\circ - 116^\circ$ | $115^\circ - 127^\circ$ | **Manifold Kinks**: Iterative noise inversion creates erratic turns in self-supervised token space |

---

## 4. Evaluation Protocol

1. **Blind Inference**: Analyzers receive raw video bytes with no metadata or filename clues.
2. **Fixed Canonical Decision Threshold**: Model score $S \in [0.00, 1.00]$ is mapped to binary output using threshold $0.50$ ($S \ge 0.50 \implies \text{AI\_GENERATED}$).
3. **No Retrospective Threshold Tuning**: The decision threshold $0.50$ is permanently fixed across all splits.
4. **Automated Benchmark Runner**: Automated execution via `backend/app/evaluation/run_benchmark.py`.
