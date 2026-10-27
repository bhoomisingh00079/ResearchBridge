"""Securely bootstrap the first administrator from an interactive terminal."""

import getpass
import re
import sys

from sqlalchemy import func

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import User
from .security import hash_password


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python -m app.create_admin <institutional-email> <full-name>", file=sys.stderr)
        return 2
    email, name = sys.argv[1].strip().casefold(), sys.argv[2].strip()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        print("A valid institutional email is required.", file=sys.stderr)
        return 2
    if not get_settings().allows_domain(email.rsplit("@", 1)[-1]):
        print("Administrator email domain is not allowed by ALLOWED_DOMAINS.", file=sys.stderr)
        return 2
    password = getpass.getpass("Administrator password (minimum 12 characters): ")
    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 2
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        if session.query(func.count(User.id)).filter(User.role == "Administrator").scalar():
            print("An administrator already exists; use the admin API to assign additional roles.", file=sys.stderr)
            return 1
        if session.query(User.id).filter(User.email == email).first():
            print("That email is already registered.", file=sys.stderr)
            return 1
        session.add(User(email=email, password_hash=hash_password(password), name=name,
                         role="Administrator", status="Active"))
        session.commit()
    print(f"Administrator account created for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
