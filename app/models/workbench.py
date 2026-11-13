
"""Additive tables for the CodeMentor workspace."""

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Diagnosis(Base):
    __tablename__ = "cm_diagnoses"

    owner: Mapped[str] = mapped_column(String(32), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    knowledge_id: Mapped[str | None] = mapped_column(String(40), index=True)
    result: Mapped[dict] = mapped_column(JSON)


class Challenge(Base):
    __tablename__ = "cm_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(32), index=True)
    template_id: Mapped[str] = mapped_column(String(60))
    knowledge_id: Mapped[str] = mapped_column(String(40))
    hints_used: Mapped[int] = mapped_column(default=0)
    closed: Mapped[bool] = mapped_column(default=False)


class Attempt(Base):
    __tablename__ = "cm_attempts"

    challenge_id: Mapped[str] = mapped_column(ForeignKey("cm_challenges.id"), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36))
    answer_hash: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(16))
    result: Mapped[dict] = mapped_column(JSON)

class Project(Base):
    __tablename__ = 'cm_projects'
    owner: Mapped[str] = mapped_column(String(32), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    revision: Mapped[int] = mapped_column(default=0)
    files: Mapped[dict] = mapped_column(JSON)

class ProjectPrivacy(Base):
    __tablename__ = 'cm_project_privacy'
    owner: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    allow_external: Mapped[bool] = mapped_column(default=False)

class ProjectLearningEvent(Base):
    __tablename__ = 'cm_project_learning_events'
    owner: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)


class ProjectLearningState(Base):
    __tablename__ = 'cm_project_learning_state'
    owner: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    path: Mapped[str] = mapped_column(String(160), primary_key=True)
    revision: Mapped[int] = mapped_column(default=0)
    issues: Mapped[list] = mapped_column(JSON)
