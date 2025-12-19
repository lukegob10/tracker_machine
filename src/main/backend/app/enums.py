from enum import Enum


class ProjectStatus(str, Enum):
    not_started = "not_started"
    active = "active"
    on_hold = "on_hold"
    complete = "complete"
    abandoned = "abandoned"


class SolutionStatus(str, Enum):
    not_started = "not_started"
    active = "active"
    on_hold = "on_hold"
    complete = "complete"
    abandoned = "abandoned"


class SubcomponentStatus(str, Enum):
    to_do = "to_do"
    in_progress = "in_progress"
    on_hold = "on_hold"
    complete = "complete"
    abandoned = "abandoned"


class RagStatus(str, Enum):
    red = "red"
    amber = "amber"
    green = "green"


class RagSource(str, Enum):
    auto = "auto"
    manual = "manual"
