from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from .sanitization import clean_text

OpportunityStatus = Literal["Draft", "Published", "Closed", "Archived"]
ApplicationDecision = Literal["Shortlisted", "Accepted", "Rejected"]


class RegisterIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    role: str

    @field_validator("email")
    @classmethod
    def validate_institutional_email_shape(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = clean_text(value)
        if not cleaned:
            raise ValueError("Name is required")
        return cleaned


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: str
    status: str


class TokenOut(BaseModel):
    token: str
    token_type: str = "bearer"


class StudentProfileIn(BaseModel):
    research_experience: str = Field(default="", max_length=10000)
    skills: list[str] = Field(default_factory=list, max_length=100)
    interests: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("research_experience")
    @classmethod
    def clean_experience(cls, value: str) -> str:
        return clean_text(value)

    @field_validator("skills", "interests")
    @classmethod
    def clean_tags(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(clean_text(value)[:100] for value in values if clean_text(value)))
        return cleaned


class FacultyProfileIn(BaseModel):
    bio: str = Field(default="", max_length=10000)
    expertise: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("bio")
    @classmethod
    def clean_bio(cls, value: str) -> str:
        return clean_text(value)

    @field_validator("expertise")
    @classmethod
    def clean_expertise(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(clean_text(value)[:100] for value in values if clean_text(value)))


class OpportunityIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    domain: str = Field(min_length=1, max_length=120)
    duration: str = Field(default="", max_length=120)
    capacity: int = Field(ge=1, le=10000)
    deadline: date | None = None
    required_skills: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("title", "description", "domain", "duration")
    @classmethod
    def sanitize_text(cls, value: str, info: ValidationInfo) -> str:
        cleaned = clean_text(value)
        if info.field_name in {"title", "description", "domain"} and not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned

    @field_validator("required_skills")
    @classmethod
    def sanitize_skills(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(clean_text(value)[:100] for value in values if clean_text(value)))


class ApplyIn(BaseModel):
    motivation: str = Field(min_length=1, max_length=10000)

    @field_validator("motivation")
    @classmethod
    def sanitize_motivation(cls, value: str) -> str:
        cleaned = clean_text(value)
        if not cleaned:
            raise ValueError("Motivation cannot be blank")
        return cleaned


class DecideIn(BaseModel):
    status: ApplicationDecision
    faculty_comment: str = Field(default="", max_length=5000)

    @field_validator("faculty_comment")
    @classmethod
    def sanitize_comment(cls, value: str) -> str:
        return clean_text(value)


class AdminUserPatch(BaseModel):
    status: Literal["Active", "Disabled"] | None = None
    role: Literal["Student", "Faculty", "Coordinator", "Administrator"] | None = None


class ProjectCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20000)
    application_ids: list[int] = Field(min_length=1, max_length=100)

    @field_validator("title", "description")
    @classmethod
    def sanitize_text(cls, value: str, info: ValidationInfo) -> str:
        cleaned = clean_text(value)
        if info.field_name == "title" and not cleaned:
            raise ValueError("Title cannot be blank")
        return cleaned
