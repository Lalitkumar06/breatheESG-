"""
Emission Factors — kg CO2e per unit
Sources: DEFRA 2023, IPCC AR6, GHG Protocol

These are used as static defaults and also seeded into the EmissionFactor table.
"""

# -----------------------------------------------------------------------
# FUEL (Scope 1) — kg CO2e per liter
# Source: DEFRA 2023 Conversion Factors, Table 1a
# -----------------------------------------------------------------------
FUEL_FACTORS = {
    'diesel': 2.6765,         # kg CO2e / liter
    'petrol': 2.3127,         # kg CO2e / liter
    'gasoline': 2.3127,
    'natural_gas': 2.0438,    # kg CO2e / liter (LNG equivalent)
    'lpg': 1.5557,            # kg CO2e / liter
    'heating_oil': 2.5194,
    'default': 2.5,           # fallback
}

# -----------------------------------------------------------------------
# ELECTRICITY (Scope 2) — kg CO2e per kWh
# Source: DEFRA 2023 / CEA India Grid Emission Factor 2022-23
# -----------------------------------------------------------------------
ELECTRICITY_FACTORS = {
    'IN': 0.7082,   # India (CEA 2022-23)
    'GB': 0.2070,   # UK (DEFRA 2023)
    'US': 0.3866,   # USA (EPA 2023)
    'DE': 0.3660,   # Germany
    'default': 0.5, # Generic fallback
}

# -----------------------------------------------------------------------
# FLIGHTS (Scope 3) — kg CO2e per passenger-km
# Includes radiative forcing multiplier (RFI ~1.9x)
# Source: DEFRA 2023 Business Travel (air)
# -----------------------------------------------------------------------
FLIGHT_FACTORS = {
    'economy': 0.1555,         # kg CO2e / pax-km (incl. RFI)
    'premium_economy': 0.2365,
    'business': 0.4292,
    'first': 0.6019,
    'default': 0.1555,
}

# -----------------------------------------------------------------------
# HOTELS (Scope 3) — spend-based
# Source: DEFRA 2023 Spend-based method, Category: Hotel accommodation
# -----------------------------------------------------------------------
HOTEL_SPEND_FACTOR_USD = 0.290  # kg CO2e per USD spent

# Night-based (if available)
HOTEL_NIGHT_FACTOR = 17.5       # kg CO2e per room-night (average, global)

# -----------------------------------------------------------------------
# GROUND TRANSPORT (Scope 3) — kg CO2e per km
# Source: DEFRA 2023
# -----------------------------------------------------------------------
GROUND_FACTORS = {
    'car_small': 0.1400,
    'car_medium': 0.1867,
    'car_large': 0.2785,
    'car_average': 0.1867,   # average petrol car
    'taxi': 0.2178,
    'rental_car': 0.1963,
    'rail': 0.0369,
    'bus': 0.1022,
    'default': 0.1867,
}


def get_fuel_factor(fuel_type: str) -> float:
    return FUEL_FACTORS.get((fuel_type or '').lower(), FUEL_FACTORS['default'])


def get_electricity_factor(country: str = 'default') -> float:
    return ELECTRICITY_FACTORS.get((country or '').upper(), ELECTRICITY_FACTORS['default'])


def get_flight_factor(seat_class: str = 'economy') -> float:
    return FLIGHT_FACTORS.get((seat_class or '').lower(), FLIGHT_FACTORS['default'])


def get_ground_factor(vehicle_type: str = 'default') -> float:
    vt = (vehicle_type or '').lower().replace(' ', '_')
    return GROUND_FACTORS.get(vt, GROUND_FACTORS['default'])
