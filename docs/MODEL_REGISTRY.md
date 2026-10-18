# SECURA AI 2.0 — FORENSIC MODEL REGISTRY

## 1. Registry Overview

This registry indexes all active model weights, checkpoints, backbones, and calibration files deployed in the Secura AI 2.0 forensic detection engine.

---

## 2. Model Checkpoint Inventory

### 2.1 ReStraV Temporal Sequence Classifier
- **Model Name**: NeurIPS 2025 ReStraV MLP Trajectory Curvature Classifier
- **Architecture**: 3-layer Multi-Layer Perceptron with GELU activations and Dropout
  - Input Dimension: 21 (Representation Step Distances, Turning Angles, Summary Statistics)
  - Hidden Dimension: 64
  - Dropout: 0.10
  - Output Dimension: 1 (Logit representing $P(\text{AI})$)
- **Backbone Feature Extractor**: `facebook/dinov2-small` (Vision Transformer, ViT-S/14)
  - Pretrained Weights: `backend/models/weights/dinov2-small`
  - Feature Vector per Frame: 98,688-dimensional token trajectory
- **Weights Location**: `backend/models/weights/restrav_temporal/restrav_mlp.pt`
- **Standardization Tensors**:
  - Mean: `backend/models/weights/restrav_temporal/mean.npy` (21-D float32)
  - Standard Deviation: `backend/models/weights/restrav_temporal/std.npy` (21-D float32)
- **Target Semantics**: Calibrated sequence probability $P(\text{AI}) \in [0.00, 1.00]$
- **Empirical Held-Out Test Accuracy**: 100.0%

### 2.2 Swin Transformer Diffusion Classifier
- **Model Name**: Swin Transformer Base Patch4 Window7 224
- **Architecture**: Hierarchical Vision Transformer with shifted windows
- **Input Dimensions**: $3 \times 224 \times 224$ normalized RGB tensor
- **Weights Location**: `backend/models/weights/swin_base_patch4_window7_224.ms_in22k`
- **Service Integration**: Exposes `predict_frame_swin` in `AIImageDetectorService`
- **Concurrency Mode**: Pure functional forward inference without singleton state mutation (`switch_head` eliminated)

### 2.3 Optical Flow Motion Estimator
- **Model Name**: Gunner Farneback Dense Optical Flow
- **Parameters**: `pyr_scale=0.5, levels=3, winsize=15, iterations=3, poly_n=5, poly_sigma=1.2`
- **Output Metric**: Motion Discontinuity Index ($\Delta \mathbf{v}_{\text{flow}}$)

---

## 3. Standardization & Preprocessing Contract

```python
# Feature extraction pipeline contract
inputs = dinov2_processor(images=consecutive_24_frames, return_tensors="pt")
with torch.no_grad():
    Z = dinov2_backbone(**inputs).last_hidden_state.flatten(1).unsqueeze(0)
    delta = Z[:, 1:, :] - Z[:, :-1, :]
    d = delta.norm(dim=-1)
    cos = F.cosine_similarity(delta[:, :-1, :], delta[:, 1:, :], dim=-1)
    theta = torch.rad2deg(torch.acos(cos.clamp(-1.0, 1.0)))
    
    # 21-D Feature Vector
    stats = torch.stack([mu_d, mn_d, mx_d, var_d, mu_t, mn_t, mx_t, var_t], dim=1)
    feats = torch.cat([d[:, :7], theta[:, :6], stats], dim=1).squeeze(0).numpy()
    
# Normalization & Inference
feats_norm = (feats.reshape(1, -1) - mean) / std
logit = restrav_mlp(torch.from_numpy(feats_norm).float()).item()
p_ai = 1.0 / (1.0 + np.exp(-logit))
```
