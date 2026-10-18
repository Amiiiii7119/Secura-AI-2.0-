# Device Metadata Extraction & Identification Repair

## 1. The Defect in Prior Versions
In previous iterations, the user interface invariably reported capture devices as "Unidentified". The root causes were twofold:
1. Transformed image handles in memory had their EXIF directories stripped during PIL RGB conversions.
2. When EXIF tags were absent, the inspector returned `camera_metadata = None`, leaving the frontend without descriptive status.

---

## 2. The 5 Truthful Device States
Secura now enforces 5 truthful, legally defensible device identification states:

1. **`PRESENT`:**
   - Display: Full camera make and model (e.g. `Sony ILCE-7RM4` or `Apple iPhone 15 Pro`).
   - Criteria: Both Make and Model tags present and non-empty. Duplicated manufacturer prefixes are cleanly deduped.
2. **`MANUFACTURER_ONLY`:**
   - Display: `{Make} (Model unavailable)` (e.g. `Canon (Model unavailable)`).
   - Criteria: Make tag present, but Model tag missing or stripped.
3. **`SOFTWARE_ONLY`:**
   - Display: `Software: {Software}` (e.g. `Software: Adobe Photoshop 2024` or `Software: Midjourney v6.0`).
   - Criteria: No physical camera tags found, but software/application tags detected in EXIF or PNG text chunks.
4. **`ABSENT`:**
   - Display: `Device information not present in file`.
   - Criteria: Standard web, messaging, or stripped media with zero metadata tags.
5. **`MALFORMED`:**
   - Display: `Device metadata could not be read`.
   - Criteria: File contains corrupt or invalid EXIF header bytes.\n