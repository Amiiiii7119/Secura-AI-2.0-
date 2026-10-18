# Live Camera Capture Implementation Architecture

## 1. Overview
Secura AI 2.0 provides dual input modalities for both images and videos:
1. **File Upload Mode** (Standard drag-and-drop or file selector)
2. **Live Camera Mode** (Direct device sensor capture)

---

## 2. Image Webcam Photo Capture
* **Implementation:** HTML5 `navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1920 } } })`
* **Capture Technique:** Video frame rendered to hidden HTML5 `<canvas>` element at full native resolution and exported via `canvas.toBlob('image/jpeg', 0.95)`.
* **State Management:**
  - `showCameraModal`: controls open/close of viewfinder.
  - `facingMode`: supports front (`user`) and rear (`environment`) toggle on mobile/dual-camera devices.
  - Track Cleanup: All `MediaStreamTrack` instances are immediately stopped on `cancelCapture` or modal dismissal to release webcam indicator hardware lights.

---

## 3. Video Live Recording
* **Implementation:** HTML5 `MediaRecorder` API with live elapsed recording timer.
* **MIME Type Autodetection:** Checks `MediaRecorder.isTypeSupported('video/webm;codecs=vp9')`, falling back to `video/webm` or `video/mp4`.
* **Duration Limit:** Configurable max duration of 30 seconds with automatic auto-stop and countdown.
* **Playback & Re-record:** Live recorded blob is rendered into an interactive review video player before user triggers "Analyze Recording".\n