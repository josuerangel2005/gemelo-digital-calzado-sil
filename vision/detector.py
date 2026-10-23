"""Detector de defectos (stub). Sustituir por YOLO/Anomalib manteniendo la interfaz."""
import base64

import cv2
import numpy as np


def decode_png_b64(data: str) -> np.ndarray:
    buf = np.frombuffer(base64.b64decode(data), dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)


def encode_png_b64(image: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("no se pudo codificar la imagen")
    return base64.b64encode(buf.tobytes()).decode("ascii")


class Detector:
    """Heurística: proporción de píxeles oscuros (mancha) sobre el umbral."""

    def __init__(self, dark_level: int = 60, defect_ratio: float = 0.01):
        self.dark_level = dark_level
        self.defect_ratio = defect_ratio

    def predict(self, image: np.ndarray) -> dict:
        ratio = float(np.mean(image < self.dark_level))
        score = min(1.0, ratio / (self.defect_ratio * 4))
        label = "mancha" if ratio >= self.defect_ratio else "ok"
        return {"label": label, "score": score}
