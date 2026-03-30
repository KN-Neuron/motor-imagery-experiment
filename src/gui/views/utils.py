import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from src.sample_manager.experiment_step_type import ExperimentStepType


_PIXMAP_CACHE: dict[ExperimentStepType, QPixmap] | None = None


def get_pixmap_cache(step_display: dict) -> dict[ExperimentStepType, QPixmap]:
    """Return a lazily-initialized cache of pre-scaled QPixmaps keyed by step type.

    Loading and scaling happens once on first call (after QApplication exists).
    Subsequent calls return the same dict without touching the filesystem.
    """
    global _PIXMAP_CACHE
    if _PIXMAP_CACHE is None:
        _PIXMAP_CACHE = {}
        for step_type, (_, _, img_path) in step_display.items():
            if img_path and os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                _PIXMAP_CACHE[step_type] = pixmap.scaled(
                    300, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
    return _PIXMAP_CACHE
