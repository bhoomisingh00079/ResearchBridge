"""Idempotently seed the shared skill vocabulary for local/initial deployments."""

from sqlalchemy import select

from .db import SessionLocal
from .models import Skill

DEFAULT_SKILLS = {
    "Python": "Programming", "R": "Programming", "Java": "Programming", "SQL": "Data",
    "Statistics": "Methods", "Machine Learning": "Data Science", "Artificial Intelligence": "Data Science",
    "Data Visualization": "Data", "Literature Review": "Research Methods", "Survey Design": "Research Methods",
}


def seed_skills() -> int:
    created = 0
    with SessionLocal() as session:
        existing = {name for (name,) in session.execute(select(Skill.name)).all()}
        for name, category in DEFAULT_SKILLS.items():
            if name not in existing:
                session.add(Skill(name=name, category=category))
                created += 1
        session.commit()
    return created


if __name__ == "__main__":
    print(f"Seeded {seed_skills()} skills.")
