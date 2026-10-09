"""Pure Qt-free selection controller for the quantum circuit editor."""

from collections.abc import Callable, Iterable

from libqsim.application.operations import OperationResult, change_target, move_gates
from libqsim.application.selection import (
    click_selection,
    gate_at,
    gates_in_rect,
    marquee_selection,
    prune_selection,
)
from libqsim.application.selection import (
    select_all as libqsim_select_all,
)
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement


class SelectionController:
    """Manages circuit editor selection state and mouse interaction logic without Qt."""

    def __init__(
        self,
        selection: frozenset[GatePlacement] = frozenset(),
        last_clicked_cell: tuple[int, int] | None = None,
    ) -> None:
        self._selection: frozenset[GatePlacement] = frozenset(selection)
        self._last_clicked_cell: tuple[int, int] | None = last_clicked_cell
        self._marquee_start: tuple[int, int] | None = None
        self._marquee_current: tuple[int, int] | None = None
        self._marquee_ctrl: bool = False
        self._base_selection: frozenset[GatePlacement] = frozenset(selection)

        # Drag-to-move state
        self._drag_start_cell: tuple[int, int] | None = None
        self._drag_current_cell: tuple[int, int] | None = None
        self._drag_start_pixel: tuple[int, int] | None = None
        self._drag_initiated: bool = False
        self._dragging_move: bool = False

        self._subscribers: list[Callable[[], None]] = []

    @property
    def selection(self) -> frozenset[GatePlacement]:
        return self._selection

    @property
    def last_clicked_cell(self) -> tuple[int, int] | None:
        return self._last_clicked_cell

    @property
    def is_marquee_active(self) -> bool:
        return self._marquee_start is not None

    @property
    def marquee_start(self) -> tuple[int, int] | None:
        return self._marquee_start

    @property
    def marquee_current(self) -> tuple[int, int] | None:
        return self._marquee_current

    @property
    def is_drag_initiated(self) -> bool:
        return self._drag_initiated

    @property
    def is_dragging_move(self) -> bool:
        return self._dragging_move

    @property
    def drag_start_cell(self) -> tuple[int, int] | None:
        return self._drag_start_cell

    @property
    def drag_current_cell(self) -> tuple[int, int] | None:
        return self._drag_current_cell

    @property
    def drag_delta(self) -> tuple[int, int]:
        if (
            self._dragging_move
            and self._drag_start_cell is not None
            and self._drag_current_cell is not None
        ):
            return (
                self._drag_current_cell[0] - self._drag_start_cell[0],
                self._drag_current_cell[1] - self._drag_start_cell[1],
            )
        return (0, 0)

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    def _notify(self) -> None:
        for cb in list(self._subscribers):
            cb()

    def set_selection(self, selection: Iterable[GatePlacement]) -> None:
        new_sel = frozenset(selection)
        if new_sel != self._selection:
            self._selection = new_sel
            self._notify()

    def clear_selection(self) -> None:
        if self._selection:
            self._selection = frozenset()
            self._notify()

    def select_all(self, circuit: Circuit) -> None:
        new_sel = libqsim_select_all(circuit)
        if new_sel != self._selection:
            self._selection = new_sel
            self._notify()

    def prune(self, circuit: Circuit) -> None:
        new_sel = prune_selection(circuit, self._selection)
        if new_sel != self._selection:
            self._selection = new_sel
            self._notify()

    def click_cell(self, circuit: Circuit, cell: tuple[int, int], ctrl: bool = False) -> None:
        self._last_clicked_cell = cell
        hit = gate_at(circuit, cell[0], cell[1])
        new_sel = click_selection(self._selection, hit, ctrl=ctrl)
        if new_sel != self._selection:
            self._selection = new_sel
            self._notify()

    def press_gate(
        self, placement: GatePlacement, cell: tuple[int, int], ctrl: bool = False
    ) -> None:
        self._last_clicked_cell = cell
        new_sel = click_selection(self._selection, placement, ctrl=ctrl)
        if new_sel != self._selection:
            self._selection = new_sel
            self._notify()

    def press_empty(self, cell: tuple[int, int], ctrl: bool = False) -> None:
        self._last_clicked_cell = cell
        new_sel = click_selection(self._selection, None, ctrl=ctrl)
        if new_sel != self._selection:
            self._selection = new_sel
            self._notify()

    def click_empty(self, cell: tuple[int, int], ctrl: bool = False) -> None:
        self.press_empty(cell, ctrl=ctrl)

    def marquee_begin(self, cell: tuple[int, int], ctrl: bool = False) -> None:
        self._last_clicked_cell = cell
        self._marquee_start = cell
        self._marquee_current = cell
        self._marquee_ctrl = ctrl
        self._base_selection = self._selection
        if not ctrl and self._selection:
            self._selection = frozenset()
            self._notify()

    def marquee_update(self, circuit: Circuit, cell: tuple[int, int]) -> None:
        if self._marquee_start is None:
            return
        self._marquee_current = cell
        q_min, q_max = min(self._marquee_start[0], cell[0]), max(self._marquee_start[0], cell[0])
        c_min, c_max = min(self._marquee_start[1], cell[1]), max(self._marquee_start[1], cell[1])
        self.marquee_update_rect(circuit, q_min, q_max, c_min, c_max)

    def marquee_update_rect(
        self, circuit: Circuit, q_min: int, q_max: int, c_min: int, c_max: int
    ) -> None:
        if self._marquee_start is None:
            return
        rect_gates = gates_in_rect(circuit, q_min, q_max, c_min, c_max)
        new_sel = marquee_selection(self._base_selection, rect_gates, ctrl=self._marquee_ctrl)
        if new_sel != self._selection:
            self._selection = new_sel
            self._notify()

    def marquee_end(self, circuit: Circuit, cell: tuple[int, int] | None = None) -> None:
        if cell is not None and self._marquee_start is not None:
            self.marquee_update(circuit, cell)
        self._marquee_start = None
        self._marquee_current = None
        self._marquee_ctrl = False
        self._notify()

    def cancel_marquee(self) -> None:
        if self._marquee_start is not None:
            self._marquee_start = None
            self._marquee_current = None
            self._marquee_ctrl = False
            self.set_selection(self._base_selection)
            self._notify()

    # --- Move & Drag interactions ---

    def press_cell_for_drag(
        self,
        circuit: Circuit,
        cell: tuple[int, int],
        pixel_pos: tuple[int, int],
        ctrl: bool = False,
    ) -> None:
        """Handle mouse press on a cell that could potentially drag-to-move."""
        self._last_clicked_cell = cell
        hit = gate_at(circuit, cell[0], cell[1])
        if hit is not None:
            if hit not in self._selection:
                self.press_gate(hit, cell, ctrl=ctrl)
            self.start_drag_move(cell, pixel_pos)
        else:
            self.press_empty(cell, ctrl=ctrl)
            self.marquee_begin(cell, ctrl=ctrl)

    def start_drag_move(self, cell: tuple[int, int], pixel_pos: tuple[int, int]) -> None:
        """Record start of potential drag-to-move operation."""
        self._drag_start_cell = cell
        self._drag_current_cell = cell
        self._drag_start_pixel = pixel_pos
        self._drag_initiated = True
        self._dragging_move = False

    def cancel_drag_move(self) -> None:
        self._drag_initiated = False
        self._dragging_move = False
        self._drag_start_cell = None
        self._drag_current_cell = None
        self._drag_start_pixel = None
        self._notify()

    def update_drag_move(
        self,
        cell: tuple[int, int],
        pixel_pos: tuple[int, int],
        threshold: float = 5.0,
    ) -> None:
        """Update drag movement and activate move state if beyond pixel threshold."""
        if not self._drag_initiated or self._drag_start_pixel is None:
            return
        self._drag_current_cell = cell
        dx = pixel_pos[0] - self._drag_start_pixel[0]
        dy = pixel_pos[1] - self._drag_start_pixel[1]
        dist = (dx * dx + dy * dy) ** 0.5
        if dist >= threshold:
            if not self._dragging_move:
                self._dragging_move = True
            self._notify()

    def end_drag_move(
        self,
        circuit: Circuit,
        cell: tuple[int, int] | None = None,
    ) -> str:
        """End drag-to-move; return 'click' if ended on start cell or 'move' if dragged."""
        if not self._drag_initiated:
            return "none"

        was_dragging = self._dragging_move
        start_cell = self._drag_start_cell
        cur_cell = cell if cell is not None else self._drag_current_cell
        delta = (0, 0)
        if was_dragging and start_cell is not None and cur_cell is not None:
            delta = (cur_cell[0] - start_cell[0], cur_cell[1] - start_cell[1])

        self._drag_initiated = False
        self._dragging_move = False
        self._drag_start_cell = None
        self._drag_current_cell = None
        self._drag_start_pixel = None
        self._notify()

        if not was_dragging or delta == (0, 0):
            if start_cell is not None:
                hit = gate_at(circuit, start_cell[0], start_cell[1])
                if hit is not None and len(self._selection) > 1:
                    self.press_gate(hit, start_cell, ctrl=False)
            return "click"
        return "move"

    def move_selection(self, circuit: Circuit, d_qubit: int, d_column: int) -> OperationResult:
        """Translate the currently selected gates by d_qubit and d_column."""
        if not self._selection or (d_qubit == 0 and d_column == 0):
            return OperationResult(status="noop", circuit=circuit)
        return move_gates(circuit, self._selection, d_qubit, d_column)

    def follow_move(self, result: OperationResult) -> None:
        """Update selection to follow the touched placements after a successful move."""
        if result.status == "applied" and result.touched:
            self.set_selection(result.touched)

    def can_change_target(self) -> bool:
        """True if exactly one CNOT or Toffoli gate is selected."""
        if len(self._selection) != 1:
            return False
        gate = next(iter(self._selection))
        return gate.gate_type in (GateType.CNOT, GateType.Toffoli)

    def change_target_selected(self, circuit: Circuit) -> OperationResult:
        """Cycle or swap target/control assignments on the single selected CNOT/Toffoli."""
        if not self.can_change_target():
            return OperationResult(
                status="rejected",
                circuit=circuit,
                messages=(
                    "Change target is enabled only when exactly one CNOT/Toffoli is selected.",
                ),
            )
        placement = next(iter(self._selection))
        return change_target(circuit, placement)
