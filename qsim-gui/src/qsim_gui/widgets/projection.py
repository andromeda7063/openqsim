"""Qt-free orthographic projection for the rotatable Bloch view."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BlochProjection:
    """Project Bloch coordinates through a camera orbiting the origin."""

    center_x: float
    center_y: float
    radius: float
    yaw: float = math.radians(130.0)
    elevation: float = math.radians(25.0)

    def view_coordinates(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """Return camera-space right, up, and depth (positive is nearer)."""
        right = math.cos(self.yaw) * x + math.sin(self.yaw) * y
        horizontal_depth = -math.sin(self.yaw) * x + math.cos(self.yaw) * y
        up = math.sin(self.elevation) * horizontal_depth + math.cos(self.elevation) * z
        depth = math.cos(self.elevation) * horizontal_depth - math.sin(self.elevation) * z
        return right, up, depth

    def project(self, x: float, y: float, z: float) -> tuple[float, float]:
        """Project (x, y, z) to screen pixels."""
        right, up, _ = self.view_coordinates(x, y, z)
        return self.center_x + self.radius * right, self.center_y - self.radius * up
