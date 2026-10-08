import pytest
from libqsim.application.operations import place_gate
from libqsim.application.session import EditorSession, SaveStatus, SimulationStatus
from libqsim.examples import get_example, list_examples, validate_examples


@pytest.mark.req("FR-5.19", "FR-5.20", "NFR-4.4", "NFR-7.9")
def test_catalog_has_five_valid_named_examples() -> None:
    examples = list_examples()
    assert len(examples) == 5
    assert all(example.name and example.description for example in examples)
    assert validate_examples() == ()
    for example in examples:
        session = EditorSession()
        assert session.load_example(example).ok
        assert session.run().ok


@pytest.mark.req("FR-5.20", "FR-5.21", "FR-5.22", "FR-5.23", "LC-18")
def test_load_example_replaces_session_as_unsaved_and_clears_history() -> None:
    session = EditorSession()
    session.apply(place_gate(session.circuit, "X", 0, 0))
    assert session.can_undo
    assert session.run().ok

    outcome = session.load_example(get_example("Bell state"))

    assert outcome.ok
    assert session.circuit == get_example("Bell state").circuit
    assert session.file_path is None
    assert session.baseline is None
    assert session.save_status is SaveStatus.DIRTY
    assert session.simulation_status is SimulationStatus.NONE
    assert not session.can_undo and not session.can_redo


@pytest.mark.req("FR-5.25", "LC-18")
def test_invalid_example_failure_preserves_session_state() -> None:
    from libqsim.domain.gates import GateType
    from libqsim.domain.models import Circuit, GatePlacement
    from libqsim.examples import CircuitExample

    session = EditorSession()
    before = (
        session.circuit,
        session.file_path,
        session.baseline,
        session.save_status,
        session.simulation_status,
        session.can_undo,
        session.can_redo,
    )
    invalid = CircuitExample(
        "invalid", "invalid fixture", Circuit(2, (GatePlacement(GateType.H, (8,), (), 0),))
    )
    assert not session.load_example(invalid).ok
    assert before == (
        session.circuit,
        session.file_path,
        session.baseline,
        session.save_status,
        session.simulation_status,
        session.can_undo,
        session.can_redo,
    )
