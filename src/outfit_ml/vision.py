from __future__ import annotations

import base64
import json
import os
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from .schemas import FaceMatch


class VisionUnavailableError(RuntimeError):
    pass


class VisionError(RuntimeError):
    pass


def _get_face_recognition_module():
    try:
        import face_recognition as fr  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise VisionUnavailableError(
            "Le package 'face-recognition' n'est pas installe. "
            "Installe-le pour activer l'identification camera."
        ) from exc
    return fr


def decode_image_base64(image_base64: str) -> np.ndarray:
    payload = image_base64
    if "," in payload and payload.lower().startswith("data:image"):
        payload = payload.split(",", 1)[1]

    try:
        raw = base64.b64decode(payload)
    except Exception as exc:  # noqa: BLE001
        raise VisionError("Image base64 invalide") from exc

    try:
        image = Image.open(BytesIO(raw)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise VisionError("Impossible de lire l'image") from exc

    return np.array(image)


def extract_face_embedding(image_base64: str) -> list[float]:
    fr = _get_face_recognition_module()
    image = decode_image_base64(image_base64)

    locations = fr.face_locations(image)
    if not locations:
        raise VisionError("Aucun visage detecte")
    if len(locations) > 1:
        raise VisionError("Plusieurs visages detectes: fournir une image avec un seul visage")

    encodings = fr.face_encodings(image, known_face_locations=locations)
    if not encodings:
        raise VisionError("Impossible de calculer l'empreinte faciale")

    return [float(value) for value in encodings[0]]


class FaceRegistry:
    def __init__(self, registry_path: Path | None = None) -> None:
        raw = os.getenv("FACE_REGISTRY_PATH", "data/vision/face_registry.json")
        self.registry_path = registry_path or Path(raw)

    def _load(self) -> dict[str, list[float]]:
        if not self.registry_path.exists():
            return {}
        try:
            with self.registry_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as exc:  # noqa: BLE001
            raise VisionError("Registry visage invalide") from exc

        if not isinstance(data, dict):
            raise VisionError("Registry visage invalide")

        cleaned: dict[str, list[float]] = {}
        for user_id, vector in data.items():
            if isinstance(user_id, str) and isinstance(vector, list):
                cleaned[user_id] = [float(v) for v in vector]
        return cleaned

    def _save(self, registry: dict[str, list[float]]) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.registry_path.open("w", encoding="utf-8") as file:
            json.dump(registry, file)

    def enroll(self, user_id: str, image_base64: str) -> None:
        embedding = extract_face_embedding(image_base64)
        registry = self._load()
        registry[user_id] = embedding
        self._save(registry)

    def identify(
        self,
        image_base64: str,
        threshold: float = 0.45,
        max_results: int = 1,
    ) -> list[FaceMatch]:
        probe = np.array(extract_face_embedding(image_base64), dtype=np.float64)
        registry = self._load()

        if not registry:
            return []

        candidates: list[FaceMatch] = []
        for user_id, vector in registry.items():
            known = np.array(vector, dtype=np.float64)
            distance = float(np.linalg.norm(probe - known))
            if distance <= threshold:
                confidence = max(0.0, min(1.0, 1.0 - (distance / threshold)))
                candidates.append(
                    FaceMatch(
                        user_id=user_id,
                        distance=round(distance, 6),
                        confidence=round(confidence, 6),
                    )
                )

        return sorted(candidates, key=lambda item: item.distance)[:max_results]
