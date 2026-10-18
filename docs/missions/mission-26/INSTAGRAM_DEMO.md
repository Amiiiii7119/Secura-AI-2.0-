# Instagram Simulation Demo Guide

## 1. Features
- **Visual Interface:** Sleek dark-mode feed recreating the Instagram mobile and web experience.
- **Live Camera Snapshot:** High-fidelity webcam capture for direct content publishing.
- **Atomic Likes:** Multi-user idempotent like toggle with live counter updates.
- **Threaded Comments:** Comment input with inline RAG scanning before submission.
- **Pre-Publication Interception:** Synthetic images undergo synchronous inference prior to database persistence.

## 2. Walkthrough Steps
1. Navigate to `http://localhost:5173/?mode=social`.
2. Select the **Instagram** client tab from the top navigation bar.
3. Observe Arjun's feed showing verified authentic photography.
4. Click **Create Post**, select a synthetic test image, and click **Publish**.
5. Observe the red moderation alert modal displaying `403 Forbidden` with the `UniversalFakeDetect` model confidence score and policy explanation.
6. The feed remains untainted by synthetic media.