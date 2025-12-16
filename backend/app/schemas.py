from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, ConfigDict, constr

from .enums import ProjectStatus, RagSource, RagStatus, SolutionStatus, SubcomponentStatus


class UserBase(BaseModel):
    soeid: str
    display_name: str


class UserCreate(UserBase):
    password: constr(min_length=8)  # type: ignore[type-arg]


class UserLogin(BaseModel):
    soeid: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    soeid: str
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ChangeLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    change_id: str
    entity_type: str
    entity_id: str
    action: str
    field: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    user_id: str
    request_id: Optional[str] = None
    created_at: datetime


class ProjectBase(BaseModel):
    project_name: Optional[str] = None
    name_abbreviation: Optional[constr(min_length=4, max_length=4)] = None  # type: ignore[type-arg]
    status: Optional[ProjectStatus] = None
    description: Optional[str] = None
    success_criteria: Optional[str] = None
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
    success_criteria: Optional[str] = None
    sponsor: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SolutionBase(BaseModel):
    solution_name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[SolutionStatus] = None
    rag_status: Optional[RagStatus] = None
    rag_source: Optional[RagSource] = None
    rag_reason: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[date] = None
    current_phase: Optional[str] = None
    description: Optional[str] = None
    success_criteria: Optional[str] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    approver: Optional[str] = None
    key_stakeholder: Optional[str] = None
    blockers: Optional[str] = None
    risks: Optional[str] = None


class SolutionCreate(SolutionBase):
    solution_name: str
    version: str
    status: SolutionStatus = SolutionStatus.not_started
    priority: int = 3
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
    rag_status: RagStatus
    rag_source: RagSource
    rag_reason: Optional[str] = None
    priority: int
    due_date: Optional[date] = None
    current_phase: Optional[str] = None
    description: Optional[str] = None
    success_criteria: Optional[str] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    approver: Optional[str] = None
    key_stakeholder: Optional[str] = None
    blockers: Optional[str] = None
    risks: Optional[str] = None
    completed_at: Optional[datetime] = None
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
    assignee: Optional[str] = None


class SubcomponentCreate(SubcomponentBase):
    subcomponent_name: str
    status: SubcomponentStatus = SubcomponentStatus.to_do
    priority: int = 3
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
    assignee: Optional[str] = None
    user_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
