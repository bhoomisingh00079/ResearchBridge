"""Member B API slice: project workspace, resources, activity, notices and LORs.

Authentication and project membership use the shared app dependencies. Feature
records currently use an in-process repository until their shared ORM models
and migrations are integrated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
import binascii
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

try:  # support both `uvicorn main:app` from backend/ and `backend.main:app`
    from .project_workspace import (
        ActivityEntry, LocalPrivateStorage, ResourceMetadata, WorkspaceError,
        is_overdue, paginate_activity, utc_now, validate_status_transition,
    )
except ImportError:  # pragma: no cover - exercised by the backend container entry point
    from project_workspace import (
        ActivityEntry, LocalPrivateStorage, ResourceMetadata, WorkspaceError,
        is_overdue, paginate_activity, utc_now, validate_status_transition,
    )

try:
    from app.db import get_db
    from app.deps import current_user
    from app.models import AuditLog, Milestone, Opportunity, Project, ProjectMember, Resource, Task, User
except ImportError:  # package import during local development
    from .app.db import get_db
    from .app.deps import current_user
    from .app.models import AuditLog, Milestone, Opportunity, Project, ProjectMember, Resource, Task, User


router = APIRouter(tags=["Member B"])
_storage = LocalPrivateStorage(os.getenv("PRIVATE_FILE_DIR", "./private-files"))


@dataclass(frozen=True)
class Principal:
    id: int
    role: str


def principal(user: User = Depends(current_user), db: Session = Depends(get_db)) -> Principal:
    """Use the shared auth dependency and synchronize current project membership, milestones, and tasks."""
    memberships = db.query(ProjectMember).all()
    all_users = {item.id: item for item in db.query(User).all()}
    workspace.memberships = {}
    workspace.faculty_by_project = {}
    for membership in memberships:
        workspace.memberships.setdefault(membership.project_id, {})[membership.user_id] = membership.role_in_project
        member = all_users.get(membership.user_id)
        if member and member.role == "Faculty":
            workspace.faculty_by_project.setdefault(membership.project_id, set()).add(member.id)

    # Automatically recognize faculty who created the project's linked opportunity as Lead
    all_projects = db.query(Project).all()
    for proj in all_projects:
        if proj.opportunity_id:
            opp = db.query(Opportunity).filter(Opportunity.id == proj.opportunity_id).first()
            if opp and opp.faculty_id:
                workspace.faculty_by_project.setdefault(proj.id, set()).add(opp.faculty_id)
                workspace.memberships.setdefault(proj.id, {})[opp.faculty_id] = "Lead"

    # Sync database milestones into in-memory workspace
    db_milestones = db.query(Milestone).all()
    for m in db_milestones:
        m_id = m.id
        t_date = m.target_date.isoformat() if hasattr(m.target_date, "isoformat") else str(m.target_date)
        c_at = m.completed_at.isoformat() if m.completed_at and hasattr(m.completed_at, "isoformat") else None
        workspace.milestones[m_id] = {
            "id": m_id,
            "project_id": m.project_id,
            "description": m.description,
            "target_date": t_date,
            "status": m.status,
            "completed_at": c_at,
        }

    # Sync database tasks into in-memory workspace
    db_tasks = db.query(Task).all()
    for t in db_tasks:
        workspace.tasks[t.id] = {
            "id": t.id,
            "milestone_id": t.milestone_id,
            "description": t.description,
            "status": t.status,
            "assigned_to": t.assigned_to,
        }

    # Sync database resources into in-memory workspace
    db_resources = db.query(Resource).all()
    for r in db_resources:
        if r.id not in workspace.resources:
            link = r.storage_reference if (r.storage_reference and (r.storage_reference.startswith("http://") or r.storage_reference.startswith("https://"))) else None
            workspace.resources[r.id] = {
                "id": r.id,
                "project_id": r.project_id,
                "title": r.title,
                "description": r.description or "",
                "type": r.type,
                "storage_reference": r.storage_reference,
                "uploaded_by": r.uploaded_by,
                "created_at": utc_now(),
                "link_url": link,
            }

    # Sync audit log into workspace activity if empty
    if not workspace.activity:
        logs = db.query(AuditLog).filter(AuditLog.project_id.isnot(None)).order_by(AuditLog.timestamp.asc()).all()
        for log in logs:
            workspace.activity.append(
                ActivityEntry(
                    id=log.id,
                    actor=log.user_id,
                    entity=log.entity_type,
                    entity_id=log.entity_id,
                    project_id=log.project_id,
                    action=log.action,
                    timestamp=log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp),
                )
            )

    return Principal(user.id, user.role)


@dataclass
class Workspace:
    # project_id -> user_id -> role_in_project (Lead/Member)
    memberships: dict[int, dict[int, str]] = field(default_factory=dict)
    faculty_by_project: dict[int, set[int]] = field(default_factory=dict)
    resources: dict[int, dict[str, Any]] = field(default_factory=dict)
    milestones: dict[int, dict[str, Any]] = field(default_factory=dict)
    tasks: dict[int, dict[str, Any]] = field(default_factory=dict)
    notifications: dict[int, dict[str, Any]] = field(default_factory=dict)
    letters: dict[int, dict[str, Any]] = field(default_factory=dict)
    activity: list[ActivityEntry] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    def next_id(self, kind: str) -> int:
        self.counters[kind] = self.counters.get(kind, 0) + 1
        return self.counters[kind]

    def member(self, project_id: int, user: Principal) -> bool:
        return user.id in self.memberships.get(project_id, {}) or user.id in self.faculty_by_project.get(project_id, set())

    def require_member(self, project_id: int, user: Principal) -> None:
        if not self.member(project_id, user):
            raise HTTPException(403, "Project membership required")

    def require_lead_or_faculty(self, project_id: int, user: Principal) -> None:
        if self.memberships.get(project_id, {}).get(user.id) != "Lead" and user.id not in self.faculty_by_project.get(project_id, set()):
            raise HTTPException(403, "Project lead or faculty permission required")

    def log(self, actor: int | None, entity: str, entity_id: int, project_id: int | None, action: str) -> None:
        self.activity.append(ActivityEntry(self.next_id("activity"), actor, entity, entity_id, project_id, action, utc_now()))

    def notify(self, user_id: int, kind: str, message: str, related: str) -> int:
        nid = self.next_id("notification")
        self.notifications[nid] = {"id": nid, "user_id": user_id, "type": kind, "message": message,
                                   "related": related, "read": False, "created_at": utc_now()}
        return nid


workspace = Workspace()


def register_project_access(project_id: int, *, members: dict[int, str], faculty_ids: set[int] | None = None) -> None:
    """Integration hook for Member A's project creation/membership service."""
    if any(role not in {"Lead", "Member"} for role in members.values()):
        raise ValueError("Project roles must be Lead or Member")
    workspace.memberships[project_id] = dict(members)
    workspace.faculty_by_project[project_id] = set(faculty_ids or ())


class ResourceIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    type: str = "Link"
    url: HttpUrl | None = None


class ResourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    url: HttpUrl | None = None


class MilestoneIn(BaseModel):
    description: str = Field(min_length=1, max_length=4000)
    target_date: date


class StatusIn(BaseModel):
    status: str


class TaskIn(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    assigned_to: int | None = None


class LetterIn(BaseModel):
    student_id: int
    project_id: int | None = None


class LetterRequestIn(BaseModel):
    faculty_user_id: int
    project_id: int | None = None


class LetterDecision(BaseModel):
    decision: str
    body: str | None = Field(default=None, max_length=20000)


def _translate_workspace_error(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except WorkspaceError as exc:
        raise HTTPException(422, str(exc)) from exc


def _resource_view(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "storage_reference"} | {
        "has_file": bool(item.get("storage_reference"))
    }


@router.post("/projects/{project_id}/resources", status_code=201)
def create_resource(project_id: int, body: ResourceIn, user: Principal = Depends(principal), db: Session = Depends(get_db)):
    workspace.require_member(project_id, user)
    if body.type not in {"Paper", "Dataset", "Link"}:
        raise HTTPException(422, "Use the upload route for file resources")
    if body.type == "Link" and not body.url:
        raise HTTPException(422, "Link resources require a URL")
    storage_ref = str(body.url) if body.url else f"resource-{body.type.lower()}"
    db_res = Resource(
        project_id=project_id,
        title=body.title.strip(),
        description=body.description.strip(),
        type=body.type,
        storage_reference=storage_ref,
        uploaded_by=user.id,
    )
    db.add(db_res)
    db.commit()
    db.refresh(db_res)
    rid = db_res.id
    item = asdict(ResourceMetadata(project_id, body.title.strip(), body.description.strip(), body.type,
                                  None, user.id, utc_now(), str(body.url) if body.url else None))
    item.update(id=rid, link_url=str(body.url) if body.url else None)
    workspace.resources[rid] = item
    workspace.log(user.id, "Resource", rid, project_id, "resource added")
    return {"id": rid}


@router.post("/projects/{project_id}/resources/upload", status_code=201)
async def upload_resource(project_id: int, request: Request, title: str = Query(min_length=1, max_length=200),
                          description: str = "", user: Principal = Depends(principal)):
    workspace.require_member(project_id, user)
    if len(description) > 4000:
        raise HTTPException(422, "Description is too long")
    filename = request.headers.get("X-Filename", "")
    content_type = request.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0].strip()
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > _storage.max_bytes:
            raise HTTPException(413, "File exceeds the configured size limit")
    try:
        reference = _storage.put(filename, bytes(chunks), content_type)
    except WorkspaceError as exc:
        raise HTTPException(422, str(exc)) from exc
    rid = workspace.next_id("resource")
    workspace.resources[rid] = asdict(ResourceMetadata(project_id, title.strip(), description.strip(), "File",
                                                        reference, user.id, utc_now())) | {"id": rid, "link_url": None}
    workspace.log(user.id, "Resource", rid, project_id, "file uploaded")
    return {"id": rid}


@router.get("/projects/{project_id}/resources")
def list_resources(project_id: int, user: Principal = Depends(principal)):
    workspace.require_member(project_id, user)
    return [_resource_view(row) for row in workspace.resources.values() if row["project_id"] == project_id]


@router.put("/resources/{resource_id}")
def update_resource(resource_id: int, body: ResourceUpdate, user: Principal = Depends(principal)):
    row = workspace.resources.get(resource_id)
    if row is None:
        raise HTTPException(404, "Resource not found")
    workspace.require_member(row["project_id"], user)
    if row["uploaded_by"] != user.id and workspace.memberships.get(row["project_id"], {}).get(user.id) != "Lead" and user.id not in workspace.faculty_by_project.get(row["project_id"], set()):
        raise HTTPException(403, "Only the uploader, lead, or faculty may edit this resource")
    updates = body.model_dump(exclude_unset=True)
    if "url" in updates:
        if row["type"] != "Link":
            raise HTTPException(422, "Only link resources have an editable URL")
        row["link_url"] = str(updates.pop("url")) if updates["url"] else None
        if not row["link_url"]:
            raise HTTPException(422, "Link resources require a URL")
    for key, value in updates.items():
        row[key] = value.strip() if isinstance(value, str) else value
    workspace.log(user.id, "Resource", resource_id, row["project_id"], "resource updated")
    return _resource_view(row)


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: int, user: Principal = Depends(principal)):
    row = workspace.resources.get(resource_id)
    if row is None:
        raise HTTPException(404, "Resource not found")
    workspace.require_member(row["project_id"], user)
    if row["uploaded_by"] != user.id and workspace.memberships.get(row["project_id"], {}).get(user.id) != "Lead" and user.id not in workspace.faculty_by_project.get(row["project_id"], set()):
        raise HTTPException(403, "Only the uploader, lead, or faculty may delete this resource")
    workspace.log(user.id, "Resource", resource_id, row["project_id"], "resource removed")
    if row.get("storage_reference"):
        _storage.delete(row["storage_reference"])
    del workspace.resources[resource_id]
    return Response(status_code=204)


@router.get("/resources/{resource_id}/download")
def download_resource(resource_id: int, user: Principal = Depends(principal)):
    row = workspace.resources.get(resource_id)
    if row is None:
        raise HTTPException(404, "Resource not found")
    workspace.require_member(row["project_id"], user)
    if not row.get("storage_reference"):
        raise HTTPException(404, "Resource has no file")
    try:
        data = _storage.get(row["storage_reference"])
    except FileNotFoundError as exc:
        raise HTTPException(404, "Stored file is missing") from exc
    from fastapi.responses import Response as FileResponse
    return FileResponse(content=data, media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{row["title"][:100]}"',
                                 "Cache-Control": "no-store"})


@router.post("/projects/{project_id}/milestones", status_code=201)
def create_milestone(project_id: int, body: MilestoneIn, user: Principal = Depends(principal), db: Session = Depends(get_db)):
    workspace.require_member(project_id, user)
    workspace.require_lead_or_faculty(project_id, user)
    try:
        t_date = datetime.strptime(body.target_date, "%Y-%m-%d").date()
    except Exception:
        t_date = datetime.now(timezone.utc).date()
    db_m = Milestone(project_id=project_id, description=body.description.strip(), target_date=t_date, status="Not Started")
    db.add(db_m)
    db.commit()
    db.refresh(db_m)
    mid = db_m.id
    workspace.milestones[mid] = {"id": mid, "project_id": project_id, "description": body.description.strip(),
                                 "target_date": body.target_date, "status": "Not Started", "completed_at": None}
    workspace.log(user.id, "Milestone", mid, project_id, "milestone created")
    return {"id": mid}


@router.get("/projects/{project_id}/milestones")
def list_milestones(project_id: int, user: Principal = Depends(principal)):
    workspace.require_member(project_id, user)
    rows = [item for item in workspace.milestones.values() if item["project_id"] == project_id]
    rows.sort(key=lambda item: (item["target_date"], item["id"]))
    return rows


@router.get("/milestones/{milestone_id}/tasks")
def list_tasks(milestone_id: int, user: Principal = Depends(principal)):
    milestone = workspace.milestones.get(milestone_id)
    if milestone is None:
        raise HTTPException(404, "Milestone not found")
    workspace.require_member(milestone["project_id"], user)
    return [item for item in workspace.tasks.values() if item["milestone_id"] == milestone_id]


@router.patch("/milestones/{milestone_id}")
def update_milestone(milestone_id: int, body: StatusIn, user: Principal = Depends(principal), db: Session = Depends(get_db)):
    item = workspace.milestones.get(milestone_id)
    if item is None:
        raise HTTPException(404, "Milestone not found")
    workspace.require_member(item["project_id"], user)
    item["status"] = _translate_workspace_error(validate_status_transition, item["status"], body.status)
    item["completed_at"] = utc_now() if item["status"] == "Completed" else None
    db_m = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if db_m:
        db_m.status = item["status"]
        if item["status"] == "Completed":
            db_m.completed_at = datetime.now(timezone.utc)
        else:
            db_m.completed_at = None
        db.commit()
    workspace.log(user.id, "Milestone", milestone_id, item["project_id"], f"status changed to {item['status']}")
    return {"status": item["status"], "completed_at": item["completed_at"]}


@router.post("/milestones/{milestone_id}/tasks", status_code=201)
def create_task(milestone_id: int, body: TaskIn, user: Principal = Depends(principal)):
    milestone = workspace.milestones.get(milestone_id)
    if milestone is None:
        raise HTTPException(404, "Milestone not found")
    project_id = milestone["project_id"]
    workspace.require_member(project_id, user)
    if body.assigned_to is not None and body.assigned_to not in workspace.memberships.get(project_id, {}):
        raise HTTPException(422, "Task assignee must be a project member")
    task_id = workspace.next_id("task")
    workspace.tasks[task_id] = {"id": task_id, "milestone_id": milestone_id, "description": body.description.strip(),
                                "status": "Not Started", "assigned_to": body.assigned_to}
    workspace.log(user.id, "Task", task_id, project_id, "task created")
    return {"id": task_id}


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, body: StatusIn, user: Principal = Depends(principal)):
    item = workspace.tasks.get(task_id)
    if item is None:
        raise HTTPException(404, "Task not found")
    milestone = workspace.milestones[item["milestone_id"]]
    workspace.require_member(milestone["project_id"], user)
    item["status"] = _translate_workspace_error(validate_status_transition, item["status"], body.status)
    workspace.log(user.id, "Task", task_id, milestone["project_id"], f"status changed to {item['status']}")
    return {"status": item["status"]}


@router.get("/projects/{project_id}/milestones/overdue")
def overdue_milestones(project_id: int, user: Principal = Depends(principal)):
    workspace.require_member(project_id, user)
    return [{"id": item["id"], "description": item["description"], "target_date": item["target_date"], "status": item["status"]}
            for item in workspace.milestones.values() if item["project_id"] == project_id and
            _translate_workspace_error(is_overdue, item["target_date"], item["status"])]


@router.get("/projects/{project_id}/activity")
def project_activity(project_id: int, page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
                     user: Principal = Depends(principal)):
    workspace.require_member(project_id, user)
    rows = paginate_activity((row for row in workspace.activity if row.project_id == project_id), page=page, page_size=page_size)
    total = sum(row.project_id == project_id for row in workspace.activity)
    return {"items": [asdict(row) for row in rows], "page": page, "page_size": page_size,
            "total": total, "has_more": page * page_size < total}


@router.get("/notifications")
def my_notifications(user: Principal = Depends(principal), unread_only: bool = False):
    rows = [row for row in workspace.notifications.values() if row["user_id"] == user.id and (not unread_only or not row["read"])]
    rows.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
    return rows


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: Principal = Depends(principal)):
    item = workspace.notifications.get(notification_id)
    if item is None or item["user_id"] != user.id:
        raise HTTPException(404, "Notification not found")
    item["read"] = True
    return {"ok": True}


def run_reminder_job(*, today: date | None = None, reminder_days: int | None = None) -> int:
    """Re-check current milestone state before creating reminder notifications."""
    today = today or date.today()
    window = reminder_days if reminder_days is not None else int(os.getenv("REMINDER_DAYS", "3"))
    if window < 0:
        raise ValueError("REMINDER_DAYS must be non-negative")
    count = 0
    for item in workspace.milestones.values():
        # Re-read from the current repository on each run; completed work is suppressed.
        if item["status"] == "Completed":
            continue
        days = (item["target_date"] - today).days
        if days < 0:
            label = "overdue"
        elif days <= window:
            label = "due soon"
        else:
            continue
        project_id = item["project_id"]
        recipients = set(workspace.memberships.get(project_id, {})) | workspace.faculty_by_project.get(project_id, set())
        for uid in recipients:
            related = f"milestone:{item['id']}:{label}:{today.isoformat()}"
            if any(n["user_id"] == uid and n["related"] == related for n in workspace.notifications.values()):
                continue
            workspace.notify(uid, "Milestone Reminder", f"Milestone '{item['description']}' is {label}.", related)
            count += 1
    return count


@router.post("/jobs/reminders")
def trigger_reminders(user: Principal = Depends(principal)):
    if user.role != "Administrator":
        raise HTTPException(403, "Administrator role required")
    return {"created": run_reminder_job()}


@router.post("/lor/issue", status_code=201)
def issue_letter(body: LetterIn, user: Principal = Depends(principal)):
    if user.role != "Faculty":
        raise HTTPException(403, "Faculty role required")
    candidates = [pid for pid, members in workspace.memberships.items()
                  if body.student_id in members and user.id in workspace.faculty_by_project.get(pid, set())]
    project_id = body.project_id if body.project_id is not None else (candidates[0] if candidates else None)
    if project_id is None or project_id not in candidates:
        raise HTTPException(403, "Recommendation letters require shared project history")
    lid = workspace.next_id("letter")
    workspace.letters[lid] = {"id": lid, "faculty_user_id": user.id, "student_user_id": body.student_id,
                              "project_id": project_id, "status": "Issued", "requested_at": None,
                              "decided_at": utc_now(), "body": ""}
    workspace.log(user.id, "RecommendationLetter", lid, project_id, "recommendation letter issued")
    workspace.notify(body.student_id, "Recommendation Letter", "A faculty member issued you a recommendation letter.", f"lor:{lid}")
    return {"id": lid, "status": "Issued"}


@router.post("/lor/request", status_code=201)
def request_letter(body: LetterRequestIn, user: Principal = Depends(principal)):
    if user.role != "Student":
        raise HTTPException(403, "Student role required")
    project_id = body.project_id
    candidates = [pid for pid, members in workspace.memberships.items() if user.id in members and
                  body.faculty_user_id in workspace.faculty_by_project.get(pid, set()) and
                  (project_id is None or pid == project_id)]
    if not candidates:
        raise HTTPException(403, "No shared project history for this request")
    pid = candidates[0]
    if any(letter["status"] == "Requested" and letter["student_user_id"] == user.id and
           letter["faculty_user_id"] == body.faculty_user_id for letter in workspace.letters.values()):
        raise HTTPException(409, "A pending request already exists")
    lid = workspace.next_id("letter")
    workspace.letters[lid] = {"id": lid, "faculty_user_id": body.faculty_user_id, "student_user_id": user.id,
                              "project_id": pid, "status": "Requested", "requested_at": utc_now(),
                              "decided_at": None, "body": ""}
    workspace.log(user.id, "RecommendationLetter", lid, pid, "recommendation letter requested")
    workspace.notify(body.faculty_user_id, "Recommendation Letter Request", "A student requested a recommendation letter.", f"lor:{lid}")
    return {"id": lid, "status": "Requested"}


@router.get("/lor/mine")
def my_letters(user: Principal = Depends(principal)):
    rows = [letter for letter in workspace.letters.values() if user.id in {letter["faculty_user_id"], letter["student_user_id"]}]
    return sorted(rows, key=lambda row: row["id"], reverse=True)


@router.get("/lor/{letter_id}/summary")
def letter_summary(letter_id: int, user: Principal = Depends(principal)):
    item = workspace.letters.get(letter_id)
    if item is None:
        raise HTTPException(404, "Recommendation letter not found")
    if user.id not in {item["faculty_user_id"], item["student_user_id"]}:
        raise HTTPException(403, "Letter participants only")
    project_id = item["project_id"]
    milestones = [m for m in workspace.milestones.values() if project_id is not None and m["project_id"] == project_id]
    tasks = [t for t in workspace.tasks.values() if any(m["id"] == t["milestone_id"] for m in milestones)]
    return {"letter": item, "project_id": project_id, "milestones": {"total": len(milestones),
            "completed": sum(m["status"] == "Completed" for m in milestones)}, "tasks": {"total": len(tasks),
            "completed": sum(t["status"] == "Completed" for t in tasks)}}


@router.post("/lor/{letter_id}/decide")
def decide_letter(letter_id: int, body: LetterDecision, user: Principal = Depends(principal)):
    item = workspace.letters.get(letter_id)
    if item is None:
        raise HTTPException(404, "Recommendation letter not found")
    if item["faculty_user_id"] != user.id or user.role != "Faculty":
        raise HTTPException(403, "Only the requested faculty member may decide")
    if item["status"] != "Requested":
        raise HTTPException(409, "Request has already been decided")
    if body.decision not in {"Issued", "Declined"}:
        raise HTTPException(422, "Decision must be Issued or Declined")
    if body.decision == "Issued" and not (body.body or "").strip():
        raise HTTPException(422, "An issued letter requires its contents")
    item.update(status=body.decision, body=(body.body or "").strip(), decided_at=utc_now())
    workspace.log(user.id, "RecommendationLetter", letter_id, item["project_id"], f"request {body.decision.lower()}")
    message = "Your recommendation letter was issued." if body.decision == "Issued" else "Your recommendation letter request was declined."
    workspace.notify(item["student_user_id"], "Recommendation Letter", message, f"lor:{letter_id}")
    return {"id": letter_id, "status": item["status"]}
