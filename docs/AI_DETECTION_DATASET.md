# AI Detection Labeled Dataset & Manifest Documentation
**Secura AI 2.0 Greenfield Implementation**  
**Dataset Root:** `D:\SecuraAI2\data\ai_detection`  
**Manifest Path:** `D:\SecuraAI2\data\ai_detection\manifests\dataset_manifest.json`

---

## 1. Overview & Dataset Governance

The Secura AI 2.0 AI Detection Dataset is organized around an explicit, machine-readable JSON manifest schema. Rather than embedding filesystem paths or labels in training code, all dataset entries are tracked with cryptographic hashes, provenance metadata, generator architectures, and strict partition assignments.

---

## 2. Manifest Schema Specification

Each entry in `dataset_manifest.json` conforms to the following typed schema:

| Field | Type | Description |
| :--- | :--- | :--- |
| `image_id` | `string` | Unique identifier (e.g. `real_nature_01`, `diff_photoreal_01`). |
| `relative_path` | `string` | Path relative to `data/ai_detection/` (e.g. `images/real_nature_01.png`). |
| `sha256` | `string` | 64-character SHA-256 cryptographic digest of the exact image bytes. |
| `label` | `string` | Binary ground-truth label: `REAL` or `AI_GENERATED`. |
| `generator_family`| `string \| null` | Broad generator taxonomy: `GAN`, `Diffusion`, `Autoregressive`, or `null` for real images. |
| `generator_model` | `string \| null` | Specific model: `StyleGAN2`, `ProGAN`, `Stable Diffusion v1.5`, `FLUX.1-schnell`, etc. |
| `source_provenance` | `string` | Provenance description detailing camera simulation or generative prompt. |
| `split` | `string` | Assigned partition: `train`, `val`, or `test`. |
| `width` / `height` | `integer` | Native spatial resolution in pixels. |
| `format` | `string` | Image container format (`PNG`, `JPEG`). |
| `parent_id` | `string \| null` | Identifier of parent image if this entry is a transformed variant. |
| `transformation_type` | `string` | `none`, `jpeg_compression`, `downscale`, `gaussian_blur`, etc. |
| `transformation_params`| `object` | Parameters applied (e.g. `{"quality": 70}`, `{"scale": 0.5}`). |
| `created_at_utc` | `string` | ISO 8601 UTC creation timestamp. |

---

## 3. Strict Data Leakage Prevention Guarantees

The dataset pipeline enforces three non-negotiable partitioning guarantees:

1. **Cryptographic Deduplication:**
   Every image is hashed on ingestion. SHA-256 intersections across partitions are verified to be strictly empty:
   $$	ext{Hashes}(	ext{train}) \cap 	ext{Hashes}(	ext{val}) = \emptyset, \quad 	ext{Hashes}(	ext{train}) \cap 	ext{Hashes}(	ext{test}) = \emptyset, \quad 	ext{Hashes}(	ext{val}) \cap 	ext{Hashes}(	ext{test}) = \emptyset$$

2. **Parent-Child Transformation Co-Location:**
   Any cropped, downscaled, or recompressed variant of an image is guaranteed to reside in the **exact same partition** as its source image (`parent_id`). This eliminates the catastrophic leakage where an original image is in `train` while its JPEG-recompressed version is in `test`.

3. **Generator-Disjoint Test Reservation:**
   To evaluate true out-of-distribution generalization rather than memorized generator fingerprints:
   - **Train & Validation Partitions:** Contain only GAN architectures (`StyleGAN2`, `ProGAN`).
   - **Test Partition:** Reserved exclusively for unseen Diffusion architectures (`Stable Diffusion v1.5`, `SDXL`, `Midjourney v5`, `FLUX.1`, `DALL-E 3`) plus held-out real camera photographs and controlled transformations.

---

## 4. Current Dataset Summary

| Partition | Total Images | Real Images | AI Images | Primary Generator Family |
| :--- | :--- | :--- | :--- | :--- |
| **Train** | 9 | 6 | 3 | GAN (StyleGAN2, ProGAN) |
| **Validation** | 4 | 2 | 2 | GAN (StyleGAN2, ProGAN) |
| **Held-Out Test** | 14 | 4 (incl. JPEG Q70) | 10 (incl. Downscaled) | **Diffusion (SD, SDXL, Midjourney, FLUX, DALL-E 3)** |
| **Total** | **27** | **12** | **15** | Cross-Family Balanced |

---

## 5. Verification Commands

To re-verify the dataset and confirm zero leakage at any time:
```powershell
& D:\SecuraAI2\.venv\Scripts\python.exe D:\SecuraAI2\backend\scripts\prepare_ai_dataset.py
```
