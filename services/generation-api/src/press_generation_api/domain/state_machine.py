from dataclasses import dataclass

from press_generation_api.domain.models import PressingStatus

ALLOWED_TRANSITIONS: dict[PressingStatus, frozenset[PressingStatus]] = {
    PressingStatus.DRAFT: frozenset({PressingStatus.PREPARING_SOURCE, PressingStatus.DELETED}),
    PressingStatus.PREPARING_SOURCE: frozenset(
        {PressingStatus.UNDERSTANDING_FRAGMENT, PressingStatus.FAILED, PressingStatus.DELETED}
    ),
    PressingStatus.UNDERSTANDING_FRAGMENT: frozenset(
        {PressingStatus.CREATING_WORLD, PressingStatus.FAILED, PressingStatus.DELETED}
    ),
    PressingStatus.CREATING_WORLD: frozenset(
        {
            PressingStatus.RENDERING_PRESSING,
            PressingStatus.RETRYING_GENERATION,
            PressingStatus.FAILED,
            PressingStatus.DELETED,
        }
    ),
    PressingStatus.RENDERING_PRESSING: frozenset(
        {
            PressingStatus.SAVING_PRESSING,
            PressingStatus.RETRYING_GENERATION,
            PressingStatus.FAILED,
            PressingStatus.DELETED,
        }
    ),
    PressingStatus.SAVING_PRESSING: frozenset(
        {PressingStatus.READY, PressingStatus.FAILED, PressingStatus.DELETED}
    ),
    PressingStatus.RETRYING_GENERATION: frozenset(
        {
            PressingStatus.UNDERSTANDING_FRAGMENT,
            PressingStatus.CREATING_WORLD,
            PressingStatus.FAILED,
            PressingStatus.DELETED,
        }
    ),
    PressingStatus.READY: frozenset({PressingStatus.DELETED}),
    PressingStatus.FAILED: frozenset(
        {
            PressingStatus.PREPARING_SOURCE,
            PressingStatus.UNDERSTANDING_FRAGMENT,
            PressingStatus.CREATING_WORLD,
            PressingStatus.RETRYING_GENERATION,
            PressingStatus.DELETED,
        }
    ),
    PressingStatus.DELETED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class InvalidPressingTransitionError(ValueError):
    current: PressingStatus
    target: PressingStatus

    def __str__(self) -> str:
        return f"Pressing cannot transition from {self.current.value} to {self.target.value}"


def can_transition(current: PressingStatus, target: PressingStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def transition(current: PressingStatus, target: PressingStatus) -> PressingStatus:
    if not can_transition(current, target):
        raise InvalidPressingTransitionError(current=current, target=target)
    return target
