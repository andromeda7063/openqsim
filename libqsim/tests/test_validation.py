"""Comprehensive test suite for circuit validation (FR-2.1 to FR-2.11, FR-2.13)."""

import random

from hypothesis import given, settings
from hypothesis import strategies as st
from libqsim.domain.gates import GateType
from libqsim.domain.models import Circuit, GatePlacement
from libqsim.domain.validation import ValidationError, ValidationErrorCode, validate

# ==============================================================================
# Valid circuit tests
# ==============================================================================


def test_valid_empty_circuit() -> None:
    """An empty circuit with 2 qubits has no validation errors."""
    circuit = Circuit(num_qubits=2)
    assert validate(circuit) == []


def test_valid_single_h() -> None:
    """A single H gate on a 1-qubit circuit at column 0 is valid."""
    p = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    circuit = Circuit(num_qubits=1, placements=[p])
    assert validate(circuit) == []


def test_valid_bell_circuit() -> None:
    """A standard Bell-state circuit (H then CNOT) is valid."""
    h = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    cnot = GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=1)
    circuit = Circuit(num_qubits=2, placements=[h, cnot])
    assert validate(circuit) == []


def test_valid_full_grid_h() -> None:
    """A full 10-qubit x 50-column circuit filled with H gates is valid."""
    placements = [
        GatePlacement(GateType.H, targets=[q], controls=[], column=col)
        for q in range(10)
        for col in range(50)
    ]
    circuit = Circuit(num_qubits=10, placements=placements)
    assert validate(circuit) == []


def test_valid_cnot_targets() -> None:
    """CNOT with target on top wire and on bottom wire are both valid."""
    # Control 1, target 0 (target on top wire)
    top_cnot = GatePlacement(GateType.CNOT, targets=[0], controls=[1], column=0)
    # Control 0, target 1 (target on bottom wire)
    bot_cnot = GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=1)
    circuit = Circuit(num_qubits=2, placements=[top_cnot, bot_cnot])
    assert validate(circuit) == []


def test_valid_toffoli_targets() -> None:
    """Toffoli with target on top, middle, and bottom wire are all valid."""
    # Target on top wire (0), controls on 1 and 2
    t_top = GatePlacement(GateType.Toffoli, targets=[0], controls=[1, 2], column=0)
    # Target on middle wire (1), controls on 0 and 2
    t_mid = GatePlacement(GateType.Toffoli, targets=[1], controls=[0, 2], column=1)
    # Target on bottom wire (2), controls on 0 and 1
    t_bot = GatePlacement(GateType.Toffoli, targets=[2], controls=[0, 1], column=2)

    circuit = Circuit(num_qubits=3, placements=[t_top, t_mid, t_bot])
    assert validate(circuit) == []


# ==============================================================================
# Invalid circuit tests (one test per rule, asserting code, offending placement,
# and non-empty plain-text message)
# ==============================================================================


def test_invalid_num_qubits_zero_and_eleven() -> None:
    """Circuit size < 1 or > 10 produces CIRCUIT_SIZE_OUT_OF_RANGE."""
    c0 = Circuit(num_qubits=0)
    errs0 = validate(c0)
    assert len(errs0) == 1
    assert errs0[0].code == ValidationErrorCode.CIRCUIT_SIZE_OUT_OF_RANGE
    assert errs0[0].offending_placement is None
    assert errs0[0].placement is None
    assert isinstance(errs0[0].message, str) and len(errs0[0].message.strip()) > 0

    c11 = Circuit(num_qubits=11)
    errs11 = validate(c11)
    assert len(errs11) == 1
    assert errs11[0].code == ValidationErrorCode.CIRCUIT_SIZE_OUT_OF_RANGE
    assert errs11[0].offending_placement is None
    assert isinstance(errs11[0].message, str) and len(errs11[0].message.strip()) > 0


def test_invalid_column_bounds() -> None:
    """Column indices -1 and 50 produce COLUMN_OUT_OF_RANGE."""
    p_neg = GatePlacement(GateType.H, targets=[0], controls=[], column=-1)
    c_neg = Circuit(num_qubits=2, placements=[p_neg])
    errs_neg = validate(c_neg)
    assert len(errs_neg) == 1
    assert errs_neg[0].code == ValidationErrorCode.COLUMN_OUT_OF_RANGE
    assert errs_neg[0].offending_placement == p_neg
    assert isinstance(errs_neg[0].message, str) and len(errs_neg[0].message.strip()) > 0

    p_50 = GatePlacement(GateType.H, targets=[0], controls=[], column=50)
    c_50 = Circuit(num_qubits=2, placements=[p_50])
    errs_50 = validate(c_50)
    assert len(errs_50) == 1
    assert errs_50[0].code == ValidationErrorCode.COLUMN_OUT_OF_RANGE
    assert errs_50[0].offending_placement == p_50
    assert isinstance(errs_50[0].message, str) and len(errs_50[0].message.strip()) > 0


def test_invalid_qubit_bounds() -> None:
    """Qubit index -1 and n produce QUBIT_INDEX_OUT_OF_RANGE."""
    # Target qubit -1
    p_neg_tgt = GatePlacement(GateType.H, targets=[-1], controls=[], column=0)
    c_neg_tgt = Circuit(num_qubits=2, placements=[p_neg_tgt])
    errs1 = validate(c_neg_tgt)
    assert len(errs1) == 1
    assert errs1[0].code == ValidationErrorCode.QUBIT_INDEX_OUT_OF_RANGE
    assert errs1[0].offending_placement == p_neg_tgt
    assert isinstance(errs1[0].message, str) and len(errs1[0].message.strip()) > 0

    # Target qubit n (2 on a 2-qubit circuit)
    p_n_tgt = GatePlacement(GateType.H, targets=[2], controls=[], column=0)
    c_n_tgt = Circuit(num_qubits=2, placements=[p_n_tgt])
    errs2 = validate(c_n_tgt)
    assert len(errs2) == 1
    assert errs2[0].code == ValidationErrorCode.QUBIT_INDEX_OUT_OF_RANGE
    assert errs2[0].offending_placement == p_n_tgt
    assert isinstance(errs2[0].message, str) and len(errs2[0].message.strip()) > 0

    # Control qubit -1
    p_neg_ctrl = GatePlacement(GateType.CNOT, targets=[0], controls=[-1], column=0)
    c_neg_ctrl = Circuit(num_qubits=2, placements=[p_neg_ctrl])
    errs3 = validate(c_neg_ctrl)
    assert len(errs3) == 1
    assert errs3[0].code == ValidationErrorCode.QUBIT_INDEX_OUT_OF_RANGE
    assert errs3[0].offending_placement == p_neg_ctrl

    # Control qubit n
    p_n_ctrl = GatePlacement(GateType.CNOT, targets=[0], controls=[2], column=0)
    c_n_ctrl = Circuit(num_qubits=2, placements=[p_n_ctrl])
    errs4 = validate(c_n_ctrl)
    assert len(errs4) == 1
    assert errs4[0].code == ValidationErrorCode.QUBIT_INDEX_OUT_OF_RANGE
    assert errs4[0].offending_placement == p_n_ctrl


def test_invalid_gate_arity() -> None:
    """Wrong arity for each gate family produces INVALID_GATE_ARITY."""
    # Single-qubit gate with 0 targets
    p_h_0_tgt = GatePlacement(GateType.H, targets=[], controls=[], column=0)
    errs_h0 = validate(Circuit(num_qubits=2, placements=[p_h_0_tgt]))
    assert len(errs_h0) == 1
    assert errs_h0[0].code == ValidationErrorCode.INVALID_GATE_ARITY
    assert errs_h0[0].offending_placement == p_h_0_tgt
    assert isinstance(errs_h0[0].message, str) and len(errs_h0[0].message.strip()) > 0

    # Single-qubit gate with 1 control
    p_h_ctrl = GatePlacement(GateType.H, targets=[0], controls=[1], column=0)
    errs_h_ctrl = validate(Circuit(num_qubits=2, placements=[p_h_ctrl]))
    assert len(errs_h_ctrl) == 1
    assert errs_h_ctrl[0].code == ValidationErrorCode.INVALID_GATE_ARITY
    assert errs_h_ctrl[0].offending_placement == p_h_ctrl

    # CNOT with 0 controls
    p_cnot_0_ctrl = GatePlacement(GateType.CNOT, targets=[0], controls=[], column=0)
    errs_cnot = validate(Circuit(num_qubits=2, placements=[p_cnot_0_ctrl]))
    assert len(errs_cnot) == 1
    assert errs_cnot[0].code == ValidationErrorCode.INVALID_GATE_ARITY
    assert errs_cnot[0].offending_placement == p_cnot_0_ctrl

    # Toffoli with 1 control
    p_toff_1_ctrl = GatePlacement(GateType.Toffoli, targets=[0], controls=[1], column=0)
    errs_toff = validate(Circuit(num_qubits=3, placements=[p_toff_1_ctrl]))
    assert len(errs_toff) == 1
    assert errs_toff[0].code == ValidationErrorCode.INVALID_GATE_ARITY
    assert errs_toff[0].offending_placement == p_toff_1_ctrl

    # Measurement with 1 control
    p_meas_ctrl = GatePlacement(GateType.Measurement, targets=[0], controls=[1], column=0)
    errs_meas = validate(Circuit(num_qubits=2, placements=[p_meas_ctrl]))
    assert len(errs_meas) == 1
    assert errs_meas[0].code == ValidationErrorCode.INVALID_GATE_ARITY
    assert errs_meas[0].offending_placement == p_meas_ctrl


def test_invalid_duplicate_qubit_in_placement() -> None:
    """Duplicate qubit references within one placement produce DUPLICATE_QUBIT_REFERENCE."""
    # Target and control on the same wire
    p_dup_cnot = GatePlacement(GateType.CNOT, targets=[0], controls=[0], column=0)
    errs1 = validate(Circuit(num_qubits=2, placements=[p_dup_cnot]))
    assert len(errs1) == 1
    assert errs1[0].code == ValidationErrorCode.DUPLICATE_QUBIT_REFERENCE
    assert errs1[0].offending_placement == p_dup_cnot
    assert isinstance(errs1[0].message, str) and len(errs1[0].message.strip()) > 0

    # Duplicate controls on Toffoli
    p_dup_toff = GatePlacement(GateType.Toffoli, targets=[2], controls=[0, 0], column=0)
    errs2 = validate(Circuit(num_qubits=3, placements=[p_dup_toff]))
    assert len(errs2) == 1
    assert errs2[0].code == ValidationErrorCode.DUPLICATE_QUBIT_REFERENCE
    assert errs2[0].offending_placement == p_dup_toff


def test_invalid_cnot_non_contiguous() -> None:
    """CNOT placed on non-contiguous wires (e.g. q0 and q2) produces NON_CONTIGUOUS_QUBITS."""
    p = GatePlacement(GateType.CNOT, targets=[2], controls=[0], column=0)
    circuit = Circuit(num_qubits=3, placements=[p])
    errs = validate(circuit)
    assert len(errs) == 1
    assert errs[0].code == ValidationErrorCode.NON_CONTIGUOUS_QUBITS
    assert errs[0].offending_placement == p
    assert isinstance(errs[0].message, str) and len(errs[0].message.strip()) > 0


def test_invalid_toffoli_non_contiguous() -> None:
    """Toffoli placed on non-contiguous wires (e.g. q0, q1, q3) produces NON_CONTIGUOUS_QUBITS."""
    p = GatePlacement(GateType.Toffoli, targets=[3], controls=[0, 1], column=0)
    circuit = Circuit(num_qubits=4, placements=[p])
    errs = validate(circuit)
    assert len(errs) == 1
    assert errs[0].code == ValidationErrorCode.NON_CONTIGUOUS_QUBITS
    assert errs[0].offending_placement == p
    assert isinstance(errs[0].message, str) and len(errs[0].message.strip()) > 0


def test_invalid_two_gates_on_same_cell() -> None:
    """Two gates occupying the same (qubit, column) cell produce symmetric collision errors."""
    p1 = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    p2 = GatePlacement(GateType.X, targets=[0], controls=[], column=0)
    circuit = Circuit(num_qubits=2, placements=[p1, p2])
    errs = validate(circuit)

    # Symmetric cardinality: each colliding placement receives a collision error
    assert len(errs) == 2
    assert all(e.code == ValidationErrorCode.WIRE_COLUMN_COLLISION for e in errs)
    assert {e.offending_placement for e in errs} == {p1, p2}
    for e in errs:
        assert isinstance(e.message, str) and len(e.message.strip()) > 0


def test_invalid_cnot_overlapping_h() -> None:
    """A CNOT overlapping an H on one of its wires produces symmetric collision errors."""
    h = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    cnot = GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=0)
    circuit = Circuit(num_qubits=2, placements=[h, cnot])
    errs = validate(circuit)

    assert len(errs) == 2
    assert all(e.code == ValidationErrorCode.WIRE_COLUMN_COLLISION for e in errs)
    assert {e.offending_placement for e in errs} == {h, cnot}
    for e in errs:
        assert isinstance(e.message, str) and len(e.message.strip()) > 0


def test_invalid_duplicate_measurement_on_qubit() -> None:
    """Two Measurements on the same qubit wire produce DUPLICATE_MEASUREMENT on the second."""
    m1 = GatePlacement(GateType.Measurement, targets=[0], controls=[], column=1)
    m2 = GatePlacement(GateType.Measurement, targets=[0], controls=[], column=3)
    circuit = Circuit(num_qubits=2, placements=[m1, m2])
    errs = validate(circuit)

    assert len(errs) == 1
    assert errs[0].code == ValidationErrorCode.DUPLICATE_MEASUREMENT
    assert errs[0].offending_placement == m2
    assert isinstance(errs[0].message, str) and len(errs[0].message.strip()) > 0


def test_invalid_gate_after_measurement() -> None:
    """A gate placed after a Measurement on the same wire produces GATE_AFTER_MEASUREMENT."""
    m = GatePlacement(GateType.Measurement, targets=[0], controls=[], column=1)
    x = GatePlacement(GateType.X, targets=[0], controls=[], column=3)
    circuit = Circuit(num_qubits=2, placements=[m, x])
    errs = validate(circuit)

    assert len(errs) == 1
    assert errs[0].code == ValidationErrorCode.GATE_AFTER_MEASUREMENT
    assert errs[0].offending_placement == x
    assert isinstance(errs[0].message, str) and len(errs[0].message.strip()) > 0


def test_invalid_gate_after_measurement_qubit_as_control() -> None:
    """A gate after a Measurement where the measured qubit is a CONTROL produces GATE_AFTER_MEASUREMENT."""
    m = GatePlacement(GateType.Measurement, targets=[0], controls=[], column=1)
    cnot = GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=3)
    circuit = Circuit(num_qubits=2, placements=[m, cnot])
    errs = validate(circuit)

    assert len(errs) == 1
    assert errs[0].code == ValidationErrorCode.GATE_AFTER_MEASUREMENT
    assert errs[0].offending_placement == cnot
    assert isinstance(errs[0].message, str) and len(errs[0].message.strip()) > 0


# ==============================================================================
# Cascade rule tests
# ==============================================================================


def test_cascade_rule_out_of_range_qubit() -> None:
    """An out-of-range placement produces its own error and NO derived contiguity/collision errors."""
    # CNOT on wire 0 and 5 on a 2-qubit circuit:
    # Qubit 5 is out of range. It must NOT emit NON_CONTIGUOUS_QUBITS or collision errors.
    p = GatePlacement(GateType.CNOT, targets=[5], controls=[0], column=0)
    circuit = Circuit(num_qubits=2, placements=[p])
    errs = validate(circuit)

    assert len(errs) == 1
    assert errs[0].code == ValidationErrorCode.QUBIT_INDEX_OUT_OF_RANGE
    assert errs[0].offending_placement == p


def test_cascade_rule_out_of_range_column_collision() -> None:
    """Two placements at column 50 produce COLUMN_OUT_OF_RANGE and NO derived collision errors."""
    p1 = GatePlacement(GateType.H, targets=[0], controls=[], column=50)
    p2 = GatePlacement(GateType.H, targets=[0], controls=[], column=50)
    circuit = Circuit(num_qubits=2, placements=[p1, p2])
    errs = validate(circuit)

    assert len(errs) == 2
    assert all(e.code == ValidationErrorCode.COLUMN_OUT_OF_RANGE for e in errs)
    # Neither produces a WIRE_COLUMN_COLLISION error


def test_cascade_rule_out_of_range_suppresses_measurement_error() -> None:
    """An out-of-range gate placed after Measurement does not produce GATE_AFTER_MEASUREMENT."""
    m = GatePlacement(GateType.Measurement, targets=[0], controls=[], column=1)
    p = GatePlacement(GateType.H, targets=[0], controls=[], column=55)
    circuit = Circuit(num_qubits=2, placements=[m, p])
    errs = validate(circuit)

    assert len(errs) == 1
    assert errs[0].code == ValidationErrorCode.COLUMN_OUT_OF_RANGE
    assert errs[0].offending_placement == p


# ==============================================================================
# Determinism, Purity, and Robustness tests
# ==============================================================================


def test_determinism_under_shuffling() -> None:
    """Shuffling input placements yields an identical error list."""
    p1 = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    p2 = GatePlacement(GateType.X, targets=[0], controls=[], column=0)  # collision with p1
    p3 = GatePlacement(GateType.CNOT, targets=[3], controls=[0], column=1)  # non-contiguous on 3-q
    p4 = GatePlacement(GateType.Measurement, targets=[1], controls=[], column=2)
    p5 = GatePlacement(GateType.Z, targets=[1], controls=[], column=3)  # after measurement

    placements = [p1, p2, p3, p4, p5]
    base_errors = validate(Circuit(num_qubits=4, placements=placements))

    # Test across multiple random permutations
    rng = random.Random(42)
    for _ in range(25):
        shuffled = list(placements)
        rng.shuffle(shuffled)
        shuffled_errors = validate(Circuit(num_qubits=4, placements=shuffled))
        assert shuffled_errors == base_errors


def test_purity() -> None:
    """Circuit is unchanged after validate, and validating twice gives equal results."""
    h = GatePlacement(GateType.H, targets=[0], controls=[], column=0)
    cnot = GatePlacement(GateType.CNOT, targets=[1], controls=[0], column=1)
    circuit = Circuit(num_qubits=2, placements=[h, cnot])

    errs1 = validate(circuit)
    errs2 = validate(circuit)

    assert errs1 == []
    assert errs2 == []
    assert circuit.num_qubits == 2
    assert circuit.placements == (h, cnot)


def test_robustness_malformed_data() -> None:
    """validate does not raise on empty targets, huge/negative ints, or repeated placements."""
    p_empty = GatePlacement(GateType.H, targets=[], controls=[], column=0)
    p_huge = GatePlacement(GateType.X, targets=[999_999], controls=[888_888], column=1_000_000)
    p_neg = GatePlacement(GateType.Z, targets=[-50], controls=[-20], column=-999)
    p_normal = GatePlacement(GateType.H, targets=[0], controls=[], column=0)

    circuit = Circuit(
        num_qubits=-5,
        placements=[p_empty, p_huge, p_neg, p_normal, p_normal],
    )

    # Calling validate must execute without raising unhandled exceptions
    errors = validate(circuit)
    assert isinstance(errors, list)
    assert len(errors) > 0
    assert all(isinstance(e, ValidationError) for e in errors)


# ==============================================================================
# Hypothesis property-based tests
# ==============================================================================


@st.composite
def arbitrary_gate_placement(draw: st.DrawFn) -> GatePlacement:
    """Generate arbitrary GatePlacement objects, including malformed parameters."""
    gt = draw(st.sampled_from(list(GateType)))
    targets = draw(st.lists(st.integers(min_value=-5, max_value=15), max_size=4))
    controls = draw(st.lists(st.integers(min_value=-5, max_value=15), max_size=4))
    column = draw(st.integers(min_value=-10, max_value=60))
    return GatePlacement(gate_type=gt, targets=targets, controls=controls, column=column)


@st.composite
def arbitrary_circuit(draw: st.DrawFn) -> Circuit:
    """Generate arbitrary Circuit instances."""
    num_qubits = draw(st.integers(min_value=-5, max_value=15))
    placements = draw(st.lists(arbitrary_gate_placement(), max_size=10))
    return Circuit(num_qubits=num_qubits, placements=placements)


@given(arbitrary_circuit())
@settings(max_examples=100)
def test_hypothesis_validation_invariants(circuit: Circuit) -> None:
    """Property test verifying validation invariants across arbitrary circuits."""
    errors1 = validate(circuit)
    errors2 = validate(circuit)

    # 1. Purity: Calling validate twice produces identical results
    assert errors1 == errors2

    # 2. Return types & contracts
    assert isinstance(errors1, list)
    for err in errors1:
        assert isinstance(err, ValidationError)
        assert isinstance(err.code, ValidationErrorCode)
        assert isinstance(err.message, str) and len(err.message.strip()) > 0
        assert err.offending_placement == err.placement

    # 3. Determinism under permutation: Reversing placements yields identical errors
    reversed_circuit = Circuit(
        num_qubits=circuit.num_qubits,
        placements=list(reversed(circuit.placements)),
    )
    reversed_errors = validate(reversed_circuit)
    assert reversed_errors == errors1
