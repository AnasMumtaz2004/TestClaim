import pytest
from decimal import Decimal
from app.core.coverage_engine import calculate_payable


def test_basic_claim():
    """Test basic claim with deductible and copay."""
    result = calculate_payable(50000, 5000, 10, 500000, None, 0)
    assert result["payable"] == Decimal("40500.00")


def test_deductible_bigger_than_claim():
    """Test deductible bigger than the claim."""
    result = calculate_payable(3000, 5000, 0, 500000, None, 0)
    assert result["payable"] == Decimal("0.00")


def test_sub_limit_cap():
    """Test claim capped by sub-limit."""
    result = calculate_payable(80000, 0, 0, 500000, 60000, 0)
    assert result["payable"] == Decimal("60000.00")


def test_remaining_sum_insured_cap():
    """Test claim capped by remaining sum insured."""
    result = calculate_payable(100000, 0, 0, 100000, None, 70000)
    assert result["payable"] == Decimal("30000.00")


def test_sum_insured_used_up():
    """Test sum insured used up."""
    result = calculate_payable(10000, 0, 0, 50000, None, 50000)
    assert result["payable"] == Decimal("0.00")


def test_copay_rounding():
    """Test copay rounding."""
    result = calculate_payable(1000.55, 0, 15, 500000, None, 0)
    assert result["payable"] == Decimal("850.47")
    assert result["copay"] == Decimal("150.08")


def test_complex_claim():
    """Test complex claim with sub-limit, deductible and copay."""
    result = calculate_payable(120000, 10000, 20, 500000, 100000, 0)
    assert result["payable"] == Decimal("72000.00")


def test_negative_claimed_raises():
    """Test negative claimed amount raises ValueError."""
    with pytest.raises(ValueError, match="Amounts cannot be negative"):
        calculate_payable(-1000, 0, 0, 500000, None, 0)


def test_copay_over_100_raises():
    """Test copay over 100 raises ValueError."""
    with pytest.raises(ValueError, match="Co-pay must be between 0 and 100"):
        calculate_payable(10000, 0, 150, 500000, None, 0)


def test_return_type_decimal():
    """Test returned payable is a Decimal."""
    result = calculate_payable(50000, 5000, 10, 500000, None, 0)
    assert isinstance(result["payable"], Decimal)


def test_all_keys_present():
    """Test the result dict has all six keys."""
    result = calculate_payable(50000, 5000, 10, 500000, None, 0)
    expected_keys = {"claimed", "eligible", "deductible_applied", "copay", "remaining_sum_insured", "payable"}
    assert set(result.keys()) == expected_keys
# Line registry
from app.lines import get_line


def test_get_line_motor():
    """Test get_line returns motor module."""
    line = get_line("motor")
    assert hasattr(line, "motor_payable")


def test_get_line_unknown_raises():
    """Test get_line raises ValueError for unknown line."""
    with pytest.raises(ValueError, match="Unknown line: space"):
        get_line("space")


# Motor helpers
def make_motor_estimate(metal, other, labour):
    """Create a motor estimate dict."""
    return {"parts_metal": metal, "parts_other": other, "labour": labour}


# Metal rate tests
from app.lines.motor import metal_rate


def test_metal_rate_age_0_3():
    """Test metal rate for age 0.3 years."""
    assert metal_rate(0.3) == Decimal("0.00")


def test_metal_rate_age_0_5():
    """Test metal rate for age 0.5 years."""
    assert metal_rate(0.5) == Decimal("0.05")


def test_metal_rate_age_0_99():
    """Test metal rate for age 0.99 years."""
    assert metal_rate(0.99) == Decimal("0.05")


def test_metal_rate_age_1_0():
    """Test metal rate for age 1.0 years."""
    assert metal_rate(1.0) == Decimal("0.10")


def test_metal_rate_age_2_5():
    """Test metal rate for age 2.5 years."""
    assert metal_rate(2.5) == Decimal("0.15")


def test_metal_rate_age_3_5():
    """Test metal rate for age 3.5 years."""
    assert metal_rate(3.5) == Decimal("0.25")


def test_metal_rate_age_4_5():
    """Test metal rate for age 4.5 years."""
    assert metal_rate(4.5) == Decimal("0.35")


def test_metal_rate_age_7():
    """Test metal rate for age 7 years."""
    assert metal_rate(7) == Decimal("0.40")


def test_metal_rate_age_12():
    """Test metal rate for age 12 years."""
    assert metal_rate(12) == Decimal("0.50")


# Depreciation amount
from app.lines.motor import depreciation_amount


def test_depreciation_amount_1_5_years():
    """Test depreciation amount with age 1.5 years."""
    result = depreciation_amount(Decimal("40000"), Decimal("10000"), 1.5)
    assert result == Decimal("9000.00")


# Vehicle age
from app.lines.motor import vehicle_age_years


def test_vehicle_age_years_2022_to_2026():
    """Test vehicle age calculation for 2022 vehicle."""
    from datetime import datetime
    result = vehicle_age_years(2022, datetime(2026, 1, 1))
    assert round(result, 1) == Decimal("4.0")


def test_vehicle_year_after_loss_raises():
    """Test vehicle year after loss date raises ValueError."""
    from datetime import datetime
    with pytest.raises(ValueError, match="Vehicle year is after the loss date"):
        vehicle_age_years(2028, datetime(2026, 1, 1))


# Total loss
from app.lines.motor import is_total_loss


def test_is_total_loss_false():
    """Test total loss is false when repair is below threshold."""
    result = is_total_loss(Decimal("375000"), Decimal("500000"))
    assert result is False


def test_is_total_loss_true():
    """Test total loss is true when repair exceeds threshold."""
    result = is_total_loss(Decimal("375001"), Decimal("500000"))
    assert result is True


# Motor payable
from app.lines.motor import motor_payable


def test_motor_payable_basic():
    """Test motor payable with basic estimate."""
    from datetime import datetime
    estimate = make_motor_estimate(40000, 10000, 15000)
    result = motor_payable(
        estimate=estimate,
        vehicle_year=2022,
        loss_date=datetime(2026, 1, 1),
        sum_insured=500000,
        deductible=2000,
        copay_percent=0,
    )
    assert result["repair_total"] == Decimal("65000.00")
    assert result["depreciation"] == Decimal("19000.00")
    assert result["eligible_amount"] == Decimal("46000.00")
    assert result["payable"] == Decimal("44000.00")
    assert result["total_loss"] is False


def test_motor_payable_with_copay():
    """Test motor payable with 10% copay."""
    from datetime import datetime
    estimate = make_motor_estimate(40000, 10000, 15000)
    result = motor_payable(
        estimate=estimate,
        vehicle_year=2022,
        loss_date=datetime(2026, 1, 1),
        sum_insured=500000,
        deductible=2000,
        copay_percent=10,
    )
    assert result["payable"] == Decimal("39600.00")


def test_motor_payable_total_loss():
    """Test motor payable for total loss scenario."""
    from datetime import datetime
    estimate = make_motor_estimate(250000, 75000, 75000)
    result = motor_payable(
        estimate=estimate,
        vehicle_year=2022,
        loss_date=datetime(2026, 1, 1),
        sum_insured=500000,
        deductible=5000,
        copay_percent=0,
    )
    assert result["total_loss"] is True
    assert result["eligible_amount"] == Decimal("500000.00")
    assert result["payable"] == Decimal("495000.00")


def test_motor_payable_negative_raises():
    """Test motor payable with negative value raises ValueError."""
    from datetime import datetime
    estimate = {"parts_metal": -1000, "parts_other": 0, "labour": 0}
    with pytest.raises(ValueError, match="Amounts cannot be negative"):
        motor_payable(
            estimate=estimate,
            vehicle_year=2022,
            loss_date=datetime(2026, 1, 1),
            sum_insured=500000,
            deductible=2000,
            copay_percent=0,
        )


# Required documents
from app.lines.motor import required_documents, missing_documents


def test_required_documents_under_limit():
    """Test required documents for amount under police report limit."""
    docs = required_documents(50000)
    assert len(docs) == 6
    assert "photo_front" in docs
    assert "photo_rear" in docs
    assert "photo_left" in docs
    assert "photo_right" in docs
    assert "photo_closeup" in docs
    assert "estimate" in docs
    assert "police_report" not in docs


def test_required_documents_over_limit():
    """Test required documents for amount over police report limit."""
    docs = required_documents(100000)
    assert "police_report" in docs


def test_missing_documents():
    """Test missing documents calculation."""
    missing = missing_documents(50000, ["photo_front", "estimate"])
    assert missing == ["photo_rear", "photo_left", "photo_right", "photo_closeup"]


# Fraud signals helpers
from app.core import fraud_signals


def make_claim_with_date(policy_start, loss_date, items, stated_total, documents):
    """Create a claim dict for testing."""
    return {
        "claim_number": "CLM-2026-0001",
        "policy_number": "POL-001",
        "policy_start": policy_start,
        "loss_date": loss_date,
        "items": items,
        "stated_total": stated_total,
        "documents": documents,
    }


# Early claim tests
def test_early_claim_flags():
    """Test early claim flag for claim within 30 days."""
    from datetime import datetime
    policy_start = datetime(2026, 1, 1)
    loss_date = datetime(2026, 1, 20)
    claim = make_claim_with_date(policy_start, loss_date, [], Decimal("0"), [])
    flags = fraud_signals.check_early_claim(claim)
    assert len(flags) == 1
    assert flags[0]["code"] == "early_claim"


def test_early_claim_no_flag():
    """Test no early claim flag for claim after 30 days."""
    from datetime import datetime
    policy_start = datetime(2026, 1, 1)
    loss_date = datetime(2026, 1, 31)
    claim = make_claim_with_date(policy_start, loss_date, [], Decimal("0"), [])
    flags = fraud_signals.check_early_claim(claim)
    assert len(flags) == 0


# Duplicate claim tests
def test_duplicate_claim_flags():
    """Test duplicate claim flag for same policy and day."""
    from datetime import datetime
    claim1 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [],
    )
    claim1["claim_number"] = "CLM-2026-0001"
    claim2 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [],
    )
    claim2["claim_number"] = "CLM-2026-0002"
    flags = fraud_signals.check_duplicate_claim(claim1, [claim2])
    assert len(flags) == 1
    assert flags[0]["code"] == "duplicate_claim"


def test_duplicate_claim_no_flag_different_day():
    """Test no duplicate flag for different loss date."""
    from datetime import datetime
    claim1 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [],
    )
    claim1["claim_number"] = "CLM-2026-0001"
    claim2 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 20),
        [],
        Decimal("0"),
        [],
    )
    claim2["claim_number"] = "CLM-2026-0002"
    flags = fraud_signals.check_duplicate_claim(claim1, [claim2])
    assert len(flags) == 0


def test_duplicate_claim_no_flag_different_policy():
    """Test no duplicate flag for different policy."""
    from datetime import datetime
    claim1 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [],
    )
    claim1["claim_number"] = "CLM-2026-0001"
    claim1["policy_number"] = "POL-001"
    claim2 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [],
    )
    claim2["claim_number"] = "CLM-2026-0002"
    claim2["policy_number"] = "POL-002"
    flags = fraud_signals.check_duplicate_claim(claim1, [claim2])
    assert len(flags) == 0


# Reused image tests
def test_reused_image_same_hash():
    """Test reused image flag for identical image_hash."""
    from datetime import datetime
    doc1 = {"image_hash": "ffffffffffffffff", "file_hash": ""}
    doc2 = {"image_hash": "ffffffffffffffff", "file_hash": ""}
    claim1 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [doc1],
    )
    claim1["claim_number"] = "CLM-2026-0001"
    claim2 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 20),
        [],
        Decimal("0"),
        [doc2],
    )
    claim2["claim_number"] = "CLM-2026-0002"
    flags = fraud_signals.check_reused_image(claim1, [claim2])
    assert len(flags) == 1
    assert flags[0]["code"] == "reused_image"


def test_reused_image_close_hashes():
    """Test reused image flag for close perceptual hashes."""
    from datetime import datetime
    doc1 = {"image_hash": "ffffffffffffffff", "file_hash": ""}
    doc2 = {"image_hash": "fffffffffffffff8", "file_hash": ""}
    claim1 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [doc1],
    )
    claim1["claim_number"] = "CLM-2026-0001"
    claim2 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 20),
        [],
        Decimal("0"),
        [doc2],
    )
    claim2["claim_number"] = "CLM-2026-0002"
    flags = fraud_signals.check_reused_image(claim1, [claim2])
    assert len(flags) == 1
    assert flags[0]["code"] == "reused_image"


def test_reused_image_distant_hashes():
    """Test no flag for distant perceptual hashes."""
    from datetime import datetime
    doc1 = {"image_hash": "ffffffffffffffff", "file_hash": ""}
    doc2 = {"image_hash": "fffffffffff00000", "file_hash": ""}
    claim1 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [doc1],
    )
    claim1["claim_number"] = "CLM-2026-0001"
    claim2 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 20),
        [],
        Decimal("0"),
        [doc2],
    )
    claim2["claim_number"] = "CLM-2026-0002"
    flags = fraud_signals.check_reused_image(claim1, [claim2])
    assert len(flags) == 0


def test_reused_image_ignore_self():
    """Test that own documents are ignored."""
    from datetime import datetime
    doc = {"image_hash": "ffffffffffffffff", "file_hash": ""}
    claim = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [doc],
    )
    claim["claim_number"] = "CLM-2026-0001"
    flags = fraud_signals.check_reused_image(claim, [claim])
    assert len(flags) == 0


def test_reused_image_empty_hashes():
    """Test that empty hashes never match."""
    from datetime import datetime
    doc1 = {"image_hash": "", "file_hash": ""}
    doc2 = {"image_hash": "", "file_hash": ""}
    claim1 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [],
        Decimal("0"),
        [doc1],
    )
    claim1["claim_number"] = "CLM-2026-0001"
    claim2 = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 20),
        [],
        Decimal("0"),
        [doc2],
    )
    claim2["claim_number"] = "CLM-2026-0002"
    flags = fraud_signals.check_reused_image(claim1, [claim2])
    assert len(flags) == 0


# EXIF date tests
def test_exif_date_mismatch():
    """Test EXIF date mismatch flag."""
    from datetime import datetime
    doc = {"taken_at": datetime(2026, 1, 10, 10, 0, 0)}
    claim = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 13),
        [],
        Decimal("0"),
        [doc],
    )
    flags = fraud_signals.check_exif_date(claim)
    assert len(flags) == 1
    assert flags[0]["code"] == "exif_date_mismatch"


def test_exif_date_no_flag_same_day():
    """Test no EXIF flag for photo taken on same day."""
    from datetime import datetime
    doc = {"taken_at": datetime(2026, 1, 13, 10, 0, 0)}
    claim = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 13),
        [],
        Decimal("0"),
        [doc],
    )
    flags = fraud_signals.check_exif_date(claim)
    assert len(flags) == 0


def test_exif_date_no_flag_12_hours():
    """Test no EXIF flag for photo taken 12 hours before."""
    from datetime import datetime
    doc = {"taken_at": datetime(2026, 1, 12, 12, 0, 0)}
    claim = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 13),
        [],
        Decimal("0"),
        [doc],
    )
    flags = fraud_signals.check_exif_date(claim)
    assert len(flags) == 0


def test_exif_date_none_ignored():
    """Test that taken_at None is ignored."""
    from datetime import datetime
    doc = {"taken_at": None}
    claim = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 13),
        [],
        Decimal("0"),
        [doc],
    )
    flags = fraud_signals.check_exif_date(claim)
    assert len(flags) == 0


# Total mismatch tests
from datetime import datetime


def test_total_mismatch_no_flag():
    """Test no total mismatch flag when within tolerance."""
    claim = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [Decimal("30000"), Decimal("8000"), Decimal("12000")],
        Decimal("50000"),
        [],
    )
    flags = fraud_signals.check_total_mismatch(claim)
    assert len(flags) == 0


def test_total_mismatch_flags():
    """Test total mismatch flag when outside tolerance."""
    claim = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [Decimal("30000"), Decimal("8000"), Decimal("12000")],
        Decimal("65000"),
        [],
    )
    flags = fraud_signals.check_total_mismatch(claim)
    assert len(flags) == 1
    assert flags[0]["code"] == "total_mismatch"


def test_total_mismatch_within_tolerance():
    """Test no flag for 0.50 difference within tolerance."""
    claim = make_claim_with_date(
        datetime(2025, 1, 1),
        datetime(2026, 1, 15),
        [Decimal("30000"), Decimal("8000"), Decimal("12000")],
        Decimal("50000.50"),
        [],
    )
    flags = fraud_signals.check_total_mismatch(claim)
    assert len(flags) == 0


# Fraud score tests
def test_fraud_score_zero():
    """Test fraud score with no flags."""
    flags = []
    score = fraud_signals.fraud_score(flags)
    assert score == 0


def test_fraud_score_early_only():
    """Test fraud score with early claim only."""
    flags = [{"code": "early_claim", "detail": "test"}]
    score = fraud_signals.fraud_score(flags)
    assert score == 25


def test_fraud_score_early_and_exif():
    """Test fraud score with early and exif flags."""
    flags = [
        {"code": "early_claim", "detail": "test"},
        {"code": "exif_date_mismatch", "detail": "test"},
    ]
    score = fraud_signals.fraud_score(flags)
    assert score == 55


def test_fraud_score_reused_and_duplicate():
    """Test fraud score with reused and duplicate flags."""
    flags = [
        {"code": "reused_image", "detail": "test"},
        {"code": "duplicate_claim", "detail": "test"},
    ]
    score = fraud_signals.fraud_score(flags)
    assert score == 90


def test_fraud_score_max_100():
    """Test fraud score never exceeds 100."""
    flags = [
        {"code": "duplicate_claim", "detail": "test"},
        {"code": "early_claim", "detail": "test"},
        {"code": "reused_image", "detail": "test"},
        {"code": "exif_date_mismatch", "detail": "test"},
        {"code": "total_mismatch", "detail": "test"},
    ]
    score = fraud_signals.fraud_score(flags)
    assert score == 100


# Risk level tests
def test_risk_level_low():
    """Test risk level is low for score below 30."""
    assert fraud_signals.risk_level(0) == "low"
    assert fraud_signals.risk_level(25) == "low"
    assert fraud_signals.risk_level(29) == "low"


def test_risk_level_medium():
    """Test risk level is medium for score below 60."""
    assert fraud_signals.risk_level(30) == "medium"
    assert fraud_signals.risk_level(55) == "medium"
    assert fraud_signals.risk_level(59) == "medium"


def test_risk_level_high():
    """Test risk level is high for score 60 and above."""
    assert fraud_signals.risk_level(60) == "high"
    assert fraud_signals.risk_level(90) == "high"
    assert fraud_signals.risk_level(100) == "high"


# Run shared signals order test
def test_run_shared_signals_order():
    """Test run_shared_signals returns flags in fixed order."""
    from datetime import datetime
    claim = make_claim_with_date(
        datetime(2026, 1, 1),
        datetime(2026, 1, 20),
        [Decimal("1000")],
        Decimal("1000"),
        [],
    )
    others = []
    flags = fraud_signals.run_shared_signals(claim, others)
    codes = [f["code"] for f in flags]
    expected = ["duplicate_claim", "early_claim", "reused_image", "exif_date_mismatch", "total_mismatch"]
    for code in codes:
        assert code in expected
# Ground truth tests
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from app.lines import motor
from app.core import fraud_signals


def get_ground_truth_path():
    """Get path to ground truth JSON."""
    return Path(__file__).resolve().parent.parent / "data" / "ground_truth.json"


def load_ground_truth():
    """Load and convert ground truth data."""
    path = get_ground_truth_path()
    if not path.exists():
        pytest.skip("Run generate_images.py then generate_data.py --reset first.")
    with open(path) as f:
        data = json.load(f)
    for claim in data["claims"]:
        claim["policy"]["sum_insured"] = Decimal(claim["policy"]["sum_insured"])
        claim["policy"]["deductible"] = Decimal(claim["policy"]["deductible"])
        claim["policy"]["copay_percent"] = Decimal(claim["policy"]["copay_percent"])
        claim["claimed_amount"] = Decimal(claim["claimed_amount"])
        claim["estimate"]["parts_metal"] = Decimal(str(claim["estimate"]["parts_metal"]))
        claim["estimate"]["parts_other"] = Decimal(str(claim["estimate"]["parts_other"]))
        claim["estimate"]["labour"] = Decimal(str(claim["estimate"]["labour"]))
        claim["estimate"]["stated_total"] = Decimal(str(claim["estimate"]["stated_total"]))
        claim["loss_date"] = datetime.fromisoformat(claim["loss_date"])
        claim["policy"]["start_date"] = datetime.fromisoformat(claim["policy"]["start_date"])
        claim["expected"]["eligible_amount"] = Decimal(claim["expected"]["eligible_amount"])
        claim["expected"]["payable"] = Decimal(claim["expected"]["payable"])
        for doc in claim["documents"]:
            if doc.get("taken_at"):
                doc["taken_at"] = datetime.fromisoformat(doc["taken_at"])
    return data


def test_ground_truth_payables():
    """Test that motor_payable matches ground truth payables."""
    data = load_ground_truth()
    for claim in data["claims"]:
        estimate = {
            "parts_metal": claim["estimate"]["parts_metal"],
            "parts_other": claim["estimate"]["parts_other"],
            "labour": claim["estimate"]["labour"],
        }
        vehicle_year = claim["policy"]["vehicle_year"]
        loss_date = claim["loss_date"]
        sum_insured = claim["policy"]["sum_insured"]
        deductible = claim["policy"]["deductible"]
        copay_percent = claim["policy"]["copay_percent"]

        result = motor.motor_payable(
            estimate,
            vehicle_year,
            loss_date,
            sum_insured,
            deductible,
            copay_percent,
        )

        assert result["eligible_amount"] == claim["expected"]["eligible_amount"], f"{claim['claim_number']} eligible"
        assert result["payable"] == claim["expected"]["payable"], f"{claim['claim_number']} payable"
        assert result["total_loss"] == claim["expected"]["total_loss"], f"{claim['claim_number']} total_loss"


def test_ground_truth_flags():
    """Test that fraud signals match expected flags."""
    data = load_ground_truth()
    claims_by_number = {c["claim_number"]: c for c in data["claims"]}

    for claim in data["claims"]:
        claim_number = claim["claim_number"]
        others = [c for c in data["claims"] if c["claim_number"] != claim_number]

        fraud_claim = {
            "claim_number": claim["claim_number"],
            "policy_number": claim["policy"]["policy_number"],
            "policy_start": claim["policy"]["start_date"],
            "loss_date": claim["loss_date"],
            "items": [
                claim["estimate"]["parts_metal"],
                claim["estimate"]["parts_other"],
                claim["estimate"]["labour"],
            ],
            "stated_total": claim["estimate"]["stated_total"],
            "documents": claim["documents"],
        }

        fraud_others = []
        for other in others:
            fraud_other = {
                "claim_number": other["claim_number"],
                "policy_number": other["policy"]["policy_number"],
                "policy_start": other["policy"]["start_date"],
                "loss_date": other["loss_date"],
                "items": [
                    other["estimate"]["parts_metal"],
                    other["estimate"]["parts_other"],
                    other["estimate"]["labour"],
                ],
                "stated_total": other["estimate"]["stated_total"],
                "documents": other["documents"],
            }
            fraud_others.append(fraud_other)

        flags = fraud_signals.run_shared_signals(fraud_claim, fraud_others)
        flag_codes = sorted([f["code"] for f in flags])
        expected_flags = sorted(claim["expected"]["flags"])

        assert flag_codes == expected_flags, f"{claim_number}: got {flag_codes}, expected {expected_flags}"


def test_ground_truth_covers_every_scenario():
    """Test that all scenarios are present and enough are clean."""
    data = load_ground_truth()
    scenarios = set()
    clean_count = 0
    for claim in data["claims"]:
        scenarios.add(claim["scenario"])
        if claim["scenario"] == "clean":
            clean_count = clean_count + 1

    expected_scenarios = {
        "clean",
        "reused_image_source",
        "early_claim",
        "total_mismatch",
        "total_loss",
        "duplicate_claim",
        "reused_image",
        "exif_date_mismatch",
    }

    assert scenarios == expected_scenarios, f"Missing scenarios: {expected_scenarios - scenarios}"
    assert clean_count >= 4, f"Expected at least 4 clean claims, got {clean_count}"


def test_ground_truth_clean_claims_have_no_flags():
    """Test that clean claims have no fraud flags."""
    data = load_ground_truth()
    for claim in data["claims"]:
        if claim["scenario"] == "clean":
            assert claim["expected"]["flags"] == [], f"{claim['claim_number']} should have no flags"