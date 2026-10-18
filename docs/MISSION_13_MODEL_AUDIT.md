# MISSION 13 — AI DETECTOR SCIENTIFIC AUDIT & RECTIFICATION
**Date:** 2026-10-17  
**Auditor:** Antigravity Engineering & Gravitas Scientific Review  
**Project:** Secura AI 2.0  
**Target File:** `data/ai_detection/features/cached_features.npz`, `backend/models/weights/fc_weights.pth`, `backend/scripts/evaluate_ai_detector.py`

---

## 1. Provenance Audit of Cached Feature Representations

### 1.1 Methodology & Checkpoint Inspection
The feature cache `data/ai_detection/features/cached_features.npz` (27 image samples, 768 dimensions per sample) was analyzed for neural backbone lineage.

- **Intended Architecture:** OpenAI CLIP ViT-L/14 (Vision Transformer Large, patch size 14, 304 million parameters, 768-D projection output).
- **Observed Origin:** `extract_deterministic_features` in `backend/scripts/extract_ai_features.py`.
- **Extraction Mechanism:** Procedural spectral and gradient analysis (2D Fast Fourier Transform magnitude spectrum downsampled to 128 bins + 3-channel color histogram statistics + 3x3 Laplacian spatial gradients) projected to 768 dimensions.
- **Root Cause of Fallback:** In Mission 12, downloading the full 933MB PyTorch CLIP weights over the constrained network was deferred to avoid multi-gigabyte stalls.
- **Finding:** The features in `cached_features.npz` are **procedural surrogate features**, NOT real CLIP ViT-L/14 transformer representations.
- **Remediation Action:** Created `data/ai_detection/features/cache_manifest.json` marking the cache status as `UNVERIFIED_PROCEDURAL_SURROGATE`.

---

## 2. Investigation and Resolution of ROC-AUC 0.0000 Discrepancy

### 2.1 The Observed Anomaly
In Mission 12, evaluating the original UniversalFakeDetect probe head (`fc_weights.pth`, CVPR 2023) against the 14-image held-out test split produced:
- **Reported ROC-AUC:** `0.0000`
- **Accuracy:** `0.0%`
- **Reported Custom Head ROC-AUC:** `1.0000`

### 2.2 Mathematical and Empirical Diagnostic
In Mission 13, deterministic sample-by-sample logit extraction was performed across the 14 test samples (4 Real, 10 Diffusion):

| Sample Index | Ground Truth | Generator Family | Original Head Logit ($z$) | Original Head Margin ($\sigma(z)$) | Custom Head Logit | Custom Head Margin |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | `0 (Real)` | Camera | **-0.6734** | **0.3377** | -1.0643 | 0.2565 |
| **1** | `0 (Real)` | Camera | **-0.6722** | **0.3380** | -1.0830 | 0.2529 |
| **2** | `0 (Real)` | Camera | **-0.6837** | **0.3354** | -1.0050 | 0.2680 |
| **3** | `0 (Real)` | Camera | **-0.6854** | **0.3351** | -1.0202 | 0.2650 |
| **4** | `1 (AI)` | Diffusion | **-0.7955** | **0.3110** | -0.4787 | 0.3826 |
| **5** | `1 (AI)` | Diffusion | **-0.8002** | **0.3100** | -0.6044 | 0.3533 |
| **6** | `1 (AI)` | Diffusion | **-0.7864** | **0.3129** | -0.4772 | 0.3829 |
| **7** | `1 (AI)` | Diffusion | **-0.7620** | **0.3182** | -0.5928 | 0.3560 |
| **8** | `1 (AI)` | Diffusion | **-0.8000** | **0.3100** | -0.4118 | 0.3985 |
| **9** | `1 (AI)` | Diffusion | **-0.8109** | **0.3077** | -0.5187 | 0.3732 |
| **10** | `1 (AI)` | Diffusion | **-0.7884** | **0.3125** | -0.4771 | 0.3829 |
| **11** | `1 (AI)` | Diffusion | **-0.7648** | **0.3176** | -0.5916 | 0.3563 |
| **12** | `1 (AI)` | Diffusion | **-0.7978** | **0.3105** | -0.4800 | 0.3822 |
| **13** | `1 (AI)` | Diffusion | **-0.8337** | **0.3029** | -0.5925 | 0.3561 |

### 2.3 Mathematical Proof of Zero ROC-AUC
In `evaluate_ai_detector.py`, ROC-AUC is evaluated via Wilcoxon-Mann-Whitney rank-sum concordance:
$$\text{ROC-AUC} = \frac{1}{|P| \cdot |N|} \sum_{p \in P} \sum_{n \in N} \mathbf{1}[s(p) > s(n)] + 0.5 \cdot \mathbf{1}[s(p) = s(n)]$$

Where $P$ is the set of positive (AI, label=1) samples, and $N$ is the set of negative (Real, label=0) samples.
1. The highest positive score is $s(p)_{\max} = -0.7620$.
2. The lowest negative score is $s(n)_{\min} = -0.6854$.
3. Because $-0.7620 < -0.6854$, **for every positive sample $p$ and every negative sample $n$, $s(p) < s(n)$**.
4. Consequently, $\mathbf{1}[s(p) > s(n)] = 0$ for all $10 \times 4 = 40$ pairs.
5. $\text{ROC-AUC} = \frac{0}{40} = \mathbf{0.0000}$.

### 2.4 Why Did the Logit Inversion Occur?
1. The original probe vector $w_{\text{orig}}$ was optimized on genuine CLIP ViT-L/14 embeddings where synthetic artifacts (e.g. ProGAN, LDM) correlate positively with specific learned directions in latent space.
2. In contrast, the surrogate feature extractor computes normalized FFT and Laplacian energies. On natural photographs, sharp lens focus and high-frequency sensor noise produce higher high-frequency energy than smooth Diffusion textures.
3. Therefore, natural camera photos produced higher surrogate feature dot products with $w_{\text{orig}}$ than diffusion images did, creating an **inverted score ordering** when measured against an untrained linear probe.
4. Conversely, the Custom Secura Head was trained directly on these surrogate features, learning the negative correlation and achieving an apparent ROC-AUC of 1.0000 on the small test partition.

### 2.5 Verification of Metric Calculation
The rank-sum ROC-AUC implementation in `calculate_comprehensive_metrics` was independently verified against Scikit-Learn's definition. The calculation is mathematically exact; the `0.0000` score was not an arithmetic bug, but the precise mathematical consequence of an out-of-distribution feature representation driving complete ranking inversion.

---

## 3. Custom Head Scientific Assessment

- **Dataset Size:** 27 samples (13 Train, 14 Test).
- **Status:** **Exploratory prototype only**.
- **Caveat:** A 14-sample test split with 100% accuracy demonstrates that the linear head successfully separated the surrogate feature vectors of the training generators from real images. It does NOT prove generalization across arbitrary wild AI generators.
- **Production Status:** Secura AI 2.0 maintains that the AI detector's operational status is `BACKBONE_WEIGHTS_UNAVAILABLE`. The API does not claim real-time AI classification unless the neural backbone is loaded and verified.

---

## 4. Model Registry Life Cycle States

To prevent ambiguous states, all models and probes implement the following finite state machine:
- `READY`: Both the neural backbone and classification probe weights are verified, loaded into memory, and validated against sample tensors.
- `LOADING`: Asynchronous checkpoint verification or weights decompression is currently active.
- `UNAVAILABLE`: Probe weights or backbone weights are not present on local storage.
- `FAILED`: Checksum mismatch, corrupted archive, or initialization exception.
- `INCOMPATIBLE`: Checkpoint feature dimension does not match probe input dimension ($D \neq 768$).
