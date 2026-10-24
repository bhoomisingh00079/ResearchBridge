"""SQLAlchemy models for ResearchBridge (SRS 6.1, Appendix H, PLAN Section 3)."""
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # Student, Faculty, Coordinator, Administrator
    status = Column(String(50), nullable=False, default="Active")  # Pending Verification, Active, Disabled
    verify_token = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role IN ('Student', 'Faculty', 'Coordinator', 'Administrator')",
            name="check_user_role",
        ),
        CheckConstraint(
            "status IN ('Pending Verification', 'Active', 'Disabled')",
            name="check_user_status",
        ),
    )

    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)
    faculty_profile = relationship("FacultyProfile", back_populates="user", uselist=False)
    recommendations = relationship("AgentRecommendation", back_populates="user")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(100), nullable=True)


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    research_experience = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="student_profile")
    skills = relationship("StudentSkill", back_populates="profile", cascade="all, delete-orphan")
    interests = relationship("StudentInterest", back_populates="profile", cascade="all, delete-orphan")


class StudentSkill(Base):
    __tablename__ = "student_skills"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    skill_name = Column(String(100), nullable=False)

    profile = relationship("StudentProfile", back_populates="skills")


class StudentInterest(Base):
    __tablename__ = "student_interests"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    interest = Column(String(100), nullable=False)

    profile = relationship("StudentProfile", back_populates="interests")


class FacultyProfile(Base):
    __tablename__ = "faculty_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    bio = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="faculty_profile")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    faculty_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    domain = Column(String(100), nullable=False)
    duration = Column(String(100), nullable=True)
    capacity = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="Draft")  # Draft, Published, Closed, Archived
    deadline = Column(Date, nullable=True)
    published_at = Column(DateTime, nullable=True)
    requirements_version = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint("capacity >= 1", name="check_capacity_positive"),
        CheckConstraint("status IN ('Draft', 'Published', 'Closed', 'Archived')", name="check_opp_status"),
    )

    required_skills = relationship("OpportunitySkill", back_populates="opportunity", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="opportunity")


class OpportunitySkill(Base):
    __tablename__ = "opp_skills"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    skill_name = Column(String(100), nullable=False)

    opportunity = relationship("Opportunity", back_populates="required_skills")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    motivation = Column(Text, nullable=True)
    profile_snapshot = Column(Text, nullable=True)
    req_version = Column(Integer, default=1)
    status = Column(String(50), nullable=False, default="Submitted")  # Submitted, Shortlisted, Accepted, Rejected, Withdrawn
    faculty_comment = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    decided_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('Submitted', 'Shortlisted', 'Accepted', 'Rejected', 'Withdrawn')",
            name="check_application_status",
        ),
    )

    opportunity = relationship("Opportunity", back_populates="applications")
    student = relationship("User", foreign_keys=[student_id])


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    domain = Column(String(100), nullable=False, default="General")
    status = Column(String(50), nullable=False, default="Active")  # Active, Completed, On Hold
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('Active', 'Completed', 'On Hold')", name="check_project_status"),
    )

    members = relationship("ProjectMember", back_populates="project")
    milestones = relationship("Milestone", back_populates="project")
    resources = relationship("Resource", back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_in_project = Column(String(50), nullable=False, default="Member")  # Lead, Member
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        CheckConstraint("role_in_project IN ('Lead', 'Member')", name="check_member_role"),
    )

    project = relationship("Project", back_populates="members")
    user = relationship("User")


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=False)
    target_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default="Not Started")  # Not Started, In Progress, Completed, Blocked
    completed_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('Not Started', 'In Progress', 'Completed', 'Blocked')", name="check_milestone_status"),
    )

    project = relationship("Project", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="Not Started")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    milestone = relationship("Milestone", back_populates="tasks")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)  # Paper, Dataset, Link, File
    storage_reference = Column(String(500), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        CheckConstraint("type IN ('Paper', 'Dataset', 'Link', 'File')", name="check_resource_type"),
    )

    project = relationship("Project", back_populates="resources")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    related = Column(String(255), nullable=True)
    read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class AgentRecommendation(Base):
    """Stores agent recommendations with unique constraint preventing duplicate recreation (FR-031)."""
    __tablename__ = "agent_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(100), nullable=False)  # opportunity, collaborator, resource, alert
    reference_entity = Column(String(255), nullable=False)  # e.g., "opportunity:7", "candidate:5", "milestone:1"
    reason_text = Column(Text, nullable=False)
    score = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="Active")  # Active, Dismissed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "type", "reference_entity", name="uq_user_agent_rec"),
        CheckConstraint("status IN ('Active', 'Dismissed')", name="check_agent_rec_status"),
    )

    user = relationship("User", back_populates="recommendations")


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    action = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
