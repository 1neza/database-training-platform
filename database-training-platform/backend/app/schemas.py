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
    skills: list[str]
    prerequisites: list[str]
    duration_minutes: int
    summary: str
    incident: str
    objectives: list[str]


class SkillOut(BaseModel):
    slug: str
    name: str
    description: str


class ScenarioReadinessOut(BaseModel):
    scenario_slug: str
    scenario_title: str
    scenario_version: str
    state: str
    skills: list[str]
    prerequisites: list[str]
    missing_prerequisites: list[str]
    recommended: bool


class LearningPathOut(BaseModel):
    track_slug: str
    mastered_skills: list[SkillOut]
    scenarios: list[ScenarioReadinessOut]


class CreateLearnerIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)


class LearnerOut(BaseModel):
    id: UUID
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StartSessionIn(BaseModel):
    learner_name: str = Field(min_length=2, max_length=120)
    scenario_slug: str
    learner_id: UUID | None = None


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


class AttemptHistoryOut(BaseModel):
    id: UUID
    scenario_slug: str
    scenario_title: str
    scenario_version: str
    attempt_number: int
    status: str
    score: int | None = None
    started_at: datetime
    deadline_at: datetime
    lab_active: bool
    replay_of_session_id: UUID | None = None


class ScenarioProgressOut(BaseModel):
    scenario_slug: str
    scenario_title: str
    attempts: int
    passed_attempts: int
    best_score: int | None = None
    latest_score: int | None = None
    latest_status: str
    latest_attempt_at: datetime


class LearnerProgressOut(BaseModel):
    learner_id: UUID
    total_attempts: int
    completed_attempts: int
    passed_attempts: int
    scenarios_attempted: int
    scenarios_passed: int
    average_best_score: float | None = None
    scenario_progress: list[ScenarioProgressOut]


class EvaluationOut(BaseModel):
    passed: bool
    score: int
    checks: list[dict]
    feedback: list[str]
