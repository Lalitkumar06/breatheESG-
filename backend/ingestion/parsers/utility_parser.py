"""
Utility Parser — Handles electricity billing CSV exports.

Quirks handled:
- Meter IDs (multiple meters per site)
- Units: kWh, MWh → normalize to kWh
- Billing periods crossing month boundaries (period_start, period_end preserved)
- Tariff codes preserved in raw_data
- Missing reads / gaps between billing periods (flagged)
- Negative consumption (error)
"""
import csv
import io
from datetime import datetime, date, timedelta
from ingestion.normalizers import normalize_electricity
from ingestion.emission_factors import get_electricity_factor

EXPECTED_HEADERS = {
    'account_number', 'meter_id', 'site_name', 'billing_start',
    'billing_end', 'consumption_kwh', 'consumption_unit', 'tariff_code'
}

# Alternate header aliases
HEADER_ALIASES = {
    'account': 'account_number',
    'account_no': 'account_number',
    'acc_number': 'account_number',
    'meter': 'meter_id',
    'meter_number': 'meter_id',
    'site': 'site_name',
    'location': 'site_name',
    'start_date': 'billing_start',
    'from_date': 'billing_start',
    'period_from': 'billing_start',
    'end_date': 'billing_end',
    'to_date': 'billing_end',
    'period_to': 'billing_end',
    'consumption': 'consumption_kwh',
    'kwh': 'consumption_kwh',
    'usage': 'consumption_kwh',
    'units': 'consumption_unit',
    'unit': 'consumption_unit',
    'tariff': 'tariff_code',
    'rate': 'tariff_code',
    'rate_schedule': 'tariff_code',
}

# Gap threshold: if gap between billing periods > this many days, flag
GAP_THRESHOLD_DAYS = 5

# Default emission factor country
DEFAULT_COUNTRY = 'IN'


def parse_date(s: str):
    if not s or str(s).strip() in ('', 'nan', 'None'):
        return None
    s = str(s).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_header(h: str) -> str:
    clean = h.strip().lower().replace(' ', '_').replace('-', '_')
    return HEADER_ALIASES.get(clean, clean)


def detect_gaps(records: list) -> dict:
    """
    Returns dict: {meter_id: [gap_descriptions]}
    Detects periods where end_date[i] + 1 != start_date[i+1] for same meter.
    """
    by_meter = {}
    for r in records:
        mid = r.get('meter_id', 'UNKNOWN')
        by_meter.setdefault(mid, []).append(r)

    gaps = {}
    for meter, meter_records in by_meter.items():
        sorted_records = sorted(
            [r for r in meter_records if r.get('period_start') and r.get('period_end')],
            key=lambda x: x['period_start']
        )
        for i in range(1, len(sorted_records)):
            prev_end = sorted_records[i - 1]['period_end']
            curr_start = sorted_records[i]['period_start']
            gap_days = (curr_start - prev_end).days - 1
            if gap_days > GAP_THRESHOLD_DAYS:
                gaps.setdefault(meter, []).append(
                    f"Gap of {gap_days} days between {prev_end} and {curr_start}"
                )
    return gaps


def parse_utility(file_bytes: bytes) -> list:
    """
    Parse utility billing CSV.
    Returns list of parsed record dicts.
    """
    text = file_bytes.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(text))

    raw_rows = list(reader)
    if not raw_rows:
        return []

    results = []

    for row_num, raw_row in enumerate(raw_rows, start=2):
        # Normalize headers
        row = {normalize_header(k): v.strip() if v else '' for k, v in raw_row.items()}
        raw_data = dict(raw_row)

        errors = []
        used_fallback = False

        # Required fields
        meter_id = row.get('meter_id', '')
        site_name = row.get('site_name', '')
        account_number = row.get('account_number', '')
        tariff_code = row.get('tariff_code', '')

        # Dates
        period_start = parse_date(row.get('billing_start', ''))
        period_end = parse_date(row.get('billing_end', ''))

        if not period_start:
            errors.append(f"Row {row_num}: Could not parse billing_start '{row.get('billing_start')}'")
        if not period_end:
            errors.append(f"Row {row_num}: Could not parse billing_end '{row.get('billing_end')}'")

        # Mid-period activity date
        activity_date = None
        if period_start and period_end:
            mid = period_start + (period_end - period_start) / 2
            activity_date = period_start + timedelta(days=(period_end - period_start).days // 2)

        # Consumption
        consumption_raw = row.get('consumption_kwh', '') or row.get('consumption', '')
        unit_raw = row.get('consumption_unit', 'kWh') or 'kWh'

        try:
            quantity = float(consumption_raw.replace(',', ''))
        except (ValueError, AttributeError):
            quantity = None
            errors.append(f"Row {row_num}: Could not parse consumption '{consumption_raw}'")

        if quantity is not None and quantity < 0:
            errors.append(f"Row {row_num}: Negative consumption value {quantity}")

        # Normalize to kWh
        quantity_normalized = None
        if quantity is not None:
            quantity_normalized, ub = normalize_electricity(quantity, unit_raw)
            if ub:
                used_fallback = True
                errors.append(f"Row {row_num}: Unknown electricity unit '{unit_raw}', treating as kWh")

        # Emission factor
        ef = get_electricity_factor(DEFAULT_COUNTRY)
        co2e_kg = None
        if quantity_normalized is not None and quantity_normalized >= 0:
            co2e_kg = round(quantity_normalized * ef, 4)

        result = {
            'source_type': 'UTILITY',
            'scope': 2,
            'category': 'ELECTRICITY',
            'activity_date': activity_date,
            'period_start': period_start,
            'period_end': period_end,
            'quantity': quantity,
            'quantity_unit': unit_raw,
            'quantity_normalized': quantity_normalized,
            'quantity_normalized_unit': 'kWh',
            'emission_factor': ef,
            'emission_factor_unit': f'kg CO2e/kWh ({DEFAULT_COUNTRY})',
            'co2e_kg': co2e_kg,
            'location': site_name,
            'description': f"Meter {meter_id} — {site_name} (Tariff: {tariff_code})",
            'vendor': account_number,
            'raw_data': raw_data,
            'errors': errors,
            'used_fallback': used_fallback,
            '_meter_id': meter_id,
            '_site_name': site_name,
        }
        results.append(result)

    # Post-process: detect gaps and annotate
    gaps = detect_gaps(results)
    for result in results:
        mid = result.get('_meter_id', 'UNKNOWN')
        if mid in gaps:
            result['errors'].extend([f"BILLING GAP: {g}" for g in gaps[mid]])
            result['used_fallback'] = True

    return results
