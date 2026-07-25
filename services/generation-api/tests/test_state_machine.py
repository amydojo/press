import itertools

import pytest

from press_generation_api.domain.models import PressingStatus
from press_generation_api.domain.state_machine import (
    ALLOWED_TRANSITIONS,
    InvalidPressingTransition,
    transition,
)


ALLOWED_PAIRS = {
    (current, target)
    for current, targets in ALLOWED_TRANSITIONS.items()
    for target in targets
}
ALL_PAIRS = set(itertools.product(PressingStatus, repeat=2))
REJECTED_PAIRS = ALL_PAIRS - ALLOWED_PAIRS


@pytest.mark.parametrize(("current", "target"), sorted(ALLOWED_PAIRS, key=lambda pair: (pair[0], pair[1])))
def test_every_allowed_transition(current: PressingStatus, target: PressingStatus) -> None:
    assert transition(current, target) is target


@pytest.mark.parametrize(("current", "target"), sorted(REJECTED_PAIRS, key=lambda pair: (pair[0], pair[1])))
def test_every_rejected_transition(current: PressingStatus, target: PressingStatus) -> None:
    with pytest.raises(InvalidPressingTransition):
        transition(current, target)
