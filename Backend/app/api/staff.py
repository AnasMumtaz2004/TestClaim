from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models import get_db, Claim
from app.api.auth import require_staff
from app.api.customer import claim_to_dict

router = APIRouter(prefix="/staff", dependencies=[Depends(require_staff)])


@router.get("/claims")
def get_all_claims(db: Session = Depends(get_db)):
    """Get all claims for staff."""
    claims = db.query(Claim).all()
    return [claim_to_dict(c) for c in claims]
