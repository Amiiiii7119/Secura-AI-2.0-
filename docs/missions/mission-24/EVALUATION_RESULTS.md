# Empirical Evaluation Results & Metrics

## 1. Test Suite Pass Rates
* **Total Automated Tests Executed:** 137 tests
* **Pass Rate:** **100% (137 passed, 0 failed in 42.96s)**
* **Regression Test:** UHD Known AI Video (`8328099-uhd_2160_3840_25fps.mp4`) -> **PASSED** (Verdict: `AI GENERATED`, Score: 0.6303).
* **Device Metadata Test Suite:** 9/9 passed (`PRESENT`, `MANUFACTURER_ONLY`, `SOFTWARE_ONLY`, `ABSENT`, `MALFORMED`).

---

## 2. Image Compression Robustness Evaluation

| Compression | Raw Uncalibrated Margin | Predicted Class | Decision Consistency |
| :--- | :--- | :--- | :--- |
| **Uncompressed (Lossless)** | 0.3446 | LIKELY_REAL | Consistent |
| **JPEG Quality 95** | 0.3446 | LIKELY_REAL | Consistent |
| **JPEG Quality 75** | 0.3446 | LIKELY_REAL | Consistent |
| **JPEG Quality 50** | 0.3435 | LIKELY_REAL | Consistent (Delta < 0.0012) |
| **JPEG Quality 30** | 0.3446 | LIKELY_REAL | Consistent |\n