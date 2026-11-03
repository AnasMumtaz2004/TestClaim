from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models import get_db, User, Claim, Policy, ClaimDocument, ClaimMessage
from app.api.auth import require_customer
from app.core.documents import check_file, save_upload, BLUR_THRESHOLD
from app.core.governance import add_audit
from app.core.email_service import send_claim_received

router = APIRouter(prefix="/customer", dependencies=[Depends(require_customer)])

DOC_TYPES = [
    "photo_front",
    "photo_rear",
    "photo_left",
    "photo_right",
    "photo_closeup",
    "estimate",
    "police_report",
    "discharge_summary",
    "bill",
    "other",
]


def as_utc(dt):
    """Ensure datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_own_claim(db, claim_id, user):
    """Get a claim that belongs to this customer or raise 404."""
    claim = db.query(Claim).filter(Claim.id == claim_id, Claim.claimant_id == user.id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return claim


def claim_to_dict(claim):
    """Convert a claim to a dictionary."""
    return {
        "id": claim.id,
        "claim_number": claim.claim_number,
        "line": claim.line,
        "status": claim.status,
        "loss_date": claim.loss_date.isoformat(),
        "claimed_amount": float(claim.claimed_amount),
        "description": claim.description,
        "policy_id": claim.policy_id,
        "created_at": as_utc(claim.created_at).isoformat(),
    }


def policy_to_dict(policy):
    """Convert a policy to a dictionary."""
    return {
        "id": policy.id,
        "policy_number": policy.policy_number,
        "line": policy.line,
        "product": policy.product,
        "sum_insured": float(policy.sum_insured),
        "start_date": policy.start_date.isoformat(),
        "end_date": policy.end_date.isoformat(),
    }


def document_to_dict(doc):
    """Convert a document to a dictionary."""
    retake = False
    if doc.doc_type.startswith("photo") and doc.quality_score is not None:
        if doc.quality_score < BLUR_THRESHOLD:
            retake = True
    
    return {
        "id": doc.id,
        "claim_id": doc.claim_id,
        "doc_type": doc.doc_type,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "quality_score": float(doc.quality_score) if doc.quality_score is not None else None,
        "retake": retake,
        "uploaded_at": as_utc(doc.uploaded_at).isoformat(),
    }


def message_to_dict(msg):
    """Convert a message to a dictionary."""
    return {
        "id": msg.id,
        "claim_id": msg.claim_id,
        "sender_role": msg.sender_role,
        "body": msg.body,
        "created_at": as_utc(msg.created_at).isoformat(),
    }


class ClaimCreate(BaseModel):
    policy_id: str
    loss_date: datetime
    claimed_amount: float = Field(gt=0)
    description: str = Field(default="", max_length=2000)


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


@router.get("/policies")
def get_customer_policies(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    """Get all policies for the current customer."""
    policies = db.query(Policy).filter(Policy.owner_id == user.id).all()
    return [policy_to_dict(p) for p in policies]


@router.get("/claims")
def get_customer_claims(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    """Get all claims for the current customer."""
    claims = db.query(Claim).filter(Claim.claimant_id == user.id).all()
    return [claim_to_dict(c) for c in claims]


@router.get("/claims/{claim_id}")
def get_customer_claim(claim_id: str, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    """Get one claim for the current customer."""
    claim = get_own_claim(db, claim_id, user)
    return claim_to_dict(claim)


@router.post("/claims")
def create_claim(body: ClaimCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    """File a new claim."""
    policy = db.query(Policy).filter(Policy.id == body.policy_id, Policy.owner_id == user.id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    
    now = datetime.now(timezone.utc)
    if body.loss_date > now:
        raise HTTPException(status_code=400, detail="Loss date cannot be in the future.")
    
    policy_start = as_utc(policy.start_date)
    policy_end = as_utc(policy.end_date)
    if body.loss_date < policy_start or body.loss_date > policy_end:
        raise HTTPException(status_code=400, detail="Loss date is outside the policy period.")
    
    year = now.year
    count = db.query(func.count(Claim.id)).scalar()
    claim_number = f"CLM-{year}-{count + 1:04d}"
    
    claim = Claim(
        claim_number=claim_number,
        policy_id=policy.id,
        claimant_id=user.id,
        line=policy.line,
        status="submitted",
        loss_date=body.loss_date,
        claimed_amount=Decimal(str(body.claimed_amount)),
        description=body.description,
    )
    db.add(claim)
    db.flush()
    
    add_audit(
        db,
        user.id,
        "claim_filed",
        claim.id,
        {
            "claim_number": claim_number,
            "policy_id": policy.id,
            "loss_date": body.loss_date.isoformat(),
            "claimed_amount": str(body.claimed_amount),
        },
    )
    db.commit()
    
    send_claim_received(db, user, claim, policy.policy_number)
    db.commit()
    
    return claim_to_dict(claim)


@router.get("/claims/{claim_id}/documents")
def get_claim_documents(claim_id: str, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    """Get all documents for a claim."""
    claim = get_own_claim(db, claim_id, user)
    docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).order_by(desc(ClaimDocument.uploaded_at)).all()
    return [document_to_dict(d) for d in docs]


@router.post("/claims/{claim_id}/documents")
def upload_document(
    claim_id: str,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Upload a document to a claim."""
    from app.config import settings
    
    claim = get_own_claim(db, claim_id, user)
    
    if doc_type not in DOC_TYPES:
        raise HTTPException(status_code=400, detail="Unknown document type.")
    
    doc_count = db.query(func.count(ClaimDocument.id)).filter(ClaimDocument.claim_id == claim.id).scalar()
    if doc_count >= settings.max_files_per_claim:
        raise HTTPException(status_code=400, detail="Too many files for this claim.")
    
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    
    try:
        kind = check_file(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if doc_type.startswith("photo_") and kind not in ["jpeg", "png"]:
        raise HTTPException(status_code=400, detail="Photos must be JPG or PNG images.")
    
    hash_value = None
    try:
        from app.core.documents import file_sha256
        hash_value = file_sha256(data)
    except:
        pass
    
    existing = db.query(ClaimDocument).filter(
        ClaimDocument.claim_id == claim.id,
        ClaimDocument.file_hash == hash_value,
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="This file was already uploaded for this claim.")
    
    try:
        result = save_upload(claim.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    doc = ClaimDocument(
        claim_id=claim.id,
        doc_type=doc_type,
        original_path=result["original_path"],
        resized_path=result["resized_path"],
        mime_type=result["mime_type"],
        size_bytes=result["size_bytes"],
        file_hash=result["file_hash"],
        image_hash=result["image_hash"],
        quality_score=result["quality_score"],
        exif=result["exif"],
    )
    db.add(doc)
    db.flush()
    
    add_audit(
        db,
        user.id,
        "document_uploaded",
        claim.id,
        {"document_id": doc.id, "doc_type": doc_type, "file_hash": result["file_hash"]},
    )
    db.commit()
    
    return document_to_dict(doc)


@router.get("/claims/{claim_id}/messages")
def get_claim_messages(claim_id: str, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    """Get all messages for a claim."""
    claim = get_own_claim(db, claim_id, user)
    messages = db.query(ClaimMessage).filter(ClaimMessage.claim_id == claim.id).order_by(ClaimMessage.created_at).all()
    return [message_to_dict(m) for m in messages]


@router.post("/claims/{claim_id}/messages")
def post_message(
    claim_id: str,
    body: MessageCreate,
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """Post a message to a claim."""
    claim = get_own_claim(db, claim_id, user)
    
    message = ClaimMessage(
        claim_id=claim.id,
        sender_id=user.id,
        sender_role=user.role,
        body=body.body,
    )
    db.add(message)
    db.flush()
    
    add_audit(db, user.id, "message_sent", claim.id, {"message_id": message.id})
    db.commit()
    
    return message_to_dict(message)
