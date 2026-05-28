"""
Auto-Flagging Engine for Breathe ESG Platform

Flags a record (status=FLAGGED) if ANY of the following are true:
1. quantity_normalized is > 3 standard deviations from mean (for category + tenant)
2. activity_date is in the future
3. activity_date is more than 2 years old
4. co2e_kg is 0 or None after processing
5. Unit was unrecognized and a fallback was used
6. quantity_normalized is negative
"""
import statistics
from datetime import date, timedelta
from django.utils import timezone

TWO_YEARS_AGO = lambda: date.today() - timedelta(days=730)
SIGMA_THRESHOLD = 3.0


def flag_record(record_data: dict, category_stats: dict = None) -> tuple:
    """
    Evaluate a record dict and return (should_flag: bool, reasons: list[str]).

    record_data: dict with keys matching EmissionRecord fields
    category_stats: dict {(category, tenant_id): (mean, stdev)} — precomputed
    """
    reasons = []
    today = date.today()

    activity_date = record_data.get('activity_date')
    co2e_kg = record_data.get('co2e_kg')
    quantity_normalized = record_data.get('quantity_normalized')
    used_fallback = record_data.get('used_fallback', False)
    category = record_data.get('category', '')
    tenant_id = record_data.get('_tenant_id')

    # Rule 1: future date
    if activity_date and activity_date > today:
        reasons.append(f"FUTURE_DATE: activity_date {activity_date} is in the future")

    # Rule 2: more than 2 years old
    if activity_date and activity_date < TWO_YEARS_AGO():
        reasons.append(f"OLD_DATE: activity_date {activity_date} is more than 2 years old")

    # Rule 3: zero or null CO2e
    if co2e_kg is None:
        reasons.append("NULL_CO2E: co2e_kg could not be computed")
    elif co2e_kg == 0:
        reasons.append("ZERO_CO2E: co2e_kg is 0")

    # Rule 4: fallback unit used
    if used_fallback:
        reasons.append("UNIT_FALLBACK: unrecognized or estimated unit/factor was used")

    # Rule 5: negative quantity
    if quantity_normalized is not None and quantity_normalized < 0:
        reasons.append(f"NEGATIVE_QUANTITY: quantity_normalized is {quantity_normalized}")

    # Rule 6: statistical outlier (3σ)
    if category_stats and quantity_normalized is not None:
        stat_key = (category, tenant_id)
        stats = category_stats.get(stat_key)
        if stats:
            mean_val, stdev_val = stats
            if stdev_val and stdev_val > 0:
                zscore = abs(quantity_normalized - mean_val) / stdev_val
                if zscore > SIGMA_THRESHOLD:
                    reasons.append(
                        f"STATISTICAL_OUTLIER: quantity_normalized={quantity_normalized:.2f} "
                        f"is {zscore:.1f}σ from mean ({mean_val:.2f}) for {category}"
                    )

    return len(reasons) > 0, reasons


def compute_category_stats(existing_records) -> dict:
    """
    Given a queryset (or list) of EmissionRecord objects,
    compute per-(category, tenant_id) mean and stdev of quantity_normalized.

    Returns: {(category, tenant_id): (mean, stdev)}
    """
    from collections import defaultdict
    groups = defaultdict(list)

    for r in existing_records:
        if r.quantity_normalized is not None:
            groups[(r.category, r.tenant_id)].append(r.quantity_normalized)

    stats = {}
    for key, values in groups.items():
        if len(values) >= 3:
            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values)
            stats[key] = (mean_val, stdev_val)

    return stats


def apply_flagging(record_data: dict, category_stats: dict = None) -> dict:
    """
    Returns record_data with status and flag_reason set if flagging applies.
    """
    should_flag, reasons = flag_record(record_data, category_stats)
    if should_flag:
        record_data['status'] = 'FLAGGED'
        record_data['flag_reason'] = '\n'.join(reasons)
    else:
        record_data['status'] = 'PENDING_REVIEW'
        record_data['flag_reason'] = None
    return record_data
