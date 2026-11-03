import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.models import Base, get_db, User, Policy, Claim, AuditLog
from app.api.auth import hash_password
from app.main import app as fastapi_app
from app.config import settings
from app.core.governance import verify_chain
import app.core.email_service

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
    fastapi_app.dependency_overrides[get_db] = get_test_db
    yield
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def email_calls():
    """Track email calls."""
    calls = []
    
    def fake_send_email(to, subject, body):
        calls.append({"to": to, "subject": subject, "body": body})
    
    original = app.core.email_service.send_email
    app.core.email_service.send_email = fake_send_email
    yield calls
    app.core.email_service.send_email = original


@pytest.fixture
def setup_storage(monkeypatch, tmp_path):
    """Setup temporary storage directory."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))


client = TestClient(fastapi_app)


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


policy_counter = 0

def make_policy(db, owner_id):
    """Create a policy for a user."""
    global policy_counter
    policy_counter += 1
    
    start = datetime(2026, 1, 1)
    end = datetime(2027, 1, 1)
    
    policy = Policy(
        policy_number=f"TEST-POL-{policy_counter:03d}",
        owner_id=owner_id,
        line="motor",
        product="Test Product",
        sum_insured=500000,
        start_date=start,
        end_date=end,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def login_token(client, email):
    """Login and return the access token."""
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    return response.json()["access_token"]


def make_png_bytes():
    """Create a small PNG image."""
    from PIL import Image
    from io import BytesIO
    
    img = Image.new("RGB", (100, 100), color="white")
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def test_file_claim_works(db, email_calls):
    """Filing a claim on your own policy works and sends email."""
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
            "description": "Test claim",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    assert "claim_number" in response.json()
    assert len(email_calls) == 1
    assert email_calls[0]["to"] == "customer@example.com"


def test_file_claim_other_policy_404(db):
    """Filing on another customer's policy returns 404."""
    user1 = make_user(db, "customer1@example.com", "customer", "Customer 1")
    user2 = make_user(db, "customer2@example.com", "customer", "Customer 2")
    policy2 = make_policy(db, user2.id)
    token1 = login_token(client, "customer1@example.com")
    
    response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy2.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token1}"},
    )
    
    assert response.status_code == 404


def test_future_loss_date_400(db):
    """Future loss date returns 400."""
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    future = datetime.now(timezone.utc) + timedelta(days=10)
    response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": future.isoformat(),
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


def test_zero_amount_422(db):
    """Amount 0 returns 422."""
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 422


def test_email_failure_still_succeeds(db, email_calls, monkeypatch):
    """Email failure still returns success and logs email_failed."""
    def fake_fail(to, subject, body):
        raise OSError("SMTP down")
    
    monkeypatch.setattr(app.core.email_service, "send_email", fake_fail)
    
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    
    failed = db.query(AuditLog).filter(AuditLog.action == "email_failed").first()
    assert failed is not None


def test_upload_png_works(db, setup_storage):
    """Uploading a PNG to your own claim works."""
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    claim_response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    claim_id = claim_response.json()["id"]
    
    png_data = make_png_bytes()
    
    response = client.post(
        f"/customer/claims/{claim_id}/documents",
        data={"doc_type": "photo_front"},
        files={"file": ("test.png", png_data, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    assert response.json()["doc_type"] == "photo_front"


def test_upload_other_claim_404(db, setup_storage):
    """Uploading to someone else's claim returns 404."""
    user1 = make_user(db, "customer1@example.com", "customer", "Customer 1")
    user2 = make_user(db, "customer2@example.com", "customer", "Customer 2")
    policy1 = make_policy(db, user1.id)
    policy2 = make_policy(db, user2.id)
    
    token1 = login_token(client, "customer1@example.com")
    token2 = login_token(client, "customer2@example.com")
    
    claim2_response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy2.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token2}"},
    )
    claim2_id = claim2_response.json()["id"]
    
    png_data = make_png_bytes()
    
    response = client.post(
        f"/customer/claims/{claim2_id}/documents",
        data={"doc_type": "photo_front"},
        files={"file": ("test.png", png_data, "image/png")},
        headers={"Authorization": f"Bearer {token1}"},
    )
    
    assert response.status_code == 404


def test_upload_text_file_400(db, setup_storage):
    """Uploading a text file returns 400."""
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    claim_response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    claim_id = claim_response.json()["id"]
    
    response = client.post(
        f"/customer/claims/{claim_id}/documents",
        data={"doc_type": "other"},
        files={"file": ("test.txt", b"hello world", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 400


def test_upload_duplicate_400(db, setup_storage):
    """Uploading duplicate file returns 400."""
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    claim_response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    claim_id = claim_response.json()["id"]
    
    png_data = make_png_bytes()
    
    client.post(
        f"/customer/claims/{claim_id}/documents",
        data={"doc_type": "photo_front"},
        files={"file": ("test.png", png_data, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    response2 = client.post(
        f"/customer/claims/{claim_id}/documents",
        data={"doc_type": "photo_rear"},
        files={"file": ("test2.png", png_data, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response2.status_code == 400
    assert "already uploaded" in response2.json()["detail"]


def test_exceed_file_limit_400(db, setup_storage, monkeypatch):
    """Exceeding file limit returns 400."""
    monkeypatch.setattr(settings, "max_files_per_claim", 1)
    
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    claim_response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    claim_id = claim_response.json()["id"]
    
    png_data1 = make_png_bytes()
    
    client.post(
        f"/customer/claims/{claim_id}/documents",
        data={"doc_type": "photo_front"},
        files={"file": ("test1.png", png_data1, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    from PIL import Image
    from io import BytesIO
    img2 = Image.new("RGB", (100, 100), color="red")
    buf2 = BytesIO()
    img2.save(buf2, "PNG")
    png_data2 = buf2.getvalue()
    
    response2 = client.post(
        f"/customer/claims/{claim_id}/documents",
        data={"doc_type": "photo_rear"},
        files={"file": ("test2.png", png_data2, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response2.status_code == 400
    assert "Too many files" in response2.json()["detail"]


def test_list_documents_other_claim_404(db, setup_storage):
    """Listing documents for someone else's claim returns 404."""
    user1 = make_user(db, "customer1@example.com", "customer", "Customer 1")
    user2 = make_user(db, "customer2@example.com", "customer", "Customer 2")
    policy2 = make_policy(db, user2.id)
    
    token1 = login_token(client, "customer1@example.com")
    token2 = login_token(client, "customer2@example.com")
    
    claim2_response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy2.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token2}"},
    )
    claim2_id = claim2_response.json()["id"]
    
    response = client.get(
        f"/customer/claims/{claim2_id}/documents",
        headers={"Authorization": f"Bearer {token1}"},
    )
    
    assert response.status_code == 404


def test_list_messages_other_claim_404(db):
    """Listing messages for someone else's claim returns 404."""
    user1 = make_user(db, "customer1@example.com", "customer", "Customer 1")
    user2 = make_user(db, "customer2@example.com", "customer", "Customer 2")
    policy2 = make_policy(db, user2.id)
    
    token1 = login_token(client, "customer1@example.com")
    token2 = login_token(client, "customer2@example.com")
    
    claim2_response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy2.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token2}"},
    )
    claim2_id = claim2_response.json()["id"]
    
    response = client.get(
        f"/customer/claims/{claim2_id}/messages",
        headers={"Authorization": f"Bearer {token1}"},
    )
    
    assert response.status_code == 404


def test_post_and_list_message_works(db):
    """Posting and listing a message works."""
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    claim_response = client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    claim_id = claim_response.json()["id"]
    
    msg_response = client.post(
        f"/customer/claims/{claim_id}/messages",
        json={"body": "Hello, I have a question."},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert msg_response.status_code == 200
    assert msg_response.json()["body"] == "Hello, I have a question."
    
    list_response = client.get(
        f"/customer/claims/{claim_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_audit_chain_verifies(db):
    """The audit chain verifies after all operations."""
    user = make_user(db, "customer@example.com", "customer", "Customer")
    policy = make_policy(db, user.id)
    token = login_token(client, "customer@example.com")
    
    client.post(
        "/customer/claims",
        json={
            "policy_id": policy.id,
            "loss_date": "2026-06-15T10:00:00Z",
            "claimed_amount": 50000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    valid, bad_id = verify_chain(db)
    assert valid is True
    assert bad_id is None
