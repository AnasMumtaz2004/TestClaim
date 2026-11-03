import json
import hashlib
from datetime import timezone
from sqlalchemy import desc
from app.models import AuditLog, utc_now


def clean_time(dt):
    """Convert datetime to UTC and make it naive."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def hash_row(prev_hash, created_at, actor, action, claim_id, payload):
    """Compute SHA256 hash of audit row fields."""
    parts = [
        prev_hash,
        clean_time(created_at).isoformat(),
        actor,
        action,
        claim_id or "",
        json.dumps(payload, sort_keys=True, default=str),
    ]
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()


def add_audit(db, actor, action, claim_id=None, payload=None):
    """Add an audit log entry to the chain."""
    if payload is None:
        payload = {}
    
    last = db.query(AuditLog).order_by(desc(AuditLog.id)).first()
    prev_hash = last.row_hash if last else ""
    
    created_at = utc_now()
    row_hash = hash_row(prev_hash, created_at, actor, action, claim_id, payload)
    
    entry = AuditLog(
        created_at=created_at,
        actor=actor,
        action=action,
        claim_id=claim_id,
        payload=payload,
        prev_hash=prev_hash,
        row_hash=row_hash,
    )
    db.add(entry)
    db.flush()
    return entry


def verify_chain(db):
    """Verify the integrity of the audit chain."""
    rows = db.query(AuditLog).order_by(AuditLog.id).all()
    
    prev_hash = ""
    for row in rows:
        expected = hash_row(prev_hash, row.created_at, row.actor, row.action, row.claim_id, row.payload)
        if expected != row.row_hash:
            return (False, row.id)
        prev_hash = row.row_hash
    
    return (True, None)
