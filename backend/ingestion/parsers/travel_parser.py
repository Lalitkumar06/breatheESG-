"""
Travel Parser — Handles Concur/Navan-style corporate travel CSV exports.

Quirks handled:
- Categories: AIR, HOTEL, CAR, RAIL
- Flights: IATA codes, estimate distance if missing (flagged)
- Hotels: spend-based fallback if no nights given (flagged)
- Ground: miles or km → normalize to km
- Employee ID (no names)
- Missing trip_purpose → preserved as blank
"""
import csv
import io
from datetime import datetime
from ingestion.normalizers import normalize_distance, estimate_flight_distance_km
from ingestion.emission_factors import (
    get_flight_factor, get_ground_factor, HOTEL_SPEND_FACTOR_USD, HOTEL_NIGHT_FACTOR
)

HEADER_ALIASES = {
    'transaction_id': 'transaction_id',
    'txn_id': 'transaction_id',
    'id': 'transaction_id',
    'employee_id': 'employee_id',
    'emp_id': 'employee_id',
    'employee': 'employee_id',
    'travel_date': 'travel_date',
    'date': 'travel_date',
    'trip_date': 'travel_date',
    'category': 'category',
    'type': 'category',
    'travel_type': 'category',
    'origin': 'origin',
    'from': 'origin',
    'departure': 'origin',
    'destination': 'destination',
    'to': 'destination',
    'arrival': 'destination',
    'distance_km': 'distance_km',
    'distance': 'distance_km',
    'km': 'distance_km',
    'distance_unit': 'distance_unit',
    'unit': 'distance_unit',
    'spend_usd': 'spend_usd',
    'spend': 'spend_usd',
    'amount': 'spend_usd',
    'cost': 'spend_usd',
    'vendor': 'vendor',
    'supplier': 'vendor',
    'trip_purpose': 'trip_purpose',
    'purpose': 'trip_purpose',
    'nights': 'nights',
    'hotel_nights': 'nights',
    'seat_class': 'seat_class',
    'class': 'seat_class',
    'vehicle_type': 'vehicle_type',
    'vehicle': 'vehicle_type',
}

CATEGORY_MAP = {
    'AIR': 'FLIGHT',
    'FLIGHT': 'FLIGHT',
    'AIRLINE': 'FLIGHT',
    'HOTEL': 'HOTEL',
    'ACCOMMODATION': 'HOTEL',
    'LODGING': 'HOTEL',
    'CAR': 'GROUND',
    'AUTO': 'GROUND',
    'RENTAL': 'GROUND',
    'RENTAL CAR': 'GROUND',
    'GROUND': 'GROUND',
    'TAXI': 'GROUND',
    'RAIL': 'GROUND',
    'TRAIN': 'GROUND',
    'BUS': 'GROUND',
}


def parse_date(s: str):
    if not s or str(s).strip() in ('', 'nan', 'None'):
        return None
    s = str(s).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_header(h: str) -> str:
    clean = h.strip().lower().replace(' ', '_').replace('-', '_')
    return HEADER_ALIASES.get(clean, clean)


def safe_float(s: str):
    try:
        return float(str(s).replace(',', '').strip())
    except (ValueError, TypeError):
        return None


def compute_flight_emissions(row: dict, errors: list) -> tuple:
    """Returns (quantity_km, co2e_kg, used_fallback)"""
    origin = row.get('origin', '').upper().strip()
    destination = row.get('destination', '').upper().strip()
    dist_raw = row.get('distance_km', '')
    dist_unit = row.get('distance_unit', 'km') or 'km'
    seat_class = row.get('seat_class', 'economy') or 'economy'

    used_fallback = False
    distance_km = safe_float(dist_raw)

    if distance_km is None or distance_km <= 0:
        # Try IATA lookup
        estimated_dist, _ = estimate_flight_distance_km(origin, destination)
        if estimated_dist:
            distance_km = estimated_dist
            used_fallback = True
            errors.append(
                f"Flight {origin}→{destination}: distance not provided; "
                f"estimated {estimated_dist:.0f} km from IATA table"
            )
        else:
            errors.append(
                f"Flight {origin}→{destination}: no distance and unknown IATA pair — CO2e not computable"
            )
            return None, None, True
    else:
        # Normalize unit
        distance_km, ub = normalize_distance(distance_km, dist_unit)
        if ub:
            used_fallback = True

    ef = get_flight_factor(seat_class.lower())
    co2e_kg = round(distance_km * ef, 4)
    return distance_km, co2e_kg, used_fallback


def compute_hotel_emissions(row: dict, errors: list) -> tuple:
    """Returns (quantity, quantity_unit, co2e_kg, used_fallback)"""
    nights_raw = row.get('nights', '')
    spend_raw = row.get('spend_usd', '')
    nights = safe_float(nights_raw)
    spend = safe_float(spend_raw)
    used_fallback = False

    if nights and nights > 0:
        co2e_kg = round(nights * HOTEL_NIGHT_FACTOR, 4)
        return nights, 'nights', co2e_kg, False
    elif spend and spend > 0:
        co2e_kg = round(spend * HOTEL_SPEND_FACTOR_USD, 4)
        used_fallback = True
        errors.append(
            f"Hotel: no nights provided; using spend-based factor "
            f"(${spend:.2f} × {HOTEL_SPEND_FACTOR_USD} = {co2e_kg:.2f} kg CO2e)"
        )
        return spend, 'USD_spend', co2e_kg, True
    else:
        errors.append("Hotel: no nights or spend data — CO2e not computable")
        return None, None, None, True


def compute_ground_emissions(row: dict, errors: list, category_raw: str) -> tuple:
    """Returns (distance_km, co2e_kg, used_fallback)"""
    dist_raw = row.get('distance_km', '')
    dist_unit = row.get('distance_unit', 'km') or 'km'
    vehicle_type = row.get('vehicle_type', 'default') or 'default'

    # For RAIL, use rail factor
    cat = category_raw.upper()
    if cat in ('RAIL', 'TRAIN'):
        vehicle_type = 'rail'
    elif cat in ('BUS',):
        vehicle_type = 'bus'
    elif cat in ('TAXI',):
        vehicle_type = 'taxi'

    distance_km = safe_float(dist_raw)
    used_fallback = False

    if distance_km is None:
        spend = safe_float(row.get('spend_usd', ''))
        if spend:
            # Rough spend→km estimate: $0.5/km average
            distance_km = spend / 0.5
            used_fallback = True
            errors.append(f"Ground: no distance; estimated {distance_km:.0f} km from spend")
        else:
            errors.append("Ground: no distance or spend — CO2e not computable")
            return None, None, True
    else:
        distance_km, ub = normalize_distance(distance_km, dist_unit)
        if ub:
            used_fallback = True

    ef = get_ground_factor(vehicle_type)
    co2e_kg = round(distance_km * ef, 4)
    return distance_km, co2e_kg, used_fallback


def parse_travel(file_bytes: bytes) -> list:
    """
    Parse Concur/Navan-style travel CSV.
    Returns list of parsed record dicts.
    """
    text = file_bytes.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(text))
    raw_rows = list(reader)

    if not raw_rows:
        return []

    results = []

    for row_num, raw_row in enumerate(raw_rows, start=2):
        row = {normalize_header(k): (v.strip() if v else '') for k, v in raw_row.items() if k is not None}
        raw_data = dict(raw_row)

        errors = []
        used_fallback = False

        transaction_id = row.get('transaction_id', f'ROW_{row_num}')
        employee_id = row.get('employee_id', '')
        category_raw = (row.get('category', '') or '').strip().upper()
        canonical_category = CATEGORY_MAP.get(category_raw, 'GROUND')

        travel_date = parse_date(row.get('travel_date', ''))
        if not travel_date:
            errors.append(f"Row {row_num}: Could not parse travel_date '{row.get('travel_date')}'")

        origin = row.get('origin', '')
        destination = row.get('destination', '')
        vendor = row.get('vendor', '')
        trip_purpose = row.get('trip_purpose', '')

        quantity = None
        quantity_unit = None
        quantity_normalized = None
        quantity_normalized_unit = 'km'
        ef = None
        co2e_kg = None

        if canonical_category == 'FLIGHT':
            q, co2e_kg, ub = compute_flight_emissions(row, errors)
            quantity = quantity_normalized = q
            quantity_unit = quantity_normalized_unit = 'km'
            ef = get_flight_factor(row.get('seat_class', 'economy') or 'economy')
            used_fallback = ub
        elif canonical_category == 'HOTEL':
            q, unit, co2e_kg, ub = compute_hotel_emissions(row, errors)
            quantity = quantity_normalized = q
            quantity_unit = quantity_normalized_unit = unit or 'nights'
            ef = HOTEL_SPEND_FACTOR_USD if (unit == 'USD_spend') else HOTEL_NIGHT_FACTOR
            used_fallback = ub
        elif canonical_category == 'GROUND':
            q, co2e_kg, ub = compute_ground_emissions(row, errors, category_raw)
            quantity = quantity_normalized = q
            quantity_unit = quantity_normalized_unit = 'km'
            vehicle = row.get('vehicle_type', 'car_average') or 'car_average'
            ef = get_ground_factor(vehicle)
            used_fallback = ub

        result = {
            'source_type': 'TRAVEL',
            'scope': 3,
            'category': canonical_category,
            'activity_date': travel_date,
            'period_start': travel_date,
            'period_end': travel_date,
            'quantity': quantity,
            'quantity_unit': quantity_unit or '',
            'quantity_normalized': quantity_normalized,
            'quantity_normalized_unit': quantity_normalized_unit,
            'emission_factor': ef,
            'emission_factor_unit': 'kg CO2e/km' if canonical_category in ('FLIGHT', 'GROUND') else 'kg CO2e/unit',
            'co2e_kg': co2e_kg,
            'location': f"{origin} → {destination}" if origin else destination,
            'vendor': vendor,
            'description': f"{category_raw} | {employee_id} | {trip_purpose or 'N/A'}",
            'raw_data': raw_data,
            'errors': errors,
            'used_fallback': used_fallback,
            '_transaction_id': transaction_id,
            '_employee_id': employee_id,
            '_origin': origin,
            '_destination': destination,
        }
        results.append(result)

    return results
