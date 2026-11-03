from datetime import datetime, timedelta, timezone
from decimal import Decimal
import imagehash


EARLY_DAYS = 30

MAX_HASH_DISTANCE = 5

EXIF_TOLERANCE_DAYS = 1

TOTAL_TOLERANCE = Decimal("1.00")

WEIGHTS = {
    "duplicate_claim": 40,
    "early_claim": 25,
    "reused_image": 50,
    "exif_date_mismatch": 30,
    "total_mismatch": 30,
}


def to_naive_utc(dt):
    """Convert a datetime to naive UTC if it is timezone-aware."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def make_flag(code, detail):
    """Create a flag dictionary with the given code and detail."""
    return {"code": code, "detail": detail}


def hash_distance(hash_a, hash_b):
    """Calculate the hamming distance between two perceptual hash hex strings."""
    if not hash_a or not hash_b:
        return 64
    try:
        h1 = imagehash.hex_to_hash(hash_a)
        h2 = imagehash.hex_to_hash(hash_b)
        return int(h1 - h2)
    except:
        return 64


def check_duplicate_claim(claim, others):
    """Check if there is another claim with the same policy and loss date."""
    claim_loss_date = to_naive_utc(claim["loss_date"]).date()
    claim_policy = claim["policy_number"]
    claim_number = claim["claim_number"]
    for other in others:
        if other["claim_number"] == claim_number:
            continue
        if other["policy_number"] != claim_policy:
            continue
        other_loss_date = to_naive_utc(other["loss_date"]).date()
        if other_loss_date == claim_loss_date:
            return [make_flag("duplicate_claim", other["claim_number"])]
    return []


def check_early_claim(claim):
    """Check if the claim was filed within the early days window."""
    policy_start = to_naive_utc(claim["policy_start"])
    loss_date = to_naive_utc(claim["loss_date"])
    days_diff = (loss_date - policy_start).days
    if days_diff < EARLY_DAYS:
        return [make_flag("early_claim", f"{days_diff} days after policy start")]
    return []


def check_reused_image(claim, others):
    """Check if documents from this claim reuse images from other claims."""
    claim_number = claim["claim_number"]
    claim_docs = claim.get("documents", [])
    flags = []
    for doc in claim_docs:
        doc_file_hash = doc.get("file_hash", "")
        doc_image_hash = doc.get("image_hash", "")
        for other in others:
            if other["claim_number"] == claim_number:
                continue
            other_docs = other.get("documents", [])
            for other_doc in other_docs:
                other_file_hash = other_doc.get("file_hash", "")
                other_image_hash = other_doc.get("image_hash", "")
                if doc_file_hash and other_file_hash and doc_file_hash == other_file_hash:
                    flags.append(make_flag("reused_image", f"file_hash matches {other['claim_number']}"))
                    break
                if doc_image_hash and other_image_hash:
                    dist = hash_distance(doc_image_hash, other_image_hash)
                    if dist <= MAX_HASH_DISTANCE:
                        flags.append(make_flag("reused_image", f"image_hash matches {other['claim_number']}"))
                        break
            if flags:
                break
        if flags:
            break
    return flags


def check_exif_date(claim):
    """Check if any document was taken before the loss date."""
    loss_date = to_naive_utc(claim["loss_date"])
    tolerance = timedelta(days=EXIF_TOLERANCE_DAYS)
    threshold = loss_date - tolerance
    docs = claim.get("documents", [])
    count = 0
    for doc in docs:
        taken_at = doc.get("taken_at")
        if taken_at is None:
            continue
        taken_naive = to_naive_utc(taken_at)
        if taken_naive < threshold:
            count = count + 1
    if count > 0:
        return [make_flag("exif_date_mismatch", f"{count} photos")]
    return []


def check_total_mismatch(claim):
    """Check if the stated total differs from the sum of items."""
    items = claim.get("items", [])
    total = sum(items, Decimal("0"))
    stated = claim.get("stated_total", Decimal("0"))
    diff = abs(total - stated)
    if diff > TOTAL_TOLERANCE:
        return [make_flag("total_mismatch", f"items total {total} vs stated {stated}")]
    return []


def run_shared_signals(claim, others):
    """Run all fraud signal checks in the fixed order."""
    flags = []
    flags.extend(check_duplicate_claim(claim, others))
    flags.extend(check_early_claim(claim))
    flags.extend(check_reused_image(claim, others))
    flags.extend(check_exif_date(claim))
    flags.extend(check_total_mismatch(claim))
    return flags


def fraud_score(flags):
    """Calculate the fraud score based on the flags."""
    total = 0
    for flag in flags:
        code = flag.get("code", "")
        weight = WEIGHTS.get(code, 0)
        total = total + weight
    if total > 100:
        total = 100
    return total


def risk_level(score):
    """Determine the risk level based on the fraud score."""
    if score < 30:
        return "low"
    if score < 60:
        return "medium"
    return "high"