from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TrackOut(BaseModel):
    slug: str
    name: str
    description: str


class ScenarioOut(BaseModel):
    slug: str
    version: str
    track_slug: str
    title: str
    level: str
    duration_minutes: int
    summary: str
    incident: str
    objectives: list[str]


class StartSessionIn(BaseModel):
    learner_name: str = Field(min_length=2, max_length=120)
    scenario_slug: str


class ConnectionInfo(BaseModel):
    host: str
    port: int
    database: str
    username: str
    password: str
    sslmode: str = "disable"


class SessionOut(BaseModel):
    id: UUID
    learner_name: str
    track_slug: str
    scenario_slug: str
    scenario_version: str
    attempt_number: int
    replay_of_session_id: UUID | None = None
    lab_active: bool
    status: str
    started_at: datetime
    deadline_at: datetime
    score: int | None = None
    result: dict | None = None
    connection: ConnectionInfo

    model_config = {"from_attributes": True}


class EvaluationOut(BaseModel):
    passed: bool
    score: int
    checks: list[dict]
    feedback: list[str]
