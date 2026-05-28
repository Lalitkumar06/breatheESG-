"""
SAP Parser — Handles SAP MM60/MB51 material document exports.

Quirks handled:
- German column headers (Buchungsdatum, Werk, Menge, etc.)
- DD.MM.YYYY date format
- Plant codes → location via PlantLookup table
- Material codes → fuel type
- Mixed units (L, LTR, GAL, KG, T) → liters via normalizer
- Missing Mengeneinheit (unit) — flagged
- Tab-delimited or semicolon-delimited
"""
import csv
import io
from datetime import datetime
from ingestion.normalizers import normalize_fuel
from ingestion.emission_factors import get_fuel_factor

# German → English column mapping
HEADER_MAP = {
    'Buchungsdatum': 'activity_date',
    'Buchungs-datum': 'activity_date',
    'Werk': 'plant_code',
    'Werk(n)': 'plant_code',
    'Material': 'material_code',
    'Materialnummer': 'material_code',
    'Materialkurztext': 'material_description',
    'Kurztext': 'material_description',
    'Menge': 'quantity',
    'Buchungsmenge': 'quantity',
    'Mengeneinheit': 'unit',
    'ME': 'unit',
    'Bewegungsart': 'movement_type',
    'Lagerort': 'storage_location',
    'Betrag': 'amount',
    'Wahrung': 'currency',
    'Belegnummer': 'document_number',
    'GJ': 'fiscal_year',
}

# Material code prefix → fuel type
MATERIAL_TO_FUEL = {
    'DLS': 'diesel',
    'DSL': 'diesel',
    'DIESEL': 'diesel',
    'PTR': 'petrol',
    'PET': 'petrol',
    'PETROL': 'petrol',
    'GASOL': 'gasoline',
    'GAS': 'petrol',
    'NATGAS': 'natural_gas',
    'NG': 'natural_gas',
    'NGAS': 'natural_gas',
    'CNG': 'natural_gas',
    'LPG': 'lpg',
    'PROPANE': 'lpg',
    'HFO': 'heating_oil',
    'FUEL': 'diesel',  # generic fallback
}


def guess_delimiter(sample: str) -> str:
    """Detect tab vs comma vs semicolon."""
    tab_count = sample.count('\t')
    comma_count = sample.count(',')
    semi_count = sample.count(';')
    if tab_count >= comma_count and tab_count >= semi_count:
        return '\t'
    if semi_count > comma_count:
        return ';'
    return ','


def parse_german_date(date_str: str):
    """Parse DD.MM.YYYY or YYYY-MM-DD."""
    if not date_str or str(date_str).strip() in ('', 'nan'):
        return None
    s = str(date_str).strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def map_headers(headers: list) -> dict:
    """Map raw headers to canonical English names."""
    mapping = {}
    for i, h in enumerate(headers):
        h_clean = h.strip()
        canonical = HEADER_MAP.get(h_clean, h_clean.lower().replace(' ', '_'))
        mapping[canonical] = i
    return mapping


def material_to_fuel_type(material_code: str) -> str:
    if not material_code:
        return 'diesel'
    code = str(material_code).upper().strip()
    for prefix, fuel in MATERIAL_TO_FUEL.items():
        if code.startswith(prefix) or code == prefix:
            return fuel
    # Try partial match
    for prefix, fuel in MATERIAL_TO_FUEL.items():
        if prefix in code:
            return fuel
    return 'diesel'  # default fallback


def parse_sap(file_bytes: bytes, plant_lookup_map: dict = None) -> list:
    """
    Parse SAP file bytes.
    Returns list of dicts with normalized data + any errors.

    plant_lookup_map: {plant_code_str: {'location_name': ..., 'country': ...}}
    """
    plant_lookup_map = plant_lookup_map or {}
    text = file_bytes.decode('utf-8-sig', errors='replace')  # handle BOM
    sample = text[:2000]
    delimiter = guess_delimiter(sample)

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        return []

    # Find header row (skip blank/comment lines)
    header_row_idx = 0
    for i, row in enumerate(rows):
        if any(h.strip() in HEADER_MAP for h in row):
            header_row_idx = i
            break

    headers = rows[header_row_idx]
    col_map = map_headers(headers)

    results = []

    def get_col(row, name, default=''):
        idx = col_map.get(name)
        if idx is None:
            return default
        try:
            return row[idx].strip() if idx < len(row) else default
        except (IndexError, AttributeError):
            return default

    for row_num, row in enumerate(rows[header_row_idx + 1:], start=1):
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows

        raw = {h.strip(): (row[i].strip() if i < len(row) else '') for i, h in enumerate(headers)}

        errors = []
        used_fallback = False

        # Date
        date_raw = get_col(row, 'activity_date')
        activity_date = parse_german_date(date_raw)
        if not activity_date:
            errors.append(f"Row {row_num}: Could not parse date '{date_raw}'")

        # Plant → location
        plant_code = get_col(row, 'plant_code')
        location_info = plant_lookup_map.get(str(plant_code), {})
        location = location_info.get('location_name', plant_code)
        country = location_info.get('country', 'Unknown')

        # Material → fuel type
        material_code = get_col(row, 'material_code')
        fuel_type = material_to_fuel_type(material_code)

        # Quantity
        quantity_raw = get_col(row, 'quantity', '0')
        try:
            quantity = float(quantity_raw.replace(',', '.'))
        except (ValueError, AttributeError):
            quantity = None
            errors.append(f"Row {row_num}: Could not parse quantity '{quantity_raw}'")

        # Unit
        unit_raw = get_col(row, 'unit')
        if not unit_raw:
            unit_raw = 'L'  # default fallback
            used_fallback = True
            errors.append(f"Row {row_num}: Missing Mengeneinheit (unit), defaulting to L")

        # Normalize quantity
        quantity_normalized = None
        if quantity is not None:
            quantity_normalized, ub = normalize_fuel(quantity, unit_raw, fuel_type)
            if ub:
                used_fallback = True

        # Emission factor
        ef = get_fuel_factor(fuel_type)
        co2e_kg = None
        if quantity_normalized is not None:
            co2e_kg = round(quantity_normalized * ef, 4)

        # Determine scope
        material_desc = get_col(row, 'material_description', '').upper()
        movement_type = get_col(row, 'movement_type', '')
        # Movement type 101/122 = procurement (Scope 3), combustion = Scope 1
        scope = 3 if movement_type.startswith('1') and material_desc else 1
        category = 'PROCUREMENT' if scope == 3 else 'FUEL'

        result = {
            'source_type': 'SAP',
            'scope': scope,
            'category': category,
            'activity_date': activity_date,
            'period_start': activity_date,
            'period_end': activity_date,
            'quantity': quantity,
            'quantity_unit': unit_raw,
            'quantity_normalized': quantity_normalized,
            'quantity_normalized_unit': 'liter',
            'emission_factor': ef,
            'emission_factor_unit': f'kg CO2e/liter ({fuel_type})',
            'co2e_kg': co2e_kg,
            'location': location,
            'description': f"{material_code} — {get_col(row, 'material_description')}",
            'raw_data': raw,
            'errors': errors,
            'used_fallback': used_fallback,
            '_fuel_type': fuel_type,
            '_plant_code': plant_code,
        }
        results.append(result)

    return results
