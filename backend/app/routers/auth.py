import re
import json

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..deps import current_user
from ..models import FacultyProfile, StudentInterest, StudentProfile, StudentSkill, User
from ..schemas import FacultyProfileIn, LoginIn, RegisterIn, StudentProfileIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, new_verification_token, verify_password
from ..services.email import send_verification_email

router = APIRouter(tags=["identity"])


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    settings = get_settings()
    if body.role not in {"Student", "Faculty"} or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", body.email):
        raise HTTPException(status_code=400, detail="Registration failed")
    domain = body.email.rsplit("@", 1)[-1]
    if not settings.allows_domain(domain):
        raise HTTPException(status_code=400, detail="Registration failed")
    user = User(email=body.email, password_hash=hash_password(body.password), name=body.name,
                role=body.role, status="Pending Verification", verify_token=new_verification_token(),
                verify_expires_at=datetime.now(timezone.utc) + timedelta(hours=24))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Registration failed") from None
    db.refresh(user)
    result = UserOut.model_validate(user).model_dump()
    if settings.smtp_host or settings.is_production:
        background_tasks.add_task(send_verification_email, user.email, user.name, user.verify_token)
    if not settings.is_production:
        result["dev_verify_token"] = user.verify_token
    return result


@router.post("/auth/verify/{token}")
def verify_account(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verify_token == token).first()
    if user is None or (user.verify_expires_at is not None and
                        user.verify_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)):
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user.status = "Active"
    user.verify_token = None
    user.verify_expires_at = None
    db.commit()
    return {"verified": True}


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().casefold()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.password_hash) or user.status != "Active":
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_access_token(user.id, user.role)}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


def _profile_tags(profile, relationship_name: str, value_name: str) -> list[str]:
    return [getattr(item, value_name) for item in getattr(profile, relationship_name)]


@router.put("/profile/student")
def update_student_profile(body: StudentProfileIn, user: User = Depends(current_user),
                           db: Session = Depends(get_db)):
    if user.role != "Student":
        raise HTTPException(status_code=403, detail="Student role required")
    profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
    profile.research_experience = body.research_experience
    profile.skills.clear()
    profile.skills.extend(StudentSkill(skill_name=value) for value in body.skills)
    profile.interests.clear()
    profile.interests.extend(StudentInterest(interest=value) for value in body.interests)
    db.commit()
    db.refresh(profile)
    return {"user_id": user.id, "research_experience": profile.research_experience,
            "skills": _profile_tags(profile, "skills", "skill_name"),
            "interests": _profile_tags(profile, "interests", "interest")}


@router.get("/profile/student")
def get_student_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "Student":
        raise HTTPException(status_code=403, detail="Student role required")
    profile = db.query(StudentProfile).filter_by(user_id=user.id).first()
    return {"user_id": user.id, "research_experience": profile.research_experience if profile else "",
            "skills": _profile_tags(profile, "skills", "skill_name") if profile else [],
            "interests": _profile_tags(profile, "interests", "interest") if profile else []}


@router.put("/profile/faculty")
def update_faculty_profile(body: FacultyProfileIn, user: User = Depends(current_user),
                           db: Session = Depends(get_db)):
    if user.role != "Faculty":
        raise HTTPException(status_code=403, detail="Faculty role required")
    profile = db.query(FacultyProfile).filter_by(user_id=user.id).first()
    if profile is None:
        profile = FacultyProfile(user_id=user.id)
        db.add(profile)
    profile.bio = body.bio
    profile.expertise = json.dumps(body.expertise)
    db.commit()
    db.refresh(profile)
    return {"user_id": user.id, "bio": profile.bio, "expertise": json.loads(profile.expertise or "[]")}


@router.get("/profile/faculty")
def get_faculty_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "Faculty":
        raise HTTPException(status_code=403, detail="Faculty role required")
    profile = db.query(FacultyProfile).filter_by(user_id=user.id).first()
    return {"user_id": user.id, "bio": profile.bio if profile else "",
            "expertise": json.loads(profile.expertise or "[]") if profile else []}


@router.get("/skills")
def list_skills(q: str | None = None, db: Session = Depends(get_db)):
    from ..models import Skill
    query = db.query(Skill)
    if q:
        query = query.filter(Skill.name.ilike(f"%{q[:100]}%"))
    return [{"id": skill.id, "name": skill.name, "category": skill.category}
            for skill in query.order_by(Skill.name).limit(200).all()]
