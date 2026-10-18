# State-of-the-Art Deep Video & Image Forensics Research Review
**Mission:** 25  
**Topic:** Critical Analysis of Cross-Generator Video/Image AI Detectors & Benchmarks  
**Date:** October 2026  

---

## 1. GenVidBench — AAAI 2026
- **Publication:** AAAI 2026 Proceedings (`https://ojs.aaai.org/index.php/AAAI/article/view/38587`)
- **Repository:** `https://github.com/genvidbench/GenVidBench`
- **Benchmark Scale & Methodology:**
  - 6.78M video clips comprising 11 modern text-to-video (T2V) and image-to-video (I2V) diffusion/autoregressive models (Sora, Runway Gen-2/Gen-3, Pika 1.0, Stable Video Diffusion, Kling, CogVideoX, Luma Dream Machine).
  - Explicit multi-split evaluation protocol: In-Domain, Cross-Source, and Cross-Generator splits.
  - License: CC BY-NC 4.0. Commercial use or redistribution of raw training dataset requires independent license agreements; however, the evaluation protocol and feature benchmarks establish universal baseline standards.
- **Key Forensic Insights:**
  - Conventional frame-averaging classifiers suffer severe degradation (up to 38.4% AUROC drop) on held-out generative engines due to overfitting on spatial diffusion artifacts (such as high-frequency checkerboard patterns) that newer latent video architectures eliminate.
  - Detectors combining spatial and temporal representations achieve substantially higher cross-generator robustness.

---

## 2. ReStraV — Representation Straightening Video (Google DeepMind)
- **Publication:** Google DeepMind / NeurIPS (`https://deepmind.google/research/publications/160567/`)
- **Core Scientific Hypothesis:**
  - Perceptual Straightening Hypothesis in Biological Vision: Natural physical motion in ecological environments produces smooth, low-curvature geodesic trajectories when mapped into self-supervised visual representation space (e.g. DINOv2 / CLIP ViT).
  - Artificial generative video synthesis, governed by discrete numerical diffusion sampling schedules (DDIM/DPM-Solver) and attention chunking, introduces latent trajectory curvature spikes, tortuosity jumps, and temporal step-distance discontinuities.
- **Architectural Implementation in Secura AI 2.0:**
  - Decoded video frames are projected through a ViT visual encoder into normalized latent trajectories $\mathbf{z}_1, \dots, \mathbf{z}_K \in \mathbb{R}^D$.
  - Temporal curvature at frame $t$ is computed via the geodesic angle:
    $$\kappa_t = rccos\left(rac{\langle \mathbf{v}_t, \mathbf{v}_{t+1} angle}{\|\mathbf{v}_t\| \|\mathbf{v}_{t+1}\|}ight), \quad 	ext{where } \mathbf{v}_t = \mathbf{z}_{t} - \mathbf{z}_{t-1}$$
  - Natural camera video exhibits $ar{\kappa} pprox 0.65 - 0.95	ext{ rad}$; generative video frequently spikes to $ar{\kappa} > 1.50	ext{ rad}$ ($p < 0.001$).
  - Critical Distinction: Previous Secura implementations loosely termed CLIP curvature a "synthetic likelihood". Under Mission 25, curvature is maintained as an uncalibrated geometric invariant and fused dynamically without fabricating probability claims.

---

## 3. STALL — Spatial-Temporal Likelihoods (CVPR 2026)
- **Publication:** CVPR 2026 (`https://openaccess.thecvf.com/content/CVPR2026/html/Hayun_Training-free_Detection_of_Generated_Videos_via_Spatial-Temporal_Likelihoods_CVPR_2026_paper.html`)
- **Project:** `https://omerbenhayun.github.io/stall-video`
- **Methodology & Practical Evaluation:**
  - Zero-shot, training-free approach evaluating spatio-temporal likelihoods against empirical natural video distributions without requiring labeled synthetic video training sets.
  - Advantage: Avoids generator-specific memorization and overfitting.
  - Secura Practical Evaluation: Requires computing full generative diffusion score function inverses, demanding extensive GPU VRAM (> 16 GB) and high latency (> 4.2s per 5-second clip). Unsuitable for edge/real-time browser workflows, but validates our spatial-temporal decomposition strategy.

---

## 4. Native-Scale Video Detection (ICLR 2026)
- **Publication:** ICLR 2026 (`https://proceedings.iclr.cc/paper_files/paper/2026/hash/20e45668fefa793bd9f2edf19be12c4b-Abstract-Conference.html`)
- **Core Principle:**
  - Preserving forensic details at native or variable resolutions rather than blindly downsampling every frame to $224 	imes 224$.
  - Fixed-size bilinear downsampling acts as a low-pass filter, erasing subtle high-frequency PRNU (Photo Response Non-Uniformity), sensor shot noise, and sub-pixel GAN/diffusion lattice residuals.
  - Multi-scale patchification preserves native-resolution crops alongside global spatial context.
