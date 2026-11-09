from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from project_china.frames import DepthFrame

MIN_TARGET_DEPTH = 750
MAX_TARGET_DEPTH = 1000


@dataclass(frozen=True)
class DepthSelection:
    mask: NDArray[np.uint8]
    contours: tuple[NDArray[np.int32], ...]


def select_depth_regions(frame: DepthFrame) -> DepthSelection:
    """Return a binary target mask and contours for all foreground regions."""
    depths = np.asarray(frame.depths, dtype=np.float64)
    selected = (depths >= MIN_TARGET_DEPTH) & (depths <= MAX_TARGET_DEPTH)
    mask = selected.astype(np.uint8) * 255
    contours, hierarchy = cv2.findContours(
        mask.copy(),
        cv2.RETR_CCOMP,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if hierarchy is None:
        return DepthSelection(mask, ())

    foreground_contours = tuple(
        contour
        for contour, relation in zip(contours, hierarchy[0], strict=True)
        if relation[3] == -1
    )
    return DepthSelection(mask, foreground_contours)
