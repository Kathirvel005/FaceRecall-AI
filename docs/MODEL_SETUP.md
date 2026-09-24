# Deep Learning Models Setup & Specifications

The system utilizes specialized ONNX models for detection and recognition:

## 1. Face Detector: SCRFD (Sample and Computation Redistribution for Efficient Face Detection)

- **Model File:** `models/det_10g.onnx` (High Accuracy) or `models/det_500m.onnx` (High Speed)
- **Input Dimensions:** `[1, 3, 640, 640]` float32 (normalized with `(x - 127.5) / 128.0`)
- **Outputs:**
  - Anchor scores across strides 8, 16, 32
  - Bounding box offsets `[dx1, dy1, dx2, dy2]`
  - 5-point facial keypoints `[x, y]` for left eye, right eye, nose, left mouth, right mouth
- **Features:** Outstanding performance on small, tilted, and distance-varying faces in crowded classrooms.

---

## 2. Feature Recognizer: ArcFace ResNet50

- **Model File:** `models/w600k_r50.onnx` (or MobileFaceNet `models/w600k_mbf.onnx`)
- **Input Dimensions:** `[1, 3, 112, 112]` float32 (RGB normalized with `(x - 127.5) / 127.5`)
- **Output:** `[1, 512]` raw feature embeddings
- **Normalization:** L2-normalized vector $\hat{\mathbf{v}} = \frac{\mathbf{v}}{||\mathbf{v}||_2}$
- **Distance Metric:** Cosine similarity ($s = \hat{\mathbf{v}}_1 \cdot \hat{\mathbf{v}}_2 \in [-1.0, 1.0]$)

---

## 3. Switching Models

To switch models, edit `.env`:
```ini
# Ultra-fast mode for high FPS on CPU
DETECTION_MODEL_PATH=models/det_500m.onnx
RECOGNITION_MODEL_PATH=models/w600k_mbf.onnx

# Maximum accuracy mode
DETECTION_MODEL_PATH=models/det_10g.onnx
RECOGNITION_MODEL_PATH=models/w600k_r50.onnx
```
Both models are already provided in the `models/` directory!
