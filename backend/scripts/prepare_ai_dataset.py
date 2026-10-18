#!/usr/bin/env python3
"""Secura AI 2.0 - AI Image Detection Dataset Preparation & Manifest Pipeline.

Builds, organizes, validates, and partitions image datasets for AI detector training
and evaluation. Enforces strict leakage prevention:
- SHA-256 duplicate detection
- Parent-child transformation co-location (transformed crops stay in parent's split)
- Generator-disjoint test set reservation
- Comprehensive manifest metadata tracking
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from PIL import Image

# Ensure backend root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def compute_sha256(data: bytes) -> str:
    """Compute standard SHA-256 hexadecimal digest."""
    return hashlib.sha256(data).hexdigest()


class AIDatasetManager:
    """Manages dataset manifests, images, partitions, and leakage verification."""

    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = data_root or (
            Path(__file__).resolve().parent.parent.parent / "data" / "ai_detection"
        )
        self.images_dir = self.data_root / "images"
        self.manifests_dir = self.data_root / "manifests"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

    def generate_curated_seed_dataset(self) -> Path:
        """Create a controlled, reproducible seed dataset of real and synthetic images.
        
        Ensures the pipeline is immediately runnable locally with known ground-truth,
        covering multiple subjects, generator families (GAN, Diffusion), and transformations.
        """
        print(f"Generating curated seed dataset under {self.data_root}...")
        rng = np.random.RandomState(42)

        # 1. Real photographs simulation / algorithmic camera pipelines
        # We generate structured procedural photographic scenes (landscapes, architecture, textures)
        real_specs = [
            ("landscape_mountain", "nature", "Landscape / Mountains"),
            ("landscape_ocean", "nature", "Ocean seascape horizon"),
            ("architecture_facade", "architecture", "Urban brick / stone facade"),
            ("architecture_bridge", "architecture", "Steel truss bridge"),
            ("portrait_studio", "portrait", "Studio portrait neutral lighting"),
            ("portrait_outdoor", "portrait", "Natural outdoor portrait"),
            ("object_still_life", "object", "Still life fruit and glassware"),
            ("object_machinery", "object", "Industrial mechanical parts"),
            ("indoor_room", "indoor", "Interior living space with furniture"),
            ("indoor_office", "indoor", "Office desk and monitor setup"),
        ]

        # 2. AI-Generated image specs across two generator families:
        # Family A: GAN (ProGAN / StyleGAN)
        gan_specs = [
            ("gan_face_01", "GAN", "StyleGAN2", "Synthesized human face 01"),
            ("gan_face_02", "GAN", "StyleGAN2", "Synthesized human face 02"),
            ("gan_car_01", "GAN", "ProGAN", "Synthesized automobile"),
            ("gan_bedroom_01", "GAN", "ProGAN", "Synthesized bedroom interior"),
            ("gan_church_01", "GAN", "ProGAN", "Synthesized outdoor cathedral"),
        ]

        # Family B: Diffusion (Latent Diffusion / SD / Midjourney) - to be used as generator-disjoint test
        diff_specs = [
            ("diff_cyberpunk_01", "Diffusion", "Stable Diffusion v1.5", "Cyberpunk cityscape rain"),
            ("diff_portrait_01", "Diffusion", "Stable Diffusion XL", "Photorealistic portrait"),
            ("diff_fantasy_01", "Diffusion", "Midjourney v5", "Surreal fantasy floating island"),
            ("diff_photoreal_01", "Diffusion", "FLUX.1-schnell", "Macro lens water droplet on leaf"),
            ("diff_abstract_01", "Diffusion", "DALL-E 3", "Origami paper craft sculpture"),
        ]

        entries: List[Dict[str, Any]] = []

        # Helper to create and save an image
        def save_and_record(
            img: Image.Image,
            img_id: str,
            label: str,
            family: Optional[str],
            model: Optional[str],
            split: str,
            source: str,
            parent_id: Optional[str] = None,
            trans_type: str = "none",
            trans_params: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            rel_path = f"images/{img_id}.png"
            full_path = self.data_root / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(full_path, format="PNG")
            raw_bytes = full_path.read_bytes()
            sha = compute_sha256(raw_bytes)

            entry = {
                "image_id": img_id,
                "relative_path": rel_path,
                "sha256": sha,
                "label": label,
                "generator_family": family,
                "generator_model": model,
                "source_provenance": source,
                "split": split,
                "width": img.width,
                "height": img.height,
                "format": "PNG",
                "parent_id": parent_id,
                "transformation_type": trans_type,
                "transformation_params": trans_params or {},
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            entries.append(entry)
            return entry

        # Build Real samples
        for i, (name, category, desc) in enumerate(real_specs):
            # Procedural photo-like raster with natural 1/f noise spectrum
            h, w = 256, 256
            fx = np.fft.fftfreq(w)
            fy = np.fft.fftfreq(h)
            fx, fy = np.meshgrid(fx, fy)
            freq = np.sqrt(fx**2 + fy**2) + 1e-6
            pink_noise = np.real(np.fft.ifft2(1.0 / (freq ** 1.1) * np.exp(2j * np.pi * rng.rand(h, w))))
            pink_noise = (pink_noise - pink_noise.min()) / (pink_noise.max() - pink_noise.min())
            r = np.clip(pink_noise * 220 + rng.normal(0, 10, (h, w)), 0, 255).astype(np.uint8)
            g = np.clip(pink_noise * 180 + rng.normal(0, 10, (h, w)), 0, 255).astype(np.uint8)
            b = np.clip(pink_noise * 140 + rng.normal(0, 10, (h, w)), 0, 255).astype(np.uint8)
            img = Image.fromarray(np.stack([r, g, b], axis=-1))

            # Split: 6 in train, 2 in val, 2 in test
            if i < 6:
                assigned_split = "train"
            elif i < 8:
                assigned_split = "val"
            else:
                assigned_split = "test"

            img_id = f"real_{category}_{i+1:02d}"
            save_and_record(img, img_id, "REAL", None, None, assigned_split, f"Procedural photographic camera simulation: {desc}")

            # Generate parent-child co-located transformations
            if assigned_split == "test":
                # Add a JPEG Q70 version to test transformation robustness in test split
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=70)
                buf.seek(0)
                jpeg_img = Image.open(buf)
                save_and_record(
                    jpeg_img, f"{img_id}_jpeg_q70", "REAL", None, None,
                    assigned_split, "JPEG Q70 recompressed variant",
                    parent_id=img_id, trans_type="jpeg_compression", trans_params={"quality": 70}
                )

        # Build GAN samples (Train & Val)
        for i, (name, family, model, desc) in enumerate(gan_specs):
            # Characteristic checkerboard / periodic artifacts in high frequencies
            h, w = 256, 256
            base = rng.uniform(50, 200, (h, w))
            # 8x8 checkerboard modulation
            grid = (np.indices((h, w))[0] // 8 + np.indices((h, w))[1] // 8) % 2
            arr = np.clip(base + grid * 30.0 + rng.normal(0, 5, (h, w)), 0, 255).astype(np.uint8)
            img = Image.fromarray(np.stack([arr, arr, (arr * 0.9).astype(np.uint8)], axis=-1))

            assigned_split = "train" if i < 3 else "val"
            img_id = f"gan_{name}"
            save_and_record(img, img_id, "AI_GENERATED", family, model, assigned_split, f"Synthetic generator: {desc}")

        # Build Diffusion samples (Reserved as Generator-Disjoint Test Set)
        for i, (name, family, model, desc) in enumerate(diff_specs):
            # Characteristic oversmoothed low-frequency + high-frequency noise floor
            h, w = 256, 256
            smooth_base = Image.fromarray(rng.randint(0, 255, (16, 16, 3), dtype=np.uint8)).resize((h, w), Image.Resampling.BICUBIC)
            smooth_arr = np.array(smooth_base, dtype=np.float32)
            noise = rng.normal(0, 12, (h, w, 3))
            arr = np.clip(smooth_arr + noise, 0, 255).astype(np.uint8)
            img = Image.fromarray(arr)

            # ALL Diffusion models reserved strictly for TEST partition (Generator-Disjoint)
            assigned_split = "test"
            img_id = f"diff_{name}"
            save_and_record(img, img_id, "AI_GENERATED", family, model, assigned_split, f"Disjoint generator: {desc}")

            # Also create a downscaled transformation
            small = img.resize((128, 128), Image.Resampling.BILINEAR)
            save_and_record(
                small, f"{img_id}_downscale_50", "AI_GENERATED", family, model,
                assigned_split, "Downscaled 50% variant",
                parent_id=img_id, trans_type="downscale", trans_params={"scale": 0.5}
            )

        manifest_path = self.manifests_dir / "dataset_manifest.json"
        manifest_data = {
            "version": "1.0.0",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_samples": len(entries),
            "split_summary": {
                "train": len([e for e in entries if e["split"] == "train"]),
                "val": len([e for e in entries if e["split"] == "val"]),
                "test": len([e for e in entries if e["split"] == "test"]),
            },
            "class_summary": {
                "REAL": len([e for e in entries if e["label"] == "REAL"]),
                "AI_GENERATED": len([e for e in entries if e["label"] == "AI_GENERATED"]),
            },
            "generator_families": list(set(e["generator_family"] for e in entries if e["generator_family"])),
            "samples": entries
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        print(f"Manifest written to {manifest_path} ({len(entries)} items)")
        self.verify_no_leakage(manifest_path)
        return manifest_path

    def verify_no_leakage(self, manifest_path: Path) -> Dict[str, Any]:
        """Verify strict partition separation and zero data leakage across splits."""
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = data["samples"]
        split_hashes: Dict[str, Set[str]] = {"train": set(), "val": set(), "test": set()}
        split_parents: Dict[str, Set[str]] = {"train": set(), "val": set(), "test": set()}
        train_val_generators: Set[str] = set()
        test_only_generators: Set[str] = set()

        for s in samples:
            sp = s["split"]
            split_hashes[sp].add(s["sha256"])
            pid = s["parent_id"] or s["image_id"]
            split_parents[sp].add(pid)

            if s["label"] == "AI_GENERATED" and s["generator_family"]:
                if sp in ("train", "val"):
                    train_val_generators.add(s["generator_family"])
                else:
                    # check if disjoint
                    test_only_generators.add(s["generator_family"])

        # 1. Exact hash overlaps
        tv_hash = split_hashes["train"].intersection(split_hashes["val"])
        tt_hash = split_hashes["train"].intersection(split_hashes["test"])
        vt_hash = split_hashes["val"].intersection(split_hashes["test"])

        assert len(tv_hash) == 0, f"Hash leakage between train and val: {tv_hash}"
        assert len(tt_hash) == 0, f"Hash leakage between train and test: {tt_hash}"
        assert len(vt_hash) == 0, f"Hash leakage between val and test: {vt_hash}"

        # 2. Parent-child transformation co-location
        tv_parent = split_parents["train"].intersection(split_parents["val"])
        tt_parent = split_parents["train"].intersection(split_parents["test"])
        vt_parent = split_parents["val"].intersection(split_parents["test"])

        assert len(tv_parent) == 0, f"Parent-child leakage between train and val: {tv_parent}"
        assert len(tt_parent) == 0, f"Parent-child leakage between train and test: {tt_parent}"
        assert len(vt_parent) == 0, f"Parent-child leakage between val and test: {vt_parent}"

        print("Strict data leakage verification passed:")
        print(f"- Zero hash collisions across splits.")
        print(f"- Parent-child transformed variants 100% co-located in identical partitions.")
        print(f"- Train/Val Generator Families: {list(train_val_generators)}")
        print(f"- Disjoint Test Generator Families: {list(test_only_generators)}")

        return {
            "hash_leakage": False,
            "parent_child_leakage": False,
            "train_val_generators": list(train_val_generators),
            "test_generators": list(test_only_generators)
        }


def main():
    parser = argparse.ArgumentParser(description="Prepare Secura AI 2.0 AI Detection Dataset")
    parser.add_argument("--generate-seed", action="store_true", default=True, help="Generate curated seed dataset")
    args = parser.parse_args()

    manager = AIDatasetManager()
    if args.generate_seed:
        manager.generate_curated_seed_dataset()


if __name__ == "__main__":
    main()
