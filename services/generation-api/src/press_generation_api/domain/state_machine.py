from dataclasses import dataclass

from press_generation_api.domain.models import PressingStatus

ALLOWED_TRANSITIONS: dict[PressingStatus, frozenset[PressingStatus]] = {
    PressingStatus.DRAFT: frozenset({PressingStatus.PREPARING_SOURCE}),
    PressingStatus.PREPARING_SOURCE: frozenset(
        {PressingStatus.UNDERSTANDING_FRAGMENT, PressingStatus.FAILED}
    ),
    PressingStatus.UNDERSTANDING_FRAGMENT: frozenset(
        {PressingStatus.CREATING_WORLD, PressingStatus.FAILED}
    ),
    PressingStatus.CREATING_WORLD: frozenset(
        {PressingStatus.RENDERING_PRESSING, PressingStatus.FAILED}
    ),
    PressingStatus.RENDERING_PRESSING: frozenset(
        {PressingStatus.SAVING_PRESSING, PressingStatus.FAILED}
    ),
    PressingStatus.SAVING_PRESSING: frozenset({PressingStatus.READY, PressingStatus.FAILED}),
    PressingStatus.READY: frozenset(),
    PressingStatus.FAILED: frozenset(
        {
            PressingStatus.PREPARING_SOURCE,
            PressingStatus.UNDERSTANDING_FRAGMENT,
            PressingStatus.CREATING_WORLD,
            PressingStatus.RENDERING_PRESSING,
            PressingStatus.SAVING_PRESSING,
        }
    ),
}


@dataclass(frozen=True, slots=True)
class InvalidPressingTransition(ValueError):
    current: PressingStatus
    target: PressingStatus

    def __str__(self) -> str:
        return f"Pressing cannot transition from {self.current.value} to {self.target.value}"


def can_transition(current: PressingStatus, target: PressingStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def transition(current: PressingStatus, target: PressingStatus) -> PressingStatus:
    if not can_transition(current, target):
        raise InvalidPressingTransition(current=current, target=target)
    return target
