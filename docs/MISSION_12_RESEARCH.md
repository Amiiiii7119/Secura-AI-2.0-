# MISSION 12 RESEARCH: AI-IMAGE DETECTOR RESTORATION & APPLE-INSPIRED REDESIGN
**Secura AI 2.0 Greenfield Implementation**  
**Date:** 2026-10-17  
**Lead Agents:** Antigravity (Implementation) & Gravitas (Audit, Review & Risk Analysis)  
**Target Repository:** `D:\SecuraAI2`

---

## 1. Executive Summary & Objective

Mission 12 executes a major evolutionary step in Secura AI 2.0:
1. **Restoring Real AI Detector Inference:** Transitioning from the linear probe verification state of Mission 11 to live inference by loading a verified **OpenAI CLIP ViT-L/14** backbone alongside the verified `fc_weights.pth` linear probe head.
2. **Dataset Creation & Custom Head Training:** Building an automated, manifest-based image dataset pipeline (`D:\SecuraAI2\data\ai_detection`) with verified provenance, leakage controls, and training our own custom classification head on frozen CLIP representations to evaluate generalization against the original UniversalFakeDetect head.
3. **Complete Apple-Inspired Frontend Redesign:** Rebuilding the entire Secura AI 2.0 frontend interface according to Apple Human Interface Guidelines (HIG)—emphasizing extreme clarity, typographic hierarchy, generous whitespace, unified neutral palette, polished forensic viewports, and responsive layout.

---

## 2. Environment & Hardware Audit

A comprehensive hardware and runtime audit was conducted on the host machine:

- **Operating System:** Windows 11 Pro 64-bit (Build 10.0.26300)
- **Primary GPU:** NVIDIA GeForce RTX 5070 Laptop GPU
  - Dedicated VRAM: 12,227 MiB (~12 GB GDDR6)
  - Driver Version: 591.84
  - Supported CUDA Driver Capability: CUDA 13.1 / WDDM driver model
  - Current Utilization: 0% at 40°C idle, 19W power draw
- **System Memory:** 32.0 GB Physical RAM
- **Python Runtime:** Python 3.12.7 (MSC v.1941 64-bit) located at `D:\SecuraAI2\.venv`
- **Key Installed Libraries:**
  - FastAPI 0.143.3, Starlette 1.8.0, Uvicorn 0.54.0
  - Pydantic 2.14.1, Pydantic-Core 2.50.1
  - Pillow 12.3.0, NumPy 2.5.4
  - c2pa-python 0.38.0
  - Pytest 9.1.1, Pytest-Cov 7.1.0, Coverage 7.16.2
- **Pretrained Weights Audit:**
  - `D:\SecuraAI2\backend\models\weights\fc_weights.pth`
  - File Size: 4,083 bytes
  - Computed SHA-256: `477100745713bcc957beb2b40859536859b6483fd6301b3b9293151b194c7847`
  - Integrity: **Verified Authentic** (100% byte-for-byte match with official CVPR 2023 release).

---

## 3. Official Model Investigation (UniversalFakeDetect)

### 3.1 Academic Provenance
- **Title:** *Towards Universal Fake Image Detectors that Generalize Across Generative Models*
- **Conference:** IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR 2023)
- **Authors:** Utkarsh Ojha*, Yuheng Li*, Yong Jae Lee (University of Wisconsin–Madison)
- **Official Repository:** `https://github.com/WisconsinAIVision/UniversalFakeDetect`
- **License:** MIT License

### 3.2 Architectural Mechanism
UniversalFakeDetect operates on the premise that pre-trained multi-modal vision-language foundation models (specifically OpenAI CLIP) develop a structured semantic representation space where synthetic generative artifacts cluster together, even when originating from wildly distinct generator families.

```
Input Image (RGB)
       │
       ▼
[CLIP Preprocessing: Bicubic Resize 224 + Center Crop 224 + Normalization]
       │
       ▼
[OpenAI CLIP ViT-L/14 Vision Transformer (Frozen, ~300M Params)]
       │
       ▼
Visual Feature Vector x ∈ ℝ⁷⁶⁸ (Normalized to ‖x‖₂ = 1)
       │
       ▼
[Trained Linear Probe: z = wᵀx + b]
       │
       ├─► Output Logit: z
       └─► Sigmoid Margin: σ(z) = 1 / (1 + e⁻ᶻ)
```

### 3.3 Classification Head Parameters
- Weight vector $w \in \mathbb{R}^{768}$, serialized in `fc_weights/data/0`.
- Bias scalar $b \in \mathbb{R}$, serialized in `fc_weights/data/1` (value: $-0.516701$).
- Weight norm: $\|w\|_2 pprox 6.223$.

---

## 4. Gravitas Critical Review & Risk Identification

Gravitas independently analyzed the proposed experimental design, identifying the following technical and scientific risks:

1. **Risk of Generator Leakage in Dataset Splits:**
   - *Failure Mode:* Training on images from a generator (e.g., Stable Diffusion 1.5) and testing on the same generator produces artificially inflated accuracy that fails completely in real-world deployment on Midjourney or FLUX.
   - *Mitigation:* Strict generator-disjoint testing. Hold out entire generator families exclusively for the test set.
2. **Risk of Feature Space Distortion via Inconsistent Preprocessing:**
   - *Failure Mode:* CLIP ViT-L/14 was trained with specific bicubic resampling and center cropping. Resizing with nearest-neighbor or bilateral filters introduces artificial high-frequency artifacts that corrupt the 768-D embedding.
   - *Mitigation:* Enforce exact bicubic aspect-preserving resize with standard CLIP normalization constants:
     $$\mu = [0.48145466, 0.4578275, 0.40821073], \quad \sigma = [0.26862954, 0.26130258, 0.27577711]$$
3. **Risk of Uncalibrated Probability Exposure:**
   - *Failure Mode:* Displaying $\sigma(z)$ as "95% probability of AI" misleads forensic analysts, because the sigmoid of an uncalibrated linear SVM/logistic head does not reflect real-world base-rate posteriors.
   - *Mitigation:* Present raw logit $z$ alongside uncalibrated margin percentage with mandatory explanatory disclaimers and explicit decision thresholds ($z > 0.1 	o$ AI, $z < -0.1 	o$ Human, $[-0.1, 0.1] 	o$ Inconclusive).
4. **Risk of Over-Styling Frontend:**
   - *Failure Mode:* Cluttering the interface with dark sci-fi neon borders, arbitrary glowing cards, and dense unreadable widgets.
   - *Mitigation:* Adhere strictly to Apple HIG principles: subtle translucent materials, system typography, generous whitespace, unified light/dark appearance, tabular data alignment, and accessible contrast.

---

## 5. Dataset Architecture & Manifest Schema

The dataset pipeline will reside in `D:\SecuraAI2\data\ai_detection` governed by a JSON manifest schema:

```json
{
  "image_id": "gen_sdxl_00123",
  "relative_path": "images/sdxl/00123.png",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "label": "AI_GENERATED",
  "generator_family": "Diffusion",
  "generator_model": "Stable Diffusion XL",
  "source_dataset": "Controlled-Synthetic-Harness",
  "split": "train",
  "width": 1024,
  "height": 1024,
  "format": "PNG",
  "transformations": []
}
```

### Manifest Pipeline Requirements:
- Hash-based deduplication (SHA-256) preventing duplicated images across train/val/test.
- Grouping of crops and perturbations of the same source into the same partition.
- Independent validation partition for threshold and regularization hyperparameter tuning.

---

## 6. Training & Feature Caching Strategy

Because training an entire 300M ViT from scratch on a laptop GPU is both computationally wasteful and prone to catastrophic overfitting on small datasets:
1. **Feature Extraction Phase:** Extract frozen 768-D CLIP representations using GPU batching ($B=32$) or CPU fallback, serializing embeddings into compressed `.npz` feature archives.
2. **Head Optimization Phase:** Train an $\ell_2$-regularized logistic regression head (or linear layer with weight decay) on cached training features. Optimization takes $< 10$ seconds, allowing rigorous cross-validation and hyperparameter sweeping over $C \in [10^{-4}, 10^2]$.
3. **Head Comparison:** Compare the newly trained head directly against the CVPR 2023 `fc_weights.pth` head on the untouched generator-disjoint test partition.

---

## 7. Frontend Redesign Strategy (Apple HIG)

The existing Secura AI frontend will be completely rebuilt from the ground up:
- **Design Tokens:** Strict semantic CSS variables (`--sf-text-primary`, `--sf-bg-surface`, `--sf-border-subtle`, `--sf-accent-blue`, etc.).
- **Typography:** System font stack (`-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", Inter, sans-serif`).
- **Hierarchy:**
  1. Refined Navigation Bar with brand monogram, live status indicator, and theme toggle.
  2. Hero Upload Zone: Clean drag-and-drop dropzone with subtle dashed borders and immediate file validation.
  3. Interactive Forensic Viewport: Large main preview with segmented pill controls (Source, ELA, DCT, Noise Residual) and synchronized zoom/inspect.
  4. Executive Summary Card: Unified evidence synthesis with clear, non-alarmist status chips.
  5. Two-Column Diagnostic Grid: Technical cards for Asset Specs, C2PA Provenance, Metadata & Consistency, and AI-Generated Image Detection.
  6. Structured JSON & Export Drawer: Professional inspector with copy and download capabilities.

---

## 8. Verification & Review Signoff

This research roadmap ensures:
- 100% preservation of all 7 existing forensic layers and Mission 10 Evidence Fusion.
- Complete scientific honesty regarding model capabilities and evaluation data.
- Professional Apple-grade frontend usability and responsive elegance.
