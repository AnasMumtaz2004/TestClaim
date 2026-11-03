# The rates and limits below are assumptions, check them against the policy wording and IRDAI rules.
from decimal import Decimal
from datetime import date, datetime
from app.core.coverage_engine import calculate_payable, round_money


REQUIRED_PHOTOS = ["photo_front", "photo_rear", "photo_left", "photo_right", "photo_closeup"]

ESTIMATE_DOC = "estimate"
POLICE_REPORT_DOC = "police_report"

POLICE_REPORT_LIMIT = Decimal("100000")

TOTAL_LOSS_PERCENT = Decimal("75")

OTHER_PARTS_RATE = Decimal("0.50")

METAL_RATES = [
    (Decimal("0.5"), Decimal("0.00")),
    (Decimal("1"), Decimal("0.05")),
    (Decimal("2"), Decimal("0.10")),
    (Decimal("3"), Decimal("0.15")),
    (Decimal("4"), Decimal("0.25")),
    (Decimal("5"), Decimal("0.35")),
    (Decimal("10"), Decimal("0.40")),
]


def required_documents(claimed_amount):
    """Return the list of required document types for a motor claim."""
    docs = list(REQUIRED_PHOTOS)
    docs.append(ESTIMATE_DOC)
    if claimed_amount >= POLICE_REPORT_LIMIT:
        docs.append(POLICE_REPORT_DOC)
    return docs


def missing_documents(claimed_amount, uploaded_types):
    """Return the required document types that have not been uploaded yet."""
    required = required_documents(claimed_amount)
    uploaded_set = set(uploaded_types)
    missing = []
    for doc_type in required:
        if doc_type not in uploaded_set:
            missing.append(doc_type)
    return missing


def vehicle_age_years(vehicle_year, loss_date):
    """Calculate the age of the vehicle in years at the time of loss."""
    loss_date_obj = loss_date.date()
    start_of_year = date(vehicle_year, 1, 1)
    days = (loss_date_obj - start_of_year).days
    age = days / 365.25
    if age < 0:
        raise ValueError("Vehicle year is after the loss date.")
    return age


def metal_rate(age_years):
    """Return the depreciation rate for metal parts based on vehicle age."""
    for upper_age, rate in METAL_RATES:
        if age_years < upper_age:
            return rate
    return Decimal("0.50")


def depreciation_amount(parts_metal, parts_other, age_years):
    """Calculate the total depreciation amount for parts."""
    rate = metal_rate(age_years)
    metal_dep = parts_metal * rate
    other_dep = parts_other * OTHER_PARTS_RATE
    total = metal_dep + other_dep
    return round_money(total)


def is_total_loss(repair_total, sum_insured):
    """Check if the repair total exceeds the total loss threshold."""
    threshold = TOTAL_LOSS_PERCENT / 100 * sum_insured
    return repair_total > threshold


def motor_payable(estimate, vehicle_year, loss_date, sum_insured, deductible, copay_percent, already_paid=0):
    """Calculate the payable amount for a motor claim."""
    parts_metal = Decimal(str(estimate.get("parts_metal", 0)))
    parts_other = Decimal(str(estimate.get("parts_other", 0)))
    labour = Decimal(str(estimate.get("labour", 0)))
    sum_insured = Decimal(str(sum_insured))
    deductible = Decimal(str(deductible))
    copay_percent = Decimal(str(copay_percent))
    already_paid = Decimal(str(already_paid))
    
    if parts_metal < 0 or parts_other < 0 or labour < 0:
        raise ValueError("Amounts cannot be negative.")
    
    age = vehicle_age_years(vehicle_year, loss_date)
    repair_total = parts_metal + parts_other + labour
    depreciation = depreciation_amount(parts_metal, parts_other, age)
    total_loss = is_total_loss(repair_total, sum_insured)
    
    if total_loss:
        eligible = sum_insured
    else:
        eligible = repair_total - depreciation
    
    coverage = calculate_payable(eligible, deductible, copay_percent, sum_insured, None, already_paid)
    
    rate_used = metal_rate(age)
    
    return {
        "vehicle_age_years": round(age, 2),
        "depreciation_rate": rate_used,
        "repair_total": repair_total,
        "depreciation": depreciation,
        "eligible_amount": eligible,
        "total_loss": total_loss,
        "coverage": coverage,
        "payable": coverage["payable"],
    }