"""Safety and Invariant Verification Tests (Task C6: FR-030, SRS 5.2).

Guarantees:
  1. The agent service and agent scan routines NEVER alter applications.status or project_members.
     Autonomous agent decisions are prohibited (SRS 1.4.1, FR-030, BR-005).
  2. Static architectural check: agent_service has zero database drivers, imports, or credentials.
"""
import ast
import os
import pathlib
import pytest

from app.jobs.agent_scan import run_agent_scans
from app.models import Application, Opportunity, Project, ProjectMember
from .conftest import make_user


class TestAgentSafetyInvariants:
    """FR-030 / BR-005: Agent scans must leave applications.status and project_members unchanged."""

    def test_agent_scan_cannot_modify_applications_or_members(self, db):
        fac = make_user(db, "safety_fac@ves.ac.in", "Faculty")
        stud1 = make_user(db, "safety_s1@ves.ac.in", "Student")
        stud2 = make_user(db, "safety_s2@ves.ac.in", "Student")

        opp = Opportunity(
            faculty_id=fac.id,
            title="Safety Invariant Opp",
            description="Testing safety",
            domain="AI",
            capacity=2,
            status="Published",
        )
        db.add(opp)
        db.commit()

        app1 = Application(student_id=stud1.id, opportunity_id=opp.id, status="Submitted")
        app2 = Application(student_id=stud2.id, opportunity_id=opp.id, status="Shortlisted")
        db.add_all([app1, app2])

        project = Project(title="Safety Project", domain="AI", status="Active")
        db.add(project)
        db.commit()

        member1 = ProjectMember(project_id=project.id, user_id=stud1.id, role_in_project="Member")
        db.add(member1)
        db.commit()

        # Capture state before scan
        before_apps = {
            a.id: (a.status, a.faculty_comment, a.decided_at)
            for a in db.query(Application).all()
        }
        before_members = {
            (m.project_id, m.user_id): m.role_in_project
            for m in db.query(ProjectMember).all()
        }

        # Execute agent scan routine
        run_agent_scans(db)

        # Re-fetch and assert complete immutability
        after_apps = {
            a.id: (a.status, a.faculty_comment, a.decided_at)
            for a in db.query(Application).all()
        }
        after_members = {
            (m.project_id, m.user_id): m.role_in_project
            for m in db.query(ProjectMember).all()
        }

        assert before_apps == after_apps, "CRITICAL: Agent scan modified application state!"
        assert before_members == after_members, "CRITICAL: Agent scan modified project membership!"


class TestAgentServiceStaticCheck:
    """Static check verifying agent_service has no DB drivers or connection strings (PLAN C6, SRS 5.2)."""

    FORBIDDEN_MODULES = {
        "sqlite3",
        "psycopg2",
        "asyncpg",
        "sqlalchemy",
        "databases",
        "tortoise",
        "peewee",
        "pymysql",
        "mysql",
        "pymongo",
        "motor",
    }

    FORBIDDEN_STRINGS = [
        "postgresql://",
        "postgres://",
        "sqlite://",
        "mysql://",
        "mongodb://",
        "DATABASE_URL",
    ]

    def test_no_database_imports_in_agent_service(self):
        root_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "agent_service"
        py_files = list(root_dir.glob("**/*.py"))

        # Must inspect at least one file
        assert len(py_files) > 0, f"No Python files found in {root_dir}"

        for py_path in py_files:
            content = py_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_path))

            for node in ast.walk(tree):
                # Check `import X`
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split(".")[0]
                        assert top_pkg not in self.FORBIDDEN_MODULES, (
                            f"Prohibited DB driver import '{alias.name}' detected in {py_path.name}"
                        )
                # Check `from X import Y`
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top_pkg = node.module.split(".")[0]
                        assert top_pkg not in self.FORBIDDEN_MODULES, (
                            f"Prohibited DB driver import from '{node.module}' detected in {py_path.name}"
                        )

            # Check raw string tokens
            for forbidden_str in self.FORBIDDEN_STRINGS:
                assert forbidden_str not in content, (
                    f"Prohibited database connection pattern '{forbidden_str}' found in {py_path.name}"
                )
