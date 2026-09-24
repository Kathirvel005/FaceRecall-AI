from typing import List, Tuple, Optional, Dict, Any
import os
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort

from backend.app.config import settings
from backend.app.core.logging import logger

class DetectedFace:
    def __init__(self, bbox: List[int], confidence: float, landmarks: np.ndarray):
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = float(confidence)
        self.landmarks = landmarks  # shape (5, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox,
            "confidence": round(self.confidence, 4),
            "landmarks": self.landmarks.round(2).tolist()
        }


class SCRFDDetector:
    """
    High-Performance SCRFD Multi-Face Detector using ONNX Runtime.
    Detects small, medium, and large faces with 5-point facial landmarks.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: Optional[float] = None,
        nms_threshold: Optional[float] = None,
        input_size: Tuple[int, int] = (640, 640),
        device_preference: Optional[str] = None
    ):
        self.model_path = model_path or settings.DETECTION_MODEL_PATH
        self.conf_threshold = conf_threshold if conf_threshold is not None else settings.DETECTION_CONF_THRESHOLD
        self.nms_threshold = nms_threshold if nms_threshold is not None else settings.DETECTION_NMS_THRESHOLD
        self.input_size = input_size
        self.device_preference = device_preference or settings.DEVICE_PREFERENCE

        self.session: Optional[ort.InferenceSession] = None
        self.fmc = 3
        self._feat_stride_fpn = [8, 16, 32]
        self._num_anchors = 2
        self._use_kps = True
        self._init_session()

    def _init_session(self):
        resolved_path = Path(self.model_path)
        if not resolved_path.is_absolute():
            resolved_path = settings.BASE_DIR / resolved_path

        if not resolved_path.exists():
            raise FileNotFoundError(f"SCRFD model not found at: {resolved_path}")

        available_providers = ort.get_available_providers()
        providers = []
        if self.device_preference in ("auto", "cuda") and "CUDAExecutionProvider" in available_providers:
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")

        # Session options for optimization
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        logger.info(f"Loading SCRFD Detector from {resolved_path} with providers: {providers}")
        self.session = ort.InferenceSession(str(resolved_path), sess_options, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        output_names = [o.name for o in self.session.get_outputs()]
        self.output_names = output_names

        active_provider = self.session.get_providers()[0]
        logger.info(f"SCRFD Detector initialized successfully. Active Provider: {active_provider}")

    def _preprocess(self, img: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Resize image to input_size while maintaining aspect ratio or standard resize,
        and normalize to SCRFD format: (img - 127.5) / 128.0.
        """
        im_ratio = float(img.shape[0]) / img.shape[1]
        model_ratio = float(self.input_size[1]) / self.input_size[0]
        if im_ratio > model_ratio:
            new_height = self.input_size[1]
            new_width = int(new_height / im_ratio)
        else:
            new_width = self.input_size[0]
            new_height = int(new_width * im_ratio)

        det_scale = float(new_height) / img.shape[0]
        resized_img = cv2.resize(img, (new_width, new_height))
        det_img = np.zeros((self.input_size[1], self.input_size[0], 3), dtype=np.uint8)
        det_img[:new_height, :new_width, :] = resized_img

        # Normalization
        input_tensor = (det_img.astype(np.float32) - 127.5) / 128.0
        input_tensor = input_tensor.transpose((2, 0, 1))
        input_tensor = np.expand_dims(input_tensor, axis=0)
        return input_tensor, det_scale

    def detect(self, image: np.ndarray, max_num: int = 0) -> List[DetectedFace]:
        """
        Detect all faces in the given BGR image.
        Returns a list of DetectedFace objects.
        """
        if image is None or image.size == 0 or self.session is None:
            return []

        orig_h, orig_w = image.shape[:2]
        input_tensor, det_scale = self._preprocess(image)

        net_outs = self.session.run(self.output_names, {self.input_name: input_tensor})

        input_height = self.input_size[1]
        input_width = self.input_size[0]

        scores_list = []
        bboxes_list = []
        kpss_list = []

        # SCRFD outputs: scores (fmc), bboxes (fmc), kpss (fmc)
        for idx, stride in enumerate(self._feat_stride_fpn):
            score = net_outs[idx]
            bbox_pred = net_outs[idx + self.fmc] * stride
            kps_pred = net_outs[idx + self.fmc * 2] * stride

            height = input_height // stride
            width = input_width // stride

            # Generate grid anchors
            anchor_centers = np.stack(np.mgrid[:height, :width][::-1], axis=-1).astype(np.float32)
            anchor_centers = (anchor_centers * stride).reshape((-1, 2))
            if self._num_anchors > 1:
                anchor_centers = np.stack([anchor_centers] * self._num_anchors, axis=1).reshape((-1, 2))

            pos_inds = np.where(score >= self.conf_threshold)[0]
            if len(pos_inds) == 0:
                continue

            score = score[pos_inds]
            bbox_pred = bbox_pred[pos_inds]
            kps_pred = kps_pred[pos_inds]
            anchor_centers = anchor_centers[pos_inds]

            # Decode bounding boxes: [x1, y1, x2, y2]
            x1 = anchor_centers[:, 0] - bbox_pred[:, 0]
            y1 = anchor_centers[:, 1] - bbox_pred[:, 1]
            x2 = anchor_centers[:, 0] + bbox_pred[:, 2]
            y2 = anchor_centers[:, 1] + bbox_pred[:, 3]

            bboxes = np.stack([x1, y1, x2, y2], axis=-1) / det_scale

            # Decode 5 landmarks: shape (N, 5, 2)
            kpss = np.zeros((len(pos_inds), 5, 2), dtype=np.float32)
            for k in range(5):
                kpss[:, k, 0] = (anchor_centers[:, 0] + kps_pred[:, k * 2]) / det_scale
                kpss[:, k, 1] = (anchor_centers[:, 1] + kps_pred[:, k * 2 + 1]) / det_scale

            scores_list.append(score)
            bboxes_list.append(bboxes)
            kpss_list.append(kpss)

        if not scores_list:
            return []

        scores = np.vstack(scores_list).ravel()
        bboxes = np.vstack(bboxes_list)
        kpss = np.vstack(kpss_list)

        # OpenCV NMS
        # Convert bboxes [x1, y1, x2, y2] to [x, y, w, h]
        cv_boxes = []
        for box in bboxes:
            bx1, by1, bx2, by2 = box
            cv_boxes.append([int(bx1), int(by1), int(bx2 - bx1), int(by2 - by1)])

        indices = cv2.dnn.NMSBoxes(
            bboxes=cv_boxes,
            scores=scores.tolist(),
            score_threshold=float(self.conf_threshold),
            nms_threshold=float(self.nms_threshold)
        )

        detected_faces = []
        if len(indices) > 0:
            indices = np.array(indices).flatten()
            if max_num > 0 and len(indices) > max_num:
                # Pick top max_num by score
                order = np.argsort(-scores[indices])[:max_num]
                indices = indices[order]

            for i in indices:
                box = bboxes[i]
                x1 = max(0, int(box[0]))
                y1 = max(0, int(box[1]))
                x2 = min(orig_w, int(box[2]))
                y2 = min(orig_h, int(box[3]))

                if x2 <= x1 or y2 <= y1:
                    continue

                face = DetectedFace(
                    bbox=[x1, y1, x2, y2],
                    confidence=float(scores[i]),
                    landmarks=kpss[i]
                )
                detected_faces.append(face)

        return detected_faces
