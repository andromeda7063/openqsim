"""Pure Qt-free selection controller for the quantum circuit editor."""

from collections.abc import Callable, Iterable

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
        raise NotImplementedError

    @property
    def last_clicked_cell(self) -> tuple[int, int] | None:
        raise NotImplementedError

    @property
    def is_marquee_active(self) -> bool:
        raise NotImplementedError

    @property
    def marquee_start(self) -> tuple[int, int] | None:
        raise NotImplementedError

    @property
    def marquee_current(self) -> tuple[int, int] | None:
        raise NotImplementedError

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        raise NotImplementedError

    def set_selection(self, selection: Iterable[GatePlacement]) -> None:
        raise NotImplementedError

    def clear_selection(self) -> None:
        raise NotImplementedError

    def select_all(self, circuit: Circuit) -> None:
        raise NotImplementedError

    def prune(self, circuit: Circuit) -> None:
        raise NotImplementedError

    def click_cell(self, circuit: Circuit, cell: tuple[int, int], ctrl: bool = False) -> None:
        raise NotImplementedError

    def press_gate(
        self, placement: GatePlacement, cell: tuple[int, int], ctrl: bool = False
    ) -> None:
        raise NotImplementedError

    def press_empty(self, cell: tuple[int, int], ctrl: bool = False) -> None:
        raise NotImplementedError

    def marquee_begin(self, cell: tuple[int, int], ctrl: bool = False) -> None:
        raise NotImplementedError

    def marquee_update(self, circuit: Circuit, cell: tuple[int, int]) -> None:
        raise NotImplementedError

    def marquee_update_rect(
        self, circuit: Circuit, q_min: int, q_max: int, c_min: int, c_max: int
    ) -> None:
        raise NotImplementedError

    def marquee_end(self, circuit: Circuit, cell: tuple[int, int] | None = None) -> None:
        raise NotImplementedError
