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
        raise NotImplementedError

    def cell_center(self, q: int, c: int) -> tuple[int, int]:
        raise NotImplementedError

    def point_to_cell(
        self, x: int, y: int, num_qubits: int = 10, num_columns: int = 50
    ) -> tuple[int, int] | None:
        raise NotImplementedError

    def rect_to_cells(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        num_qubits: int = 10,
        num_columns: int = 50,
    ) -> list[tuple[int, int]]:
        raise NotImplementedError

    def content_size(self, num_qubits: int, num_columns: int = 50) -> tuple[int, int]:
        raise NotImplementedError
