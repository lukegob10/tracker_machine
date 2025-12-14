from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, ConfigDict, constr

from .enums import ProjectStatus, SolutionStatus, SubcomponentStatus


class ProjectBase(BaseModel):
    project_name: Optional[str] = None
    name_abbreviation: Optional[constr(min_length=4, max_length=4)] = None  # type: ignore[type-arg]
    status: Optional[ProjectStatus] = None
    description: Optional[str] = None
    sponsor: Optional[str] = None


class ProjectCreate(ProjectBase):
    project_name: str
    name_abbreviation: constr(min_length=4, max_length=4)  # type: ignore[type-arg]
    status: ProjectStatus = ProjectStatus.not_started
    sponsor: str


class ProjectUpdate(ProjectBase):
    pass


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: str
    project_name: str
    name_abbreviation: str
    status: ProjectStatus
    description: Optional[str] = None
    sponsor: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SolutionBase(BaseModel):
    solution_name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[SolutionStatus] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    key_stakeholder: Optional[str] = None


class SolutionCreate(SolutionBase):
    solution_name: str
    version: str
    status: SolutionStatus = SolutionStatus.not_started
    owner: str


class SolutionUpdate(SolutionBase):
    pass


class SolutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    solution_id: str
    project_id: str
    solution_name: str
    version: str
    status: SolutionStatus
    description: Optional[str] = None
    owner: Optional[str] = None
    key_stakeholder: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PhaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phase_id: str
    phase_group: str
    phase_name: str
    sequence: int
    created_at: datetime
    updated_at: datetime


class SolutionPhaseInput(BaseModel):
    phase_id: str
    is_enabled: bool = True
    sequence_override: Optional[int] = None


class SolutionPhaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    solution_phase_id: str
    solution_id: str
    phase_id: str
    is_enabled: bool
    sequence_override: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class SubcomponentBase(BaseModel):
    subcomponent_name: Optional[str] = None
    status: Optional[SubcomponentStatus] = None
    priority: Optional[int] = None
    due_date: Optional[date] = None
    sub_phase: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    dependencies: Optional[str] = None
    work_estimate: Optional[float] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    approver: Optional[str] = None


class SubcomponentCreate(SubcomponentBase):
    subcomponent_name: str
    status: SubcomponentStatus = SubcomponentStatus.to_do
    priority: int = 3
    owner: str
    assignee: str


class SubcomponentUpdate(SubcomponentBase):
    pass


class SubcomponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subcomponent_id: str
    project_id: str
    solution_id: str
    subcomponent_name: str
    status: SubcomponentStatus
    priority: int
    due_date: Optional[date] = None
    sub_phase: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    category: Optional[str] = None
    dependencies: Optional[str] = None
    work_estimate: Optional[float] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    approver: Optional[str] = None
    user_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SubcomponentPhaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subcomponent_phase_id: str
    subcomponent_id: str
    solution_phase_id: str
    phase_id: str
    is_complete: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SubcomponentPhaseUpdate(BaseModel):
    solution_phase_id: str
    is_complete: bool
