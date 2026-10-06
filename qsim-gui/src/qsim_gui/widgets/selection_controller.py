"""Pure Qt-free selection controller for the quantum circuit editor."""

from collections.abc import Callable, Iterable

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
