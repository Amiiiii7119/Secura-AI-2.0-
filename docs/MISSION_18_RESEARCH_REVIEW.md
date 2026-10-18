# MISSION 18 — SCIENTIFIC RESEARCH REVIEW & DETECTOR CANDIDATE EVALUATION
**Project:** Secura AI 2.0  
**Research Scope:** AI Video Detection, Representation Straightening, Temporal Trajectories, Motion Geometry, Provenance  
**Standard:** Gravitas Exhaustive / ASD-STE100  
**Timestamp:** 2026-10-18T12:02:00Z  

---

## 1. Candidate Methods & Literature Evaluation

| Method & Source | Target Task | Official Code Availability | Checkpoint Availability | License | Runtime / Memory Profile | Known Limitations | Reproduction Status | Decision |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **ReStraV**<br>*(Bielefeld, Google DeepMind, Honda, CSHL 2024)* | AI-Generated Video Detection (General T2V/I2V) | Open paper; conceptual formulation | Pretrained foundational visual encoders (DINOv2, CLIP ViT-L/14) | Apache 2.0 / MIT | ~120-250ms for 16 frames on CPU | Sensitive to camera motion cuts if not partitioned | **Reproduction Feasible:** Geometric trajectory & curvature pipeline implemented on foundational visual representations | **INTEGRATE** (Core Priority Branch) |
| **GenVidBench**<br>*(Ni et al., AAAI 2025, arXiv:2501.11340)* | 6.78M Benchmark across 11 AI Video Generators | Benchmark repository & evaluation splits | Benchmark splits & metadata | Academic / Research | Requires TB-scale storage for full dataset | Full 6.7M dataset infeasible for local download | **Stratified Subset Evaluation:** Protocol used for cross-generator evaluation splits and leakage prevention | **ADOPT PROTOCOL & BENCHMARK TAXONOMY** |
| **DeCoF / GVF**<br>*(He et al., arXiv:2405.04133)* | Local Motion Defects & Global Temporal Appearance | Paper & model architecture | GVF evaluation protocol | Research | Dense flow computation is compute-heavy | Dense optical flow can be slow on CPU for high resolutions | **Lightweight Farnebäck Motion Geometry:** Integrated for local-vs-global motion agreement and scene-cut filtering | **INTEGRATE** (Branch 2 Motion Engine) |
| **Deepfake Detection Challenge (DFDC)**<br>*(Meta AI / Kaggle 2020)* | Facial Manipulation & Face-Swapping | Open public dataset splits | Various community checkpoints | CC-BY-NC | Variable depending on face detector | Only applies when faces are detected; 0% value on non-human scenes | **Separate Task Distinction:** Maintained strictly for facial forgery detection | **INTEGRATE as Optional Branch 6** (Never dictate full-video verdict) |
| **DeeperForensics-1.0**<br>*(Jiang et al., CVPR 2020)* | Real-World Face Forgery with Perturbations | Open dataset | Face-swap models | Academic | Heavy multi-view pipeline | Face-only target domain | Task-separated validation | **BENCHMARK REFERENCE** |
| **C2PA Video Specification (v2.2)**<br>*(Coalition for Content Provenance & Authenticity)* | Cryptographic Provenance & Assertion Manifests | C2PA Rust toolchain (c2patool) | Self-signed / CA certificates | MIT / Apache 2.0 | < 10ms container inspection | Absent manifest does NOT indicate AI generation | **Strict Independence:** Cryptographic claims verified separately from pixel-level synthesis detection | **INTEGRATE** (Branch 7 Provenance Engine) |

---

## 2. Deep Dive: Theoretical Foundations

### 2.1 ReStraV: Representation Straightening for Video
The biological visual system performs *perceptual representation straightening* (Hénaff et al., *Nature Neuroscience* 2019): continuous natural video inputs are mapped through the visual cortex into trajectories with low temporal curvature, enabling predictable neural extrapolation.

In contrast, synthetic video generation pipelines (latent diffusion models, flow matching, and autoregressive transformers) exhibit **temporal curvature anomalies**:
1. **Curvature Metric ($):**
   Given a sequence of $-normalized visual embeddings  = [z_1, z_2, \dots, z_T] \in \mathbb{R}^{T 	imes D}$ extracted by a foundational vision transformer:
   \cos(	heta_t) = rac{(z_t - z_{t-1}) \cdot (z_{t+1} - z_t)}{\|z_t - z_{t-1}\|_2 \cdot \|z_{t+1} - z_t\|_2}
   K_t = rccos(	ext{clip}(\cos(	heta_t), -1.0, 1.0))
   Natural camera motion produces small deflection angles $	heta_t pprox 0$ ( 	o 0$), whereas generative videos produce high directional variance and unnatural trajectory kinks.
2. **Trajectory Tortuosity ($	au$):**
   	au = rac{\sum_{t=1}^{T-1} \|z_{t+1} - z_t\|_2}{\|z_T - z_1\|_2 + \epsilon}
   Straight geodesic paths yield $	au pprox 1.0$. Highly oscillating or unstable synthetic videos exhibit $	au \gg 1.0$.
3. **Stepwise Distance Consistency:**
   Step distances  = 1 - (z_t \cdot z_{t+1})$ in natural videos change smoothly. Sudden spikes in $ indicate either a scene cut or a generative temporal breakdown.

### 2.2 Local Motion Geometry (OpenCV Farnebäck Optical Flow)
To ensure legitimate camera panning, zooming, and scene cuts are not misclassified as generative jitter:
- Compute dense optical flow $\mathbf{u}(x, y), \mathbf{v}(x, y)$ between consecutive downscaled grayscale frames.
- Calculate **Motion Direction Consistency**:
  \Phi = 	ext{std}(rctan2(\mathbf{v}, \mathbf{u}))
- Calculate **Motion Magnitude Discontinuity**:
  M_{	ext{diff}} = |ar{M}_t - ar{M}_{t-1}|
- **Scene-Cut Filter:** If global optical flow and chromatic difference simultaneously spike ( > 	heta_{	ext{cut}}$ and $\Delta_{	ext{RGB}} > 	heta_{	ext{RGB}}$), the transition is cataloged as a SCENE_CUT rather than an AI anomaly.

### 2.3 Taxonomical Separation
A critical error in early deepfake systems was grouping all synthetic media under one label. Secura AI 2.0 establishes an authoritative 5-class target taxonomy:
1. REAL_CAPTURE: Unmanipulated physical camera capture.
2. AI_GENERATED_VIDEO: Full-scene generative synthesis (T2V, I2V, Sora, Runway, Pika, SVD).
3. FACE_MANIPULATED_VIDEO: Authentic background with AI facial replacement or reenactment (DFDC).
4. OTHER_MANIPULATED_VIDEO: Spatial splicing, object insertion, or post-production alterations.
5. UNKNOWN_OR_OUT_OF_DISTRIBUTION: Low resolution, extreme compression, or contradictory evidence triggering explicit INCONCLUSIVE abstention.
