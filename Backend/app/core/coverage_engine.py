from decimal import Decimal, ROUND_HALF_UP


def round_money(value):
    """Round a value to 2 decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_payable(claimed_amount, deductible, copay_percent, sum_insured, sub_limit=None, already_paid=0):
    """Calculate the payable amount for a claim."""
    claimed = Decimal(str(claimed_amount))
    deductible = Decimal(str(deductible))
    copay_percent = Decimal(str(copay_percent))
    sum_insured = Decimal(str(sum_insured))
    already_paid = Decimal(str(already_paid))
    
    if claimed < 0 or deductible < 0 or sum_insured < 0 or already_paid < 0:
        raise ValueError("Amounts cannot be negative.")
    
    if copay_percent < 0 or copay_percent > 100:
        raise ValueError("Co-pay must be between 0 and 100.")
    
    if sub_limit is not None:
        sub_limit = Decimal(str(sub_limit))
        if sub_limit < 0:
            raise ValueError("Amounts cannot be negative.")
    
    eligible = claimed
    if sub_limit is not None:
        eligible = min(claimed, sub_limit)
    
    after_deductible = max(eligible - deductible, Decimal("0"))
    
    copay = round_money(after_deductible * copay_percent / 100)
    
    before_cap = after_deductible - copay
    
    remaining = max(sum_insured - already_paid, Decimal("0"))
    
    payable = min(before_cap, remaining)
    
    deductible_applied = eligible - after_deductible
    
    return {
        "claimed": round_money(claimed),
        "eligible": round_money(eligible),
        "deductible_applied": round_money(deductible_applied),
        "copay": copay,
        "remaining_sum_insured": round_money(remaining),
        "payable": round_money(payable),
    }
