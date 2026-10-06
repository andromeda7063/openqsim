"""Tests for pure histogram layout calculation."""

import pytest
from qsim_gui.widgets.histogram_view import compute_histogram_layout


@pytest.mark.req("FR-4.7", "FR-4.8")
def test_histogram_bar_count_for_1_to_10_qubits() -> None:
    for n in range(1, 11):
        num_states = 1 << n
        probs = [1.0 / num_states] * num_states
        layout = compute_histogram_layout(probs, width=1000.0, height=400.0)
        assert len(layout) == num_states
        # First label is all 0s, last label is all 1s
        assert layout[0].label == "0" * n
        assert layout[-1].label == "1" * n


@pytest.mark.req("FR-4.8", "FR-4.9")
def test_histogram_bar_heights_proportional_and_normalized() -> None:
    probs = [0.1, 0.4, 0.0, 0.5]
    layout = compute_histogram_layout(probs, width=600.0, height=300.0)

    assert len(layout) == 4
    # Highest probability has highest bar height
    assert layout[3].height > layout[1].height > layout[0].height
    assert layout[2].height == 0.0

    # Probability sum is 1.0 within numerical tolerance
    total_prob = sum(b.probability for b in layout)
    assert total_prob == pytest.approx(1.0, abs=1e-9)


@pytest.mark.req("FR-4.7", "FR-4.8")
def test_histogram_label_policy_by_width() -> None:
    # 4 bars in 600px -> width per bar is plenty large (> 26px), show_label should be True
    layout_wide = compute_histogram_layout([0.25] * 4, width=600.0, height=300.0)
    assert all(b.show_label for b in layout_wide)

    # 128 bars in 200px -> bar width is tiny (< 26px), show_label should be False
    layout_narrow = compute_histogram_layout([1.0 / 128] * 128, width=200.0, height=300.0)
    assert not any(b.show_label for b in layout_narrow)
