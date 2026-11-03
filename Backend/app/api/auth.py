from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import bcrypt
import jwt
from app.models import get_db, User
from app.config import settings

ALGORITHM = "HS256"
TOKEN_MINUTES = 480

router = APIRouter(prefix="/auth")
bearer_scheme = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=72)


def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, password_hash):
    """Check a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def make_token(user_id):
    """Create a JWT token for a user."""
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    payload = {
        "sub": user_id,
        "exp": exp,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def user_to_dict(user):
    """Convert a user to a dictionary."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


def token_response(user):
    """Create a token response for a user."""
    return {
        "access_token": make_token(user.id),
        "token_type": "bearer",
        "user": user_to_dict(user),
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Get the current authenticated user."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not logged in.")
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    
    return user


def require_customer(user: User = Depends(get_current_user)):
    """Require the current user to be a customer."""
    if user.role != "customer":
        raise HTTPException(status_code=403, detail="Customers only.")
    return user


def require_staff(user: User = Depends(get_current_user)):
    """Require the current user to be staff."""
    if user.role == "customer":
        raise HTTPException(status_code=403, detail="Staff only.")
    return user


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new customer account."""
    email = body.email.strip().lower()
    
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return token_response(user)


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Login for customer accounts."""
    email = body.email.strip().lower()
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not check_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is wrong.")
    
    if user.role != "customer":
        raise HTTPException(status_code=403, detail="Staff accounts sign in on the staff page.")
    
    return token_response(user)


@router.post("/staff/login")
def staff_login(body: LoginRequest, db: Session = Depends(get_db)):
    """Login for staff accounts."""
    email = body.email.strip().lower()
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not check_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is wrong.")
    
    if user.role == "customer":
        raise HTTPException(status_code=403, detail="This account is not a staff account.")
    
    return token_response(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """Get the current user."""
    return user_to_dict(user)
