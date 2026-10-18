# MISSION 15 — SCIENTIFIC AUDIT OF AI DETECTION SUBSYSTEM
**Date:** 2026-10-17  
**Auditors:** Antigravity Engineering & Gravitas Scientific Review  
**Project:** Secura AI 2.0 (`D:\SecuraAI2`)  
**Target Artifacts:** `data/ai_detection/features/cached_features.npz`, `cache_manifest.json`, `dataset_manifest.json`, `fc_weights.pth`, `custom_fc_weights.pth`, `extract_ai_features.py`, `evaluate_ai_detector.py`  

---

## 1. Executive Scientific Verdict

| Assessment Domain | Verified Finding | Scientific Reliability |
| :--- | :--- | :--- |
| **Feature Representation Provenance** | Cached features were generated via procedural FFT, color histogram, and Laplacian gradients, **NOT** OpenAI CLIP ViT-L/14 neural network weights. | `UNVERIFIED_PROCEDURAL_SURROGATE` — Must never be used to substantiate claims regarding CLIP or UniversalFakeDetect. |
| **ROC-AUC 0.0000 Root Cause** | Inverted rank concordance on out-of-distribution surrogate vectors; natural camera high frequencies produced higher dot products with $w_{\text{orig}}$ than diffusion textures. | **Mathematically proven**: Concordance = 0/40 pairs $\implies$ ROC-AUC = 0.0000. Does NOT imply the original CVPR 2023 probe is broken on genuine CLIP embeddings. |
| **Secura Custom Head** | Trained on the 27-sample surrogate feature set. Achieved apparent 1.0000 AUC on the 14-sample held-out test split. | **Exploratory prototype only**. High performance on 14 surrogate vectors does not demonstrate generalization across real-world generative models. |
| **Inference Path & Availability** | Real transformer backbone (`openai/clip-vit-large-patch14`) is not installed locally. Engine returns `BACKBONE_WEIGHTS_UNAVAILABLE`. | `PASS_VERIFIED` — **Zero fabricated scores**. Raw scores and predictions are null; system honestly declines classification without neural weights. |

---

## 2. Feature Provenance & Cache Audit

### 2.1 Inspection of Feature Extraction Pipeline
Inspection of `backend/scripts/extract_ai_features.py` confirms the operational mechanism of `extract_deterministic_features`:
- **Input:** Pillow image converted to RGB, resized bicubically to $224 \times 224$.
- **Dimensions:** Normalized 768-D vector composed of:
  1. Channel means and standard deviations (6 dimensions).
  2. 2D FFT magnitude spectrum downsampled to $16 \times 8$ (128 dimensions).
  3. 3×3 Laplacian spatial gradient statistics (128 dimensions).
  4. Color histogram spatial binning (506 dimensions).
- **Intended Neural Architecture:** OpenAI CLIP ViT-L/14 (304 million parameters, 768-D visual projection).
- **Lineage Certification:** The cache manifest `data/ai_detection/features/cache_manifest.json` was updated and certified as `UNVERIFIED_PROCEDURAL_SURROGATE`. The codebase strictly forbids presenting these procedural vectors as neural embeddings.

---

## 3. Mathematical Resolution of the ROC-AUC 0.0000 Discrepancy

### 3.1 The Diagnostic Logit Distribution
Sample-by-sample logit extraction was performed across the 14 held-out test split samples (4 Real camera photos, 10 Diffusion images) using the original CVPR 2023 linear probe weights ($w_{\text{orig}}, b_{\text{orig}}$):

| Sample ID | Ground Truth ($y$) | Generator Family | Logit $z = w \cdot x + b$ | Sigmoid Margin $\sigma(z)$ |
| :--- | :--- | :--- | :--- | :--- |
| `real_nature_03` | 0 (Real) | Camera Photo | **-0.6734** | **0.3377** |
| `real_nature_04` | 0 (Real) | Camera Photo | **-0.6722** | **0.3380** |
| `real_urban_03` | 0 (Real) | Camera Photo | **-0.6837** | **0.3354** |
| `real_urban_04` | 0 (Real) | Camera Photo | **-0.6854** | **0.3351** |
| `ai_diff_01` | 1 (AI) | Diffusion | **-0.7955** | **0.3110** |
| `ai_diff_02` | 1 (AI) | Diffusion | **-0.8002** | **0.3100** |
| `ai_diff_03` | 1 (AI) | Diffusion | **-0.7864** | **0.3129** |
| `ai_diff_04` | 1 (AI) | Diffusion | **-0.7620** | **0.3182** |
| `ai_diff_05` | 1 (AI) | Diffusion | **-0.8000** | **0.3100** |
| `ai_diff_06` | 1 (AI) | Diffusion | **-0.8109** | **0.3077** |
| `ai_diff_07` | 1 (AI) | Diffusion | **-0.7884** | **0.3125** |
| `ai_diff_08` | 1 (AI) | Diffusion | **-0.7648** | **0.3176** |
| `ai_diff_09` | 1 (AI) | Diffusion | **-0.7978** | **0.3105** |
| `ai_diff_10` | 1 (AI) | Diffusion | **-0.8337** | **0.3029** |

### 3.2 Mathematical Proof of AUC Calculation
The Wilcoxon-Mann-Whitney rank-sum metric calculates:
$$\text{ROC-AUC} = \frac{1}{|P| \cdot |N|} \sum_{p \in P} \sum_{n \in N} \mathbf{1}[s(p) > s(n)] + 0.5 \cdot \mathbf{1}[s(p) = s(n)]$$

Where $P$ is the positive class (AI, $y=1$, $|P|=10$), and $N$ is the negative class (Real, $y=0$, $|N|=4$).
1. The highest positive score is $s(p)_{\max} = -0.7620$.
2. The lowest negative score is $s(n)_{\min} = -0.6854$.
3. Because $-0.7620 < -0.6854$, every positive sample has a score strictly less than every negative sample:
   $$\forall p \in P, \forall n \in N: \quad s(p) < s(n)$$
4. Therefore, $\mathbf{1}[s(p) > s(n)] = 0$ for all $10 \times 4 = 40$ evaluated pairs.
5. Consequently:
   $$\text{ROC-AUC} = \frac{0}{40} = \mathbf{0.0000}$$

### 3.3 Scientific Implication
- **What this proves:** The surrogate spectral/gradient representation vectors do not map to the hyperplane of UniversalFakeDetect. Natural photographic high frequencies projected more positively along $w_{\text{orig}}$ than diffusion images, causing an inverted ranking.
- **What this does NOT prove:** This does **not** prove that the CVPR 2023 linear probe is inverted when evaluated on genuine OpenAI CLIP ViT-L/14 representations.

---

## 4. Score Direction, Thresholds & Mapping Semantics

The score semantics across the codebase are formalized as follows:
- **Decision Boundary Threshold:** $\tau = 0.0$ (raw logit $z$).
- **Score Semantics:**
  - $z > 0.1 \implies \text{Predicted Class: 'artificial'}$, Decision: `AIDetectionDecision.AI_GENERATED_CLASS`.
  - $z < -0.1 \implies \text{Predicted Class: 'human'}$, Decision: `AIDetectionDecision.REAL_IMAGE_CLASS`.
  - $-0.1 \le z \le 0.1 \implies$ Decision: `AIDetectionDecision.INCONCLUSIVE`.
- **Margin Calculation:** $\sigma(z) = \frac{1}{1 + e^{-\text{clip}(z, -30, 30)}}$.
- **Mandatory Caveat:** The margin $\sigma(z)$ is an uncalibrated sigmoid projection; it is **NOT a Bayesian posterior probability** of synthetic origin.

---

## 5. Verification of Model Availability & Honesty

1. The API endpoint `POST /api/v1/analyze/image` executes the multi-layer pipeline without fabricating AI detector output.
2. In the absence of local transformer weights, the detector returns:
   ```json
   {
     "available": false,
     "model_name": "UniversalFakeDetect (CVPR 2023)",
     "model_status": "UNAVAILABLE",
     "decision_status": "UNAVAILABLE",
     "raw_score": null,
     "uncalibrated_margin": null,
     "predicted_class": null,
     "error_code": "BACKBONE_WEIGHTS_UNAVAILABLE"
   }
   ```
3. The application never substitutes procedural features for neural embeddings during live inference.
