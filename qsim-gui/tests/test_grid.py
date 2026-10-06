"""Tests for pure Qt-free GridGeometry."""

import pytest
from qsim_gui.widgets.grid import GridGeometry, Margins


@pytest.mark.req("NFR-2.7")
def test_grid_round_trip_for_all_cells() -> None:
    margins = Margins(left=60, top=40, right=20, bottom=20)
    geo = GridGeometry(cell_width=50, cell_height=50, margins=margins)

    for q in range(10):
        for c in range(50):
            cx, cy = geo.cell_center(q, c)
            cell = geo.point_to_cell(cx, cy, num_qubits=10, num_columns=50)
            assert cell == (q, c), f"Failed for cell ({q}, {c}) with center ({cx}, {cy})"


@pytest.mark.req("NFR-2.7")
def test_grid_points_outside_return_none() -> None:
    margins = Margins(left=60, top=40, right=20, bottom=20)
    geo = GridGeometry(cell_width=50, cell_height=50, margins=margins)

    num_qubits = 4
    num_columns = 50

    x_min = margins.left
    x_max = margins.left + num_columns * geo.cell_width
    y_min = margins.top
    y_max = margins.top + num_qubits * geo.cell_height

    # Just left
    assert geo.point_to_cell(x_min - 1, y_min + 10, num_qubits=num_qubits) is None
    # Just right
    assert geo.point_to_cell(x_max, y_min + 10, num_qubits=num_qubits) is None
    # Just above
    assert geo.point_to_cell(x_min + 10, y_min - 1, num_qubits=num_qubits) is None
    # Just below
    assert geo.point_to_cell(x_min + 10, y_max, num_qubits=num_qubits) is None
    # Negative
    assert geo.point_to_cell(-10, -10, num_qubits=num_qubits) is None


@pytest.mark.req("NFR-2.7")
def test_grid_content_size_for_1_and_10_qubits() -> None:
    margins = Margins(left=60, top=40, right=20, bottom=20)
    geo = GridGeometry(cell_width=48, cell_height=48, margins=margins)

    # 1 qubit, 50 columns
    w1, h1 = geo.content_size(num_qubits=1, num_columns=50)
    assert w1 == 60 + 50 * 48 + 20
    assert h1 == 40 + 1 * 48 + 20

    # 10 qubits, 50 columns
    w10, h10 = geo.content_size(num_qubits=10, num_columns=50)
    assert w10 == 60 + 50 * 48 + 20
    assert h10 == 40 + 10 * 48 + 20


@pytest.mark.req("NFR-2.7")
def test_grid_rect_to_cells_on_boundaries() -> None:
    margins = Margins(left=60, top=40, right=20, bottom=20)
    geo = GridGeometry(cell_width=50, cell_height=50, margins=margins)

    # Rect encompassing cell (0, 0) only
    x0, y0, w, h = geo.cell_to_rect(0, 0)
    cells = geo.rect_to_cells(x0, y0, x0 + w - 1, y0 + h - 1, num_qubits=5, num_columns=50)
    assert cells == [(0, 0)]

    # Rect covering boundary spanning cell (0,0) and (1, 1)
    x1_cell, y1_cell, _, _ = geo.cell_to_rect(1, 1)
    cells_span = geo.rect_to_cells(
        x0 + 10, y0 + 10, x1_cell + 10, y1_cell + 10, num_qubits=5, num_columns=50
    )
    assert set(cells_span) == {(0, 0), (0, 1), (1, 0), (1, 1)}
