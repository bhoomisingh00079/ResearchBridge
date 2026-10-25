from fastapi import APIRouter, Depends, HTTPException
import json
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_roles
from ..models import AuditLog, User
from ..schemas import AdminUserPatch

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/users")
def list_users(offset: int = 0, limit: int = 50, _admin: User = Depends(require_roles("Administrator")),
               db: Session = Depends(get_db)):
    if offset < 0 or limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    rows = db.query(User).order_by(User.id).offset(offset).limit(limit).all()
    return [{"id": row.id, "email": row.email, "name": row.name,
             "role": row.role, "status": row.status, "created_at": row.created_at.isoformat()} for row in rows]


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: AdminUserPatch,
                admin: User = Depends(require_roles("Administrator")), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one field is required")
    if target.id == admin.id and changes.get("status") == "Disabled":
        raise HTTPException(status_code=409, detail="You cannot disable your own account")
    before = {key: getattr(target, key) for key in changes}
    for key, value in changes.items():
        if value is not None:
            setattr(target, key, value)
    db.add(AuditLog(actor_user_id=admin.id, entity_type="user", entity_id=target.id,
                    action="admin_updated", detail={"before": before, "after": changes}))
    db.commit()
    return {"id": target.id, "email": target.email, "name": target.name,
            "role": target.role, "status": target.status}


@router.get("/audit")
def audit_log(offset: int = 0, limit: int = 100,
              _admin: User = Depends(require_roles("Administrator")), db: Session = Depends(get_db)):
    if offset < 0 or limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    rows = db.query(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).offset(offset).limit(limit).all()
    return [{"id": row.id, "actor_user_id": row.actor_user_id, "entity_type": row.entity_type,
             "entity_id": row.entity_id, "project_id": row.project_id, "action": row.action,
             "detail": row.detail or {}, "timestamp": row.timestamp.isoformat()} for row in rows]
