"""Pure Qt-free 3D to 2D projection for Bloch sphere visualization."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BlochProjection:
    """Fixed projection from 3D unit sphere coordinates to 2D pixel coordinates."""

    center_x: float
    center_y: float
    radius: float

    def project(self, x: float, y: float, z: float) -> tuple[float, float]:
        """Project (x, y, z) unit coordinates to (px, py) 2D pixel space."""
        # Fixed oblique/cabinet projection:
        # +Z points straight up (-Y in screen coordinates)
        # +X points down-left
        # +Y points down-right / right
        px = self.center_x + self.radius * (-0.6 * x + 0.8 * y)
        py = self.center_y + self.radius * (0.35 * x + 0.2 * y - 1.0 * z)
        return (px, py)
