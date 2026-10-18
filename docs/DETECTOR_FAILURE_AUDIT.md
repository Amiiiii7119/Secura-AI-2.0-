# SECURA AI 2.0 — DETECTOR FAILURE AUDIT
**Investigation Protocol:** `/gravitas` Rigorous Forensic Diagnostics  
**Workspace:** `D:\SecuraAI2`  
**Execution Environment:** Windows 11, Intel/AMD 24-Core CPU, 31.12 GB RAM, PyTorch 2.14.1+cpu  
**Status:** Defect Identified, Diagnosed & Empirically Reproduced  

---

## 1. Executive Summary

A comprehensive empirical forensic investigation of the Secura AI 2.0 image and video detection architecture was conducted to diagnose systemic misclassifications:
1. **AI-generated videos repeatedly misclassified as real.**
2. **Authentic camera footage repeatedly misclassified as AI-generated.**

By tracing the complete lifecycle from media decoding through feature extraction, branch evaluation, and fusion logic, we confirmed that previous iterations relied on superficial score adjustments and an unvalidated curvature heuristic masquerading as a temporal video detector. 

---

## 2. Hardware and Environment Audit

Direct hardware inspection conducted via `torch`, `ctypes`, and OS runtime calls:

| Resource | Specification | Audit Status |
|---|---|---|
| **Platform** | Windows 11 AMD64 | Verified (`observed`) |
| **PyTorch Engine** | PyTorch 2.14.1+cpu | Verified (`executed`) |
| **CUDA / GPU Acceleration** | Disabled / Unavailable (`torch.cuda.is_available() == False`) | Verified (`executed`) |
| **CPU Topology** | 24 Logical Cores | Verified (`executed`) |
| **System Memory** | 31.12 GB Total Physical RAM (10.21 GB Available) | Verified (`executed`) |
| **Disk Storage (D:)** | 588.99 GB Total, 429.34 GB Free | Verified (`executed`) |
| **Disk Storage (C:)** | 688.75 GB Total, 483.56 GB Free | Verified (`executed`) |

**Operational Constraint:** Any neural model or sequence classifier must execute efficiently on a multi-threaded CPU runtime (`torch.set_num_threads(12)`). Heavy GPU-only architectures (e.g. 100-layer 3D ResNets) are infeasible without dedicated acceleration, requiring parameter-efficient temporal representations.

---

## 3. Known-Test Media Forensics & Baseline Execution

### A. Known AI-Generated Video: `8328099-uhd_2160_3840_25fps.mp4`
- **Location:** `C:\Users\ammur\Downloads\8328099-uhd_2160_3840_25fps.mp4`
- **File Size:** 41,494,843 bytes (39.57 MB)
- **SHA-256:** `b25b5b1144c3a83b19380947429c9cfc2f480a824f0fb003af153a07be17e660`
- **Container / Codec:** MP4 container, H.264 video codec (`avc1`)
- **Resolution:** $2160 \times 3840$ (Portrait 4K UHD)
- **Frame Rate:** 25.00 fps
- **Total Frames:** 391 frames
- **True Duration:** 15.64 seconds
- **Ground Truth Claim:** AI-Generated synthetic video (Generative Video Synthesis)

#### Raw Orchestrator Diagnostic Output:
- **Canonical Verdict:** `AI_GENERATED` (`model_score: 0.5798`, `decision_threshold: 0.50`)
- **Branch 1 (RGB & Chromatic):** `score = 0.0533` (Low chromatic jitter)
- **Branch 2 (Motion & Optical Flow):** `score = 0.1470`
- **Branch 3 (Temporal Representation):** `score = 0.8560` (Mean curvature: $1.9091\text{ rad}$, Tortuosity: $5.638$)
- **Branch 4 (Spatial Frequency / Image Detector):** `score = 0.0662` (Mean AI probability: $0.0662$, Peak: $0.1201$, AI Frame Ratio: $0.00$)
- **Branch 7 (Container & Provenance):** `score = 0.0000` (C2PA manifest absent)

#### Key Failure Finding:
When individual frames of this confirmed AI-generated video were fed to 2D image detectors, every single detector failed:
- **`SwinAIImageDetector`:** Frame 0 AI probability = **`0.0996`** (`LIKELY_REAL`)
- **`SecuraCustom` (CLIP Linear Probe):** Frame 0 AI probability = **`0.0445`** (`LIKELY_REAL`)
- **`UniversalFakeDetect`:** Frame 0 AI probability = **`0.2687`** (`LIKELY_REAL`)

**Conclusion:** AI-generated video frames lack the static pixel-level artifacts found in standalone diffusion images (e.g. Midjourney). Evaluating an AI video purely with a 2D image model results in a false-negative score of $\approx 0.05$ (5% AI). In the multi-branch orchestrator, this dragged down the video score to $0.5798$, dangerously close to misclassifying the entire video as authentic.

---

### B. Known Authentic Camera Video: `istockphoto-1282573958-640_adpp_is.mp4`
- **Location:** `C:\Users\ammur\Downloads\istockphoto-1282573958-640_adpp_is.mp4`
- **File Size:** 9,650,477 bytes (9.20 MB)
- **SHA-256:** `9a826477d94cf3426ff3baef7d87b32ea0e051783cf66fa54ae8848a8cb904b6`
- **Container / Codec:** MP4 container, H.264 video codec
- **Resolution:** $768 \times 432$
- **Frame Rate:** 29.97 fps
- **Total Frames:** 535 frames
- **True Duration:** 17.85 seconds
- **Ground Truth Claim:** Authentic physical camera footage (iStock commercial stock footage)

#### Raw Orchestrator Diagnostic Output:
- **Canonical Verdict:** `NOT_AI_GENERATED` (`model_score: 0.4230`, `decision_threshold: 0.50`)
- **Branch 1 (RGB & Chromatic):** `score = 0.2276`
- **Branch 2 (Motion & Optical Flow):** `score = 0.0751`
- **Branch 3 (Temporal Representation):** `score = 0.9356` (Mean curvature: $2.1353\text{ rad}$, Peak: $2.6322\text{ rad}$, Tortuosity: $9.4992$)
- **Branch 4 (Spatial Frequency):** `score = 0.0510`
- **Branch 7 (Container & Provenance):** `score = 0.0000`

#### Key Failure Finding:
**Catastrophic False Positive Trigger in Temporal Branch 3:**
On this 100% authentic camera recording, Branch 3 assigned an AI synthetic score of **`0.9356` (93.56% AI!)** with a trajectory curvature of **$2.1353\text{ rad}$**. 
The unvalidated geometric heuristic assumed that natural camera video follows a straight trajectory in CLIP feature space, while AI video has high curvature. In reality, natural camera motion, panning, perspective change, and subject movement produce huge non-linear trajectories ($> 2.1\text{ rad}$ and tortuosity $9.5$). An untrained heuristic on raw CLIP curvature is completely incapable of distinguishing AI synthesis from camera motion!

---

### C. Live Browser Camera Recording: `camera_capture.webm`
- **Generator:** Browser `MediaRecorder` API via `VideoForensicsWorkspace.tsx`
- **Container / Codec:** WebM container (`video/webm;codecs=vp8` or `vp9`)
- **Observed Behavior:**
  - Browser WebM streams lack EBML duration segment metadata and index cues (`Cues` elements).
  - OpenCV `VideoCapture` returned `duration = 0.00s` and frame seeking failed, causing the frame sampler to abort after frame 0 ($N=1$).
  - With only 1 frame sampled, temporal branches failed (`INSUFFICIENT_DATA`).
  - Defective conditional fallback logic in `video_fusion.py` evaluated default curvature or fallback rules, assigning `AI_GENERATED_VIDEO` even when the spatial score was $0.410$.

---

## 4. Root Causes Identified & Confirmed

| ID | Root Cause | Mechanism & Evidence | Severity |
|---|---|---|---|
| **RC-1** | **Untrained Geometric Heuristic Labeled as "ReStraV"** | `TemporalRepresentationBranch` took raw CLIP ViT-L/14 embeddings, computed trajectory angles between displacement vectors, and applied an ad-hoc formula: `logit = 0.5*curv + 0.3*tort + 0.2*step`. On real camera footage (`istockphoto`), camera panning produced mean curvature of $2.14\text{ rad}$ and tortuosity $9.5$, emitting a false positive score of **0.9356 (93.6% AI)**! | **CRITICAL** |
| **RC-2** | **Static 2D Image Model Mismatch on Video Frames** | `SpatialFrequencyBranch` fed isolated video frames into static image detectors (`Swin` and `SecuraCustom`). On confirmed AI video `8328099`, all 16 frames scored $P(\text{AI}) < 0.12$ (mean: $0.066$). Generative video synthesis artifacts are temporal and motion-based; static 2D image models produce severe false negatives on video frames. | **CRITICAL** |
| **RC-3** | **Unindexed WebM Stream Decoding Failure** | Real-time browser webcam recordings (`camera_capture.webm`) produce unindexed WebM streams. `VideoCapture.get(CAP_PROP_FRAME_COUNT)` returned 0, `duration = 0.00s`, and seek failed, collapsing multi-second video to a single frame ($N=1$). | **HIGH** |
| **RC-4** | **Cross-Request Singleton State Leakage** | `SpatialFrequencyBranch.analyze()` explicitly called `detector.switch_head("SwinAIImageDetector")`. Because `get_ai_image_detector()` is a global singleton, running a video analysis mutated the detector head for all concurrent and subsequent image requests, corrupting production image scoring. | **HIGH** |
| **RC-5** | **Arbitrary Fusion Without Held-Out Calibration** | Branch scores from spatial diffusion (0.06), optical flow (0.14), and pseudo-curvature (0.85) were linearly blended without empirical weight calibration or proper statistical fusion on real vs AI video datasets. | **HIGH** |
| **RC-6** | **Absence of Dedicated Trained Video Sequence Classifier** | The codebase lacked an actual machine-learning classifier trained on temporal sequences of video features. | **CRITICAL** |

---

## 5. Architectural Remediation Strategy

To permanently eliminate these defects without hardcoding or superficial patches:
1. **Separation of Concerns:**
   - **Image Detection:** Isolated 2D pipeline targeting `SecuraCustom` linear probe over CLIP ViT-L/14 projection embeddings.
   - **Video Detection:** Dedicated temporal video pipeline analyzing multi-frame temporal feature sequences using an empirically trained video classifier.
2. **True Video-Level Classifier:**
   - Extract chronological frame representations using a frozen visual backbone.
   - Train a temporal sequence classifier (e.g. Temporal Pooling MLP / Sequence Classifier) on real camera videos vs modern AI synthetic videos.
3. **State Isolation:** Remove all `switch_head` calls from video branches; use local detector instances or pass explicit probe parameters to prevent singleton contamination.
4. **Robust Universal Frame Sampler:** Two-pass stream decoding ensuring accurate duration, uniform chronological frame extraction, and zero-duration prevention for WebM/MP4.
