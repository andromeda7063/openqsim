"""Pure Qt-free 3D to 2D projection for Bloch sphere visualization."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BlochProjection:
    """Fixed projection from 3D unit sphere coordinates to 2D pixel coordinates."""

    center_x: float
    center_y: float
    radius: float

    def project(self, x: float, y: float, z: float) -> tuple[float, float]:
        raise NotImplementedError
