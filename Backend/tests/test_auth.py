import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.models import Base, get_db, User, Policy, Claim
from app.api.auth import hash_password
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False)


@pytest.fixture
def db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield TestingSession()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def override_db(db):
    """Override the get_db dependency."""
    def get_test_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def make_user(db, email, role, name):
    """Create a user with password password123."""
    user = User(
        email=email,
        password_hash=hash_password("password123"),
        full_name=name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


claim_counter = 0

def make_claim(db, owner_id):
    """Create a policy and a motor claim for a user."""
    from datetime import datetime
    global claim_counter
    claim_counter += 1
    
    policy = Policy(
        policy_number=f"TEST-{claim_counter:03d}",
        owner_id=owner_id,
        line="motor",
        product="Test Product",
        sum_insured=500000,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2027, 1, 1),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    claim = Claim(
        claim_number=f"CLM-TEST-{claim_counter:03d}",
        policy_id=policy.id,
        claimant_id=owner_id,
        line="motor",
        claimed_amount=50000,
        loss_date=datetime(2026, 5, 15),
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def login_token(client, email, url):
    """Login and return the access token."""
    response = client.post(url, json={"email": email, "password": "password123"})
    return response.json()["access_token"]


def test_register_creates_customer(db):
    """Register creates a customer and returns a token."""
    response = client.post("/auth/register", json={
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["role"] == "customer"


def test_register_ignores_role(db):
    """Register ignores a role sent in the body."""
    response = client.post("/auth/register", json={
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "password123",
        "role": "admin",
    })
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "customer"


def test_register_duplicate_email(db):
    """Register with a duplicate email returns 400."""
    client.post("/auth/register", json={
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    })
    response = client.post("/auth/register", json={
        "full_name": "Test User 2",
        "email": "test@example.com",
        "password": "password456",
    })
    assert response.status_code == 400


def test_register_short_password(db):
    """Register with a short password returns 422."""
    response = client.post("/auth/register", json={
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "short",
    })
    assert response.status_code == 422


def test_customer_login_works(db):
    """Customer login works."""
    make_user(db, "customer@example.com", "customer", "Customer")
    response = client.post("/auth/login", json={
        "email": "customer@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(db):
    """Login with a wrong password returns 401."""
    make_user(db, "customer@example.com", "customer", "Customer")
    response = client.post("/auth/login", json={
        "email": "customer@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_login_unknown_email(db):
    """Login with an unknown email returns 401."""
    response = client.post("/auth/login", json={
        "email": "unknown@example.com",
        "password": "password123",
    })
    assert response.status_code == 401


def test_staff_on_customer_login(db):
    """Staff account on customer login returns 403."""
    make_user(db, "staff@example.com", "claims_officer", "Staff")
    response = client.post("/auth/login", json={
        "email": "staff@example.com",
        "password": "password123",
    })
    assert response.status_code == 403


def test_customer_on_staff_login(db):
    """Customer account on staff login returns 403."""
    make_user(db, "customer@example.com", "customer", "Customer")
    response = client.post("/auth/staff/login", json={
        "email": "customer@example.com",
        "password": "password123",
    })
    assert response.status_code == 403


def test_staff_login_works(db):
    """Staff login works."""
    make_user(db, "staff@example.com", "claims_officer", "Staff")
    response = client.post("/auth/staff/login", json={
        "email": "staff@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_me_with_token(db):
    """Me with a valid token returns the user."""
    make_user(db, "customer@example.com", "customer", "Customer")
    token = login_token(client, "customer@example.com", "/auth/login")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "customer@example.com"


def test_me_no_token(db):
    """Me with no token returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_garbage_token(db):
    """Me with a garbage token returns 401."""
    response = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_customer_sees_own_claims(db):
    """Customer sees only their own claims."""
    user1 = make_user(db, "customer1@example.com", "customer", "Customer 1")
    user2 = make_user(db, "customer2@example.com", "customer", "Customer 2")
    make_claim(db, user1.id)
    make_claim(db, user2.id)
    
    token = login_token(client, "customer1@example.com", "/auth/login")
    response = client.get("/customer/claims", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_customer_other_claim_404(db):
    """Customer asking for another customer claim gets 404."""
    user1 = make_user(db, "customer1@example.com", "customer", "Customer 1")
    user2 = make_user(db, "customer2@example.com", "customer", "Customer 2")
    claim2 = make_claim(db, user2.id)
    
    token = login_token(client, "customer1@example.com", "/auth/login")
    response = client.get(f"/customer/claims/{claim2.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_customer_on_staff_claims(db):
    """Customer on staff claims gets 403."""
    make_user(db, "customer@example.com", "customer", "Customer")
    token = login_token(client, "customer@example.com", "/auth/login")
    response = client.get("/staff/claims", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_staff_sees_all_claims(db):
    """Staff on staff claims gets 200 and sees all claims."""
    user1 = make_user(db, "customer1@example.com", "customer", "Customer 1")
    user2 = make_user(db, "customer2@example.com", "customer", "Customer 2")
    make_user(db, "staff@example.com", "claims_officer", "Staff")
    make_claim(db, user1.id)
    make_claim(db, user2.id)
    
    token = login_token(client, "staff@example.com", "/auth/staff/login")
    response = client.get("/staff/claims", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_staff_claims_no_token(db):
    """Staff claims with no token gets 401."""
    response = client.get("/staff/claims")
    assert response.status_code == 401


def test_staff_on_customer_claims(db):
    """Staff on customer claims gets 403."""
    make_user(db, "staff@example.com", "claims_officer", "Staff")
    token = login_token(client, "staff@example.com", "/auth/staff/login")
    response = client.get("/customer/claims", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
