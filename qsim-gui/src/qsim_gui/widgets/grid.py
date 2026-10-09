"""Pure Qt-free grid geometry calculations for circuit canvas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Margins:
    left: int = 60
    top: int = 40
    right: int = 20
    bottom: int = 20


class GridGeometry:
    """Pure geometry mapping discrete (qubit, column) cells to pixel coordinates."""

    def __init__(
        self,
        cell_width: int = 48,
        cell_height: int = 48,
        margins: Margins | None = None,
    ) -> None:
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.margins = margins if margins is not None else Margins()

    def cell_to_rect(self, q: int, c: int) -> tuple[int, int, int, int]:
        """Return (x, y, width, height) of the cell (qubit q, column c)."""
        x = self.margins.left + c * self.cell_width
        y = self.margins.top + q * self.cell_height
        return (x, y, self.cell_width, self.cell_height)

    def cell_center(self, q: int, c: int) -> tuple[int, int]:
        """Return (cx, cy) pixel coordinates of the center of cell (q, c)."""
        cx = self.margins.left + c * self.cell_width + self.cell_width // 2
        cy = self.margins.top + q * self.cell_height + self.cell_height // 2
        return (cx, cy)

    def point_to_cell(
        self, x: int, y: int, num_qubits: int = 10, num_columns: int = 50
    ) -> tuple[int, int] | None:
        """Convert pixel (x, y) to (qubit, column) or None if outside grid bounds."""
        x_min = self.margins.left
        x_max = self.margins.left + num_columns * self.cell_width
        y_min = self.margins.top
        y_max = self.margins.top + num_qubits * self.cell_height

        if x < x_min or x >= x_max or y < y_min or y >= y_max:
            return None

        c = (x - x_min) // self.cell_width
        q = (y - y_min) // self.cell_height

        if 0 <= q < num_qubits and 0 <= c < num_columns:
            return (q, c)
        return None

    def rect_to_cells(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        num_qubits: int = 10,
        num_columns: int = 50,
    ) -> list[tuple[int, int]]:
        """Return all (qubit, column) cells overlapping pixel bounding box [x0..x1, y0..y1]."""
        min_x = min(x0, x1)
        max_x = max(x0, x1)
        min_y = min(y0, y1)
        max_y = max(y0, y1)

        grid_left = self.margins.left
        grid_top = self.margins.top
        grid_right = grid_left + num_columns * self.cell_width
        grid_bottom = grid_top + num_qubits * self.cell_height

        if max_x < grid_left or min_x >= grid_right or max_y < grid_top or min_y >= grid_bottom:
            return []

        c_start = max(0, (min_x - grid_left) // self.cell_width)
        c_end = min(num_columns - 1, (max_x - grid_left) // self.cell_width)
        q_start = max(0, (min_y - grid_top) // self.cell_height)
        q_end = min(num_qubits - 1, (max_y - grid_top) // self.cell_height)

        cells: list[tuple[int, int]] = []
        for q in range(q_start, q_end + 1):
            for c in range(c_start, c_end + 1):
                cells.append((q, c))
        return cells

    def content_size(self, num_qubits: int, num_columns: int = 50) -> tuple[int, int]:
        """Total width and height needed to render the circuit grid."""
        width = self.margins.left + num_columns * self.cell_width + self.margins.right
        height = self.margins.top + num_qubits * self.cell_height + self.margins.bottom
        return (width, height)

    def visible_columns(self, viewport_width: int) -> int:
        """Count columns at least partly visible past the left grid margin."""
        grid_width = max(0, viewport_width - self.margins.left)
        return min(50, (grid_width + self.cell_width - 1) // self.cell_width)
