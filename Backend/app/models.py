import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, Numeric, DateTime, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

Base = declarative_base()


def new_id():
    """Return a new UUID string."""
    return str(uuid.uuid4())


def utc_now():
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=new_id)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class Policy(Base):
    __tablename__ = "policies"
    
    id = Column(String(36), primary_key=True, default=new_id)
    policy_number = Column(String, unique=True, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    line = Column(String, nullable=False)
    product = Column(String, nullable=False)
    version = Column(String, nullable=False, default="v1")
    sum_insured = Column(Numeric(14, 2), nullable=False)
    deductible = Column(Numeric(14, 2), nullable=False, default=0)
    copay_percent = Column(Numeric(5, 2), nullable=False, default=0)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    terms = Column(JSON, nullable=False, default=dict)


class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(String(36), primary_key=True, default=new_id)
    claim_number = Column(String, unique=True, nullable=False)
    policy_id = Column(String(36), ForeignKey("policies.id"), nullable=False)
    claimant_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    line = Column(String, nullable=False)
    status = Column(String, nullable=False, default="submitted")
    loss_date = Column(DateTime(timezone=True), nullable=False)
    claimed_amount = Column(Numeric(14, 2), nullable=False)
    description = Column(Text, nullable=False, default="")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class ClaimDocument(Base):
    __tablename__ = "claim_documents"
    
    id = Column(String(36), primary_key=True, default=new_id)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False)
    doc_type = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    resized_path = Column(String, nullable=False, default="")
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    image_hash = Column(String, nullable=False, default="", index=True)
    quality_score = Column(Float, nullable=True)
    exif = Column(JSON, nullable=False, default=dict)
    extracted = Column(JSON, nullable=False, default=dict)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    claim_id = Column(String(36), nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    prev_hash = Column(String, nullable=False, default="")
    row_hash = Column(String, nullable=False, default="")


class ClaimMessage(Base):
    __tablename__ = "claim_messages"
    
    id = Column(String(36), primary_key=True, default=new_id)
    claim_id = Column(String(36), ForeignKey("claims.id"), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    sender_role = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
