"""audit.py — one-liner to append a governance/audit-trail entry."""
from sqlalchemy.orm import Session

from app.models import AuditLog


def record(db: Session, entity: str, entity_id: int | None, action: str,
           user: str = "steward", before: dict | None = None,
           after: dict | None = None) -> AuditLog:
    entry = AuditLog(entity=entity, entity_id=entity_id, action=action,
                     user=user, before=before, after=after)
    db.add(entry)
    return entry
