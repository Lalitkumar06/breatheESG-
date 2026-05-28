"""
Unit Normalization Utilities for Breathe ESG Platform

Normalizes:
  - Fuel quantities → liters
  - Electricity → kWh
  - Distance → km
"""

# Conversion factors
FUEL_DENSITY_KG_PER_L = {
    'diesel': 0.850,
    'petrol': 0.745,
    'gasoline': 0.745,
    'natural_gas': None,   # gas is in m3 or kg, not liters
    'lpg': 0.510,
    'default': 0.800,
}

GAL_TO_LITER = 3.78541       # US gallon
IMP_GAL_TO_LITER = 4.54609  # Imperial gallon
LB_TO_KG = 0.453592
M3_TO_LITER = 1000.0
MWH_TO_KWH = 1000.0
WH_TO_KWH = 0.001
MILE_TO_KM = 1.60934


UNRECOGNIZED_UNIT = object()  # sentinel


def normalize_fuel(quantity: float, unit: str, fuel_type: str = 'default') -> tuple:
    """
    Returns (normalized_liters: float, used_fallback: bool)
    Handles: L, LTR, LITER, LITRE, GAL, GALLON, KG, KGS, T, TONNE, M3, SCF, CF
    """
    if quantity is None:
        return None, False

    u = unit.strip().upper()
    fuel = (fuel_type or 'default').lower()

    if u in ('L', 'LTR', 'LITER', 'LITRE', 'LITERS', 'LITRES'):
        return quantity, False

    if u in ('GAL', 'GALLON', 'GALLONS', 'USG'):
        return quantity * GAL_TO_LITER, False

    if u in ('IMPGAL', 'UKGAL', 'IGAL'):
        return quantity * IMP_GAL_TO_LITER, False

    if u in ('KG', 'KGS', 'KILOGRAM', 'KILOGRAMS'):
        density = FUEL_DENSITY_KG_PER_L.get(fuel, FUEL_DENSITY_KG_PER_L['default'])
        if density is None:
            # Natural gas: approximate 1 kg ≈ 1.5 liters LNG equivalent (flag)
            return quantity * 1.5, True
        return quantity / density, False

    if u in ('T', 'TONNE', 'TONNES', 'MT', 'METRIC TON'):
        density = FUEL_DENSITY_KG_PER_L.get(fuel, FUEL_DENSITY_KG_PER_L['default'])
        if density is None:
            return quantity * 1500.0, True
        return (quantity * 1000.0) / density, False

    if u in ('M3', 'CBM', 'CUBIC METER', 'CUBIC METRES'):
        return quantity * M3_TO_LITER, False

    if u in ('SCF', 'CF', 'CUBIC FOOT', 'CUBIC FEET', 'CUBICFOOT'):
        # 1 SCF ≈ 28.3168 liters
        return quantity * 28.3168, True

    # Unknown unit — return as-is with fallback flag
    return quantity, True


def normalize_electricity(quantity: float, unit: str) -> tuple:
    """
    Returns (kwh: float, used_fallback: bool)
    Handles: kWh, MWh, Wh, GWh
    """
    if quantity is None:
        return None, False

    u = unit.strip().upper().replace(' ', '')

    if u in ('KWH', 'KILOWATTHOUR', 'KILOWATT-HOUR', 'KILOWATT HOUR'):
        return quantity, False

    if u in ('MWH', 'MEGAWATTHOUR', 'MEGAWATT-HOUR', 'MEGAWATT HOUR'):
        return quantity * MWH_TO_KWH, False

    if u in ('WH', 'WATTHOUR', 'WATT-HOUR', 'WATT HOUR'):
        return quantity * WH_TO_KWH, False

    if u in ('GWH', 'GIGAWATTHOUR', 'GIGAWATT-HOUR'):
        return quantity * 1_000_000.0, False

    return quantity, True


def normalize_distance(quantity: float, unit: str) -> tuple:
    """
    Returns (km: float, used_fallback: bool)
    Handles: km, mi, miles, m
    """
    if quantity is None:
        return None, False

    u = unit.strip().upper()

    if u in ('KM', 'KMS', 'KILOMETER', 'KILOMETRES', 'KILOMETERS', 'KILOMETRE'):
        return quantity, False

    if u in ('MI', 'MILE', 'MILES', 'ML'):
        return quantity * MILE_TO_KM, False

    if u in ('M', 'METER', 'METERS', 'METRE', 'METRES'):
        return quantity / 1000.0, False

    return quantity, True


# --- IATA great-circle distance estimates (km) ---
# Source: approximate geodesic calculations for common city pairs
IATA_DISTANCES_KM = {
    # Indian domestic
    ('DEL', 'BOM'): 1148, ('BOM', 'DEL'): 1148,
    ('DEL', 'BLR'): 1748, ('BLR', 'DEL'): 1748,
    ('DEL', 'HYD'): 1253, ('HYD', 'DEL'): 1253,
    ('DEL', 'MAA'): 1754, ('MAA', 'DEL'): 1754,
    ('DEL', 'CCU'): 1305, ('CCU', 'DEL'): 1305,
    ('BOM', 'BLR'): 845,  ('BLR', 'BOM'): 845,
    ('BOM', 'HYD'): 620,  ('HYD', 'BOM'): 620,
    ('BOM', 'MAA'): 1032, ('MAA', 'BOM'): 1032,
    ('DEL', 'PNQ'): 1200, ('PNQ', 'DEL'): 1200,
    ('DEL', 'JAI'): 258,  ('JAI', 'DEL'): 258,
    ('DEL', 'AMD'): 900,  ('AMD', 'DEL'): 900,
    ('DEL', 'GOI'): 1865, ('GOI', 'DEL'): 1865,
    # International
    ('DEL', 'LHR'): 6740, ('LHR', 'DEL'): 6740,
    ('DEL', 'DXB'): 2190, ('DXB', 'DEL'): 2190,
    ('DEL', 'SIN'): 4148, ('SIN', 'DEL'): 4148,
    ('DEL', 'JFK'): 11786, ('JFK', 'DEL'): 11786,
    ('BOM', 'LHR'): 7191, ('LHR', 'BOM'): 7191,
    ('BOM', 'DXB'): 1938, ('DXB', 'BOM'): 1938,
    ('BLR', 'SIN'): 3416, ('SIN', 'BLR'): 3416,
    ('HYD', 'DXB'): 2313, ('DXB', 'HYD'): 2313,
    # US domestic
    ('JFK', 'LAX'): 3983, ('LAX', 'JFK'): 3983,
    ('JFK', 'ORD'): 1189, ('ORD', 'JFK'): 1189,
    ('LAX', 'SFO'): 543,  ('SFO', 'LAX'): 543,
    # Europe
    ('LHR', 'CDG'): 340,  ('CDG', 'LHR'): 340,
    ('LHR', 'FRA'): 632,  ('FRA', 'LHR'): 632,
    ('CDG', 'AMS'): 430,  ('AMS', 'CDG'): 430,
}


def estimate_flight_distance_km(origin: str, destination: str) -> tuple:
    """
    Returns (distance_km: float | None, estimated: bool)
    Tries IATA lookup table first. Returns (None, True) if unknown.
    """
    if not origin or not destination:
        return None, True

    key = (origin.upper().strip(), destination.upper().strip())
    dist = IATA_DISTANCES_KM.get(key)
    if dist:
        return float(dist), True  # estimated, even from table
    return None, True
