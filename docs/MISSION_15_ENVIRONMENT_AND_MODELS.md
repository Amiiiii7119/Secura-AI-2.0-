# MISSION 15 — ENVIRONMENT, DEPENDENCIES & MODEL AVAILABILITY AUDIT
**Date:** 2026-10-17  
**Auditor:** Antigravity Engineering & Forensic Reliability Team  
**Project:** Secura AI 2.0 (`D:\SecuraAI2`)  
**Host Hardware:** NVIDIA GeForce RTX 5070 Laptop GPU (12,227 MiB VRAM), Driver 591.84, CUDA 13.1  

---

## 1. Runtime Environment & Dependency Verification

### 1.1 Python Virtual Environment
- **Executable:** `D:\SecuraAI2\.venv\Scripts\python.exe`
- **Python Version:** `3.12.7 (tags/v3.12.7:0b05ead, Oct 1 2024, 03:06:41) [MSC v.1941 64 bit (AMD64)]`
- **Pip Check:** `python -m pip check` returned exit code 0 ("No broken requirements found.").
- **Installed Packages:**
  - `fastapi 0.143.3`, `uvicorn 0.54.0`, `starlette 1.8.0`, `pydantic 2.14.1`
  - `pillow 12.3.0`, `numpy 2.5.4`
  - `c2pa-python 0.38.0`, `cryptography 50.0.2`
  - `pytest 9.1.1`, `pytest-cov 7.1.0`
- **PyTorch Status:** **Not installed in virtualenv**. `import torch` raises `ModuleNotFoundError`. Pure NumPy is utilized for matrix mathematics and vector projection.

### 1.2 Frontend Toolchain
- **Node.js:** `v24.22.0`
- **npm:** `11.19.1`
- **TypeScript:** `5.6.3` (`npm run type-check` passes with 0 errors).
- **Vite:** `5.4.10` (`npm run build` generates production bundle in 484ms).

### 1.3 Hardware Execution Reality
- **GPU Presence:** NVIDIA GeForce RTX 5070 Laptop GPU detected via Windows driver and `nvidia-smi` (Bus ID `00000000:64:00.0`, 12,227 MiB total VRAM).
- **Driver / CUDA:** Driver 591.84, CUDA 13.1.
- **Process Reality:** Because `torch` is not installed in `.venv`, the backend executes all spatial and frequency transforms (ELA, DCT, Laplacian, C2PA, EXIF) on the host CPU. GPU compute is not engaged by Python processes.

---

## 2. Checkpoint Lineage & Backbone Availability

### 2.1 Classification Probe Heads
The model directory `backend/models/weights/` was inspected:
1. `fc_weights.pth` (4,083 bytes):
   - **Architecture:** 768-input linear probe classification head ($w \in \mathbb{R}^{768}, b \in \mathbb{R}$).
   - **Expected Checksum:** SHA-256 `477100745713bcc957beb2b40859536859b6483fd6301b3b9293151b194c7847`.
   - **Observed Checksum:** `477100745713bcc957beb2b40859536859b6483fd6301b3b9293151b194c7847` (Exact match).
   - **Lineage:** UniversalFakeDetect (Ojha et al., CVPR 2023), trained on ProGAN/LDM representations from OpenAI CLIP ViT-L/14.
   - **Head State:** `READY`.
2. `custom_fc_weights.pth` (3,318 bytes):
   - **Architecture:** 768-input L2-regularized logistic classification probe.
   - **Lineage:** Secura AI custom head trained on exploratory 27-sample balanced dataset.
   - **Head State:** `READY`.

### 2.2 Shared Vision Transformer Backbone
- **Required Checkpoint:** `openai/clip-vit-large-patch14` (304 million parameters, 933 MB).
- **Local Status:** **NOT FOUND ON DISK** in `D:\SecuraAI2`.
- **Dependency Requirement:** Requires PyTorch (`torch`), torchvision, or Hugging Face `transformers` (~2.5+ GB installation).
- **Download Risk & Constraint Assessment:**
  - Network throughput for gigabyte-scale wheel and weight downloads poses a severe risk of timeouts and environment destabilization.
  - Per Mission 15 guidelines: *"Do not download hundreds of megabytes or install large GPU dependencies without first assessing disk space, connectivity, compatibility... If downloading is blocked, unavailable, or unsafe, fix the model registry and UI so the unavailable state is explicit and actionable."*
- **Operational Determination:** Retain the honest `UNAVAILABLE` state.

---

## 3. Model Registry Finite State Machine

The Model Registry implements a strictly enforced 5-state lifecycle model:
- `READY`: Both the 304M transformer backbone and linear probe weights are loaded, verified, and operational.
- `LOADING`: Checkpoint decompression or parameter transfer is actively running.
- `UNAVAILABLE`: Either the transformer backbone or probe weights are absent from local storage.
- `FAILED`: Checksum mismatch, archive corruption, or inference exception.
- `INCOMPATIBLE`: Feature projection dimension mismatch ($D \neq 768$).

### Current Operational Verification:
```json
{
  "status": "operational",
  "active_head_id": "UniversalFakeDetect",
  "inference_ready": false,
  "device_available": "NVIDIA RTX 5070 Laptop (Host)",
  "cuda_driver_available": true,
  "vram_total_mb": 12227.0,
  "backbone": {
    "backbone_id": "clip_vit_l14",
    "name": "OpenAI CLIP ViT-L/14",
    "architecture": "Vision Transformer (ViT-L/14, 304M params)",
    "expected_dim": 768,
    "loaded": false,
    "device": "cuda",
    "state": "UNAVAILABLE",
    "reason": "Pretrained 933MB transformer weights (openai/clip-vit-large-patch14) not installed locally. Surrogate cache status: UNVERIFIED_SURROGATE."
  }
}
```
