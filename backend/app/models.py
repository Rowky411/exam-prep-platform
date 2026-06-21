import uuid
from sqlalchemy import Boolean, Column, Index, Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Integer, nullable=False, default=1)
    type = Column(Text, nullable=False)  # single_mcq | multi_mcq | true_false | numerical
    subject = Column(Text, nullable=False)
    chapter = Column(Text, nullable=False)
    topic = Column(Text, nullable=False)
    difficulty = Column(Integer, nullable=False)  # 1–5
    exam_tag = Column(Text, nullable=False)       # HSC | BCS | admission
    stem = Column(Text, nullable=False)            # Markdown + LaTeX
    options = Column(JSONB)                        # [{id, text}] — null for numerical
    correct = Column(JSONB, nullable=False)
    explanation = Column(Text)
    media = Column(JSONB)
    language = Column(Text, nullable=False, default="en")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_questions_taxonomy", "subject", "chapter", "topic", "difficulty", "exam_tag"),
    )


class Test(Base):
    __tablename__ = "tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    question_ids = Column(JSONB, nullable=False)  # ordered list of question UUIDs
    filters = Column(JSONB)                        # the assembly filters used
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)
    test_id = Column(UUID(as_uuid=True), nullable=True)
    question_id = Column(UUID(as_uuid=True), nullable=False)
    question_version = Column(Integer, nullable=False)
    selected = Column(JSONB, nullable=False)      # user's answer
    is_correct = Column(Boolean, nullable=True)   # NULL until scored
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    scored_at = Column(DateTime(timezone=True), nullable=True)


class UserStats(Base):
    __tablename__ = "user_stats"

    user_id = Column(Text, primary_key=True)
    total_attempted = Column(Integer, nullable=False, default=0)
    total_correct = Column(Integer, nullable=False, default=0)
    accuracy_by_topic = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
