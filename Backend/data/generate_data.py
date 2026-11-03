import sys
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
import random

# Run this from the Backend folder so .env is found.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from faker import Faker
from app.models import init_db, Base, engine, SessionLocal, User, Policy, Claim, ClaimDocument
from app.api.auth import hash_password
from app.core.documents import save_upload
from app.config import settings
from app.lines.motor import motor_payable

Faker.seed(42)
random.seed(42)

fake = Faker()

PASSWORD = "Demo@1234"

CARS = [
    ("Maruti Suzuki", "Swift"),
    ("Hyundai", "Creta"),
    ("Tata", "Nexon"),
    ("Honda", "City"),
    ("Mahindra", "XUV700"),
]

DAMAGES = [
    "Front bumper dent",
    "Rear bumper cracked",
    "Side door scratched",
    "Windshield broken",
    "Headlight damaged",
]

GARAGES = [
    "City Auto Works",
    "Sharma Motors",
    "Delhi Car Care",
    "Prime Garage",
    "Shree Auto Repairs",
]

SCENARIOS = [
    {"customer": 1, "days": 60, "metal": 30000, "other": 8000, "labour": 12000, "name": "clean"},
    {"customer": 2, "days": 45, "metal": 22000, "other": 5000, "labour": 9000, "name": "reused_image_source"},
    {"customer": 3, "days": 70, "metal": 40000, "other": 10000, "labour": 15000, "name": "clean"},
    {"customer": 4, "days": 90, "metal": 18000, "other": 4000, "labour": 8000, "name": "clean"},
    {"customer": 5, "days": 120, "metal": 55000, "other": 12000, "labour": 20000, "name": "clean"},
    {"customer": 6, "days": 10, "metal": 26000, "other": 6000, "labour": 10000, "name": "early_claim"},
    {"customer": 7, "days": 80, "metal": 45000, "other": 9000, "labour": 16000, "name": "total_mismatch"},
    {"customer": 8, "days": 100, "metal": "total_loss", "other": "total_loss", "labour": "total_loss", "name": "total_loss"},
    {"customer": 1, "days": 100, "metal": 15000, "other": 3000, "labour": 6000, "name": "duplicate_claim"},
    {"customer": 1, "days": 100, "metal": 15000, "other": 3000, "labour": 6000, "name": "duplicate_claim"},
    {"customer": 2, "days": 75, "metal": 20000, "other": 4000, "labour": 8000, "name": "reused_image"},
    {"customer": 3, "days": 110, "metal": 28000, "other": 6000, "labour": 11000, "name": "exif_date_mismatch"},
]

STATUSES = ["submitted"] * 8 + ["pending_review", "pending_review", "approved", "submitted"]

# Depreciation table - kept separate on purpose so the test is independent
METAL_RATES_DATA = [
    (0.5, Decimal("0.00")),
    (1, Decimal("0.05")),
    (2, Decimal("0.10")),
    (3, Decimal("0.15")),
    (4, Decimal("0.25")),
    (5, Decimal("0.35")),
    (10, Decimal("0.40")),
]


def get_metal_rate_by_age(age_years):
    """Get metal depreciation rate by vehicle age."""
    for upper_age, rate in METAL_RATES_DATA:
        if age_years < upper_age:
            return rate
    return Decimal("0.50")


def expected_payable(metal, other, labour, vehicle_year, loss_date, sum_insured, deductible, copay_percent):
    """Calculate expected payable using plain Decimal arithmetic."""
    loss_date_utc = loss_date
    if loss_date_utc.tzinfo is not None:
        loss_date_utc = loss_date_utc.astimezone(timezone.utc).replace(tzinfo=None)

    year_start = date(vehicle_year, 1, 1)
    days = (loss_date_utc.date() - year_start).days
    age = days / 365.25

    metal_rate = get_metal_rate_by_age(age)
    other_rate = Decimal("0.50")

    repair_total = Decimal(str(metal)) + Decimal(str(other)) + Decimal(str(labour))

    total_loss_threshold = sum_insured * Decimal("0.75")

    if repair_total > total_loss_threshold:
        eligible = sum_insured
        is_total_loss = True
    else:
        metal_dep = Decimal(str(metal)) * metal_rate
        other_dep = Decimal(str(other)) * other_rate
        depreciation = metal_dep + other_dep
        eligible = repair_total - depreciation
        is_total_loss = False

    after_deductible = max(eligible - deductible, Decimal("0"))
    copay_amount = after_deductible * Decimal(str(copay_percent)) / 100
    payable = min(after_deductible - copay_amount, sum_insured)
    payable = payable.quantize(Decimal("0.01"))

    return {
        "eligible": eligible.quantize(Decimal("0.01")),
        "payable": payable.quantize(Decimal("0.01")),
        "total_loss": is_total_loss,
    }


def make_staff(db, password_hash):
    """Create staff users."""
    staff = [
        ("officer@demo.com", "claims_officer", "Claims Officer"),
        ("medical@demo.com", "medical_officer", "Medical Officer"),
        ("surveyor@demo.com", "surveyor", "Surveyor"),
    ]

    users = []
    for email, role, name in staff:
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=name,
            role=role,
        )
        db.add(user)
        users.append(user)

    return users


def make_customers(db, password_hash):
    """Create customer users."""
    customers = []
    for i in range(1, 9):
        user = User(
            email=f"customer{i}@demo.com",
            password_hash=password_hash,
            full_name=fake.name(),
            role="customer",
        )
        db.add(user)
        customers.append(user)

    return customers


def make_policy(db, owner_id, policy_num, start_date):
    """Create a motor policy for a customer."""
    end_date = start_date + timedelta(days=365)
    make, model = random.choice(CARS)
    reg_no = "DL01" + fake.bothify(text="??").upper() + str(random.randint(1000, 9999))
    vehicle_year = random.randint(2018, 2024)

    policy = Policy(
        policy_number=f"MOT-2026-{policy_num:04d}",
        owner_id=owner_id,
        line="motor",
        product="Private Car Comprehensive",
        sum_insured=random.choice([300000, 500000, 700000, 900000]),
        deductible=random.choice([1000, 2000, 5000]),
        copay_percent=0,
        start_date=start_date,
        end_date=end_date,
        terms={
            "make": make,
            "model": model,
            "year": vehicle_year,
            "reg_no": reg_no,
        },
    )
    db.add(policy)
    return policy


def make_claims_and_documents(db, policies, today):
    """Create motor claims with documents from generated images."""
    claims_data = []

    for i, scenario in enumerate(SCENARIOS):
        policy = policies[scenario["customer"] - 1]
        policy_start = policy.start_date
        loss_date = policy_start + timedelta(days=scenario["days"])

        metal = scenario["metal"]
        other = scenario["other"]
        labour = scenario["labour"]

        if metal == "total_loss":
            sum_insured = policy.sum_insured
            metal = int(sum_insured * Decimal("0.50"))
            other = int(sum_insured * Decimal("0.15"))
            labour = int(sum_insured * Decimal("0.15"))

        stated_total = metal + other + labour
        if scenario["name"] == "total_mismatch":
            stated_total = stated_total + 15000

        estimate = {
            "parts_metal": metal,
            "parts_other": other,
            "labour": labour,
            "stated_total": stated_total,
        }

        claim = Claim(
            claim_number=f"CLM-2026-{i + 1:04d}",
            policy_id=policy.id,
            claimant_id=policy.owner_id,
            line="motor",
            status=STATUSES[i],
            loss_date=loss_date,
            claimed_amount=stated_total,
            description=random.choice(DAMAGES),
            details={
                "garage": random.choice(GARAGES),
                "damage": random.choice(DAMAGES),
                "estimate": estimate,
                "estimate_amount": stated_total,
            },
        )
        db.add(claim)
        db.flush()

        claim_data = {
            "claim": claim,
            "policy": policy,
            "scenario": scenario,
            "estimate": estimate,
            "loss_date": loss_date,
            "stated_total": stated_total,
        }
        claims_data.append(claim_data)

    db.flush()

    base_dir = Path(__file__).resolve().parent
    photos_dir = base_dir / "sample_images" / "photos"

    doc_count = 0

    for claim_data in claims_data:
        claim = claim_data["claim"]
        loss_date = claim_data["loss_date"]
        scenario_name = claim_data["scenario"]["name"]

        claim_dir = photos_dir / claim.claim_number

        if not claim_dir.exists():
            continue

        for doc_type in ["photo_front", "photo_rear", "photo_left", "photo_right", "photo_closeup"]:
            photo_path = claim_dir / f"{doc_type}.jpg"

            if not photo_path.exists():
                continue

            img = Image.open(photo_path)

            exif = img.getexif()
            if exif is None:
                exif = {}

            if scenario_name == "exif_date_mismatch":
                taken_date = loss_date - timedelta(days=20)
            else:
                taken_date = loss_date

            taken_datetime = taken_date + timedelta(hours=2)
            exif[0x0132] = taken_datetime.strftime("%Y:%m:%d %H:%M:%S")

            buffer = BytesIO()
            img.save(buffer, "JPEG", quality=90, exif=exif)
            buffer.seek(0)
            data = buffer.read()

            result = save_upload(claim.id, data)

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
            doc_count = doc_count + 1

    db.commit()

    return claims_data, doc_count


def write_ground_truth(claims_data, db):
    """Write ground truth JSON file."""
    base_dir = Path(__file__).resolve().parent
    truth_path = base_dir / "ground_truth.json"

    claims_list = []

    for i, claim_data in enumerate(claims_data):
        claim = claim_data["claim"]
        policy = claim_data["policy"]
        scenario = claim_data["scenario"]
        estimate = claim_data["estimate"]
        loss_date = claim_data["loss_date"]

        policy_start_utc = policy.start_date
        if policy_start_utc.tzinfo is not None:
            policy_start_utc = policy_start_utc.astimezone(timezone.utc).replace(tzinfo=None)

        loss_date_utc = loss_date
        if loss_date_utc.tzinfo is not None:
            loss_date_utc = loss_date_utc.astimezone(timezone.utc).replace(tzinfo=None)

        vehicle_year = policy.terms.get("year", 2020)

        expected = expected_payable(
            estimate["parts_metal"],
            estimate["parts_other"],
            estimate["labour"],
            vehicle_year,
            loss_date_utc,
            policy.sum_insured,
            policy.deductible,
            policy.copay_percent,
        )

        scenario_flags = []
        if scenario["name"] == "reused_image_source":
            scenario_flags = ["reused_image"]
        elif scenario["name"] == "reused_image":
            scenario_flags = ["reused_image"]
        elif scenario["name"] == "early_claim":
            scenario_flags = ["early_claim"]
        elif scenario["name"] == "total_mismatch":
            scenario_flags = ["total_mismatch"]
        elif scenario["name"] == "duplicate_claim":
            scenario_flags = ["duplicate_claim"]
        elif scenario["name"] == "exif_date_mismatch":
            scenario_flags = ["exif_date_mismatch"]

        docs_query = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()

        docs = []
        for doc in docs_query:
            taken_at = None
            if doc.exif and doc.exif.get("taken_at"):
                taken_at = doc.exif["taken_at"]

            docs.append({
                "doc_type": doc.doc_type,
                "image_hash": doc.image_hash or "",
                "file_hash": doc.file_hash or "",
                "taken_at": taken_at,
            })

        claim_entry = {
            "claim_number": claim.claim_number,
            "scenario": scenario["name"],
            "policy": {
                "policy_number": policy.policy_number,
                "start_date": policy_start_utc.isoformat(),
                "sum_insured": str(policy.sum_insured),
                "deductible": str(policy.deductible),
                "copay_percent": str(policy.copay_percent),
                "vehicle_year": vehicle_year,
            },
            "loss_date": loss_date_utc.isoformat(),
            "claimed_amount": str(claim.claimed_amount),
            "estimate": {
                "parts_metal": estimate["parts_metal"],
                "parts_other": estimate["parts_other"],
                "labour": estimate["labour"],
                "stated_total": estimate["stated_total"],
            },
            "documents": docs,
            "expected": {
                "flags": sorted(scenario_flags),
                "total_loss": expected["total_loss"],
                "eligible_amount": str(expected["eligible"]),
                "payable": str(expected["payable"]),
            },
        }

        claims_list.append(claim_entry)

    truth_data = {"claims": claims_list}

    with open(truth_path, "w") as f:
        json.dump(truth_data, f, indent=2)

    return truth_path


def main():
    """Generate demo data."""
    base_dir = Path(__file__).resolve().parent
    photos_dir = base_dir / "sample_images" / "photos"

    if not photos_dir.exists():
        print("Run python data\\generate_images.py first.")
        return

    if "--reset" in sys.argv:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        originals_dir = Path(settings.storage_dir) / "originals"
        resized_dir = Path(settings.storage_dir) / "resized"

        if originals_dir.exists():
            shutil.rmtree(originals_dir)
            print(f"Deleted {originals_dir}")

        if resized_dir.exists():
            shutil.rmtree(resized_dir)
            print(f"Deleted {resized_dir}")
    else:
        init_db()

    db = SessionLocal()

    if db.query(User).first():
        print("Data already exists. Use --reset to start over.")
        db.close()
        return

    password_hash = hash_password(PASSWORD)

    staff = make_staff(db, password_hash)
    customers = make_customers(db, password_hash)
    db.flush()

    today = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
    policy_start = today - timedelta(days=180)

    policies = []
    for i, customer in enumerate(customers):
        policy = make_policy(db, customer.id, i + 1, policy_start)
        policies.append(policy)
    db.flush()

    claims_data, doc_count = make_claims_and_documents(db, policies, today)

    truth_path = write_ground_truth(claims_data, db)

    db.close()

    print("\nDemo data created.\n")
    print("Staff accounts:")
    print("  officer@demo.com (claims_officer)")
    print("  medical@demo.com (medical_officer)")
    print("  surveyor@demo.com (surveyor)")
    print("\nCustomer accounts:")
    for i in range(1, 9):
        print(f"  customer{i}@demo.com")
    print(f"\nAll accounts use password: {PASSWORD}")
    print(f"\nCreated {len(staff)} staff, {len(customers)} customers, {len(policies)} policies, {len(claims_data)} claims, {doc_count} documents.")
    print(f"Ground truth: {truth_path}")


if __name__ == "__main__":
    from io import BytesIO
    from PIL import Image
    main()