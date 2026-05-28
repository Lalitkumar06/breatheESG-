from django.db import models


class PlantLookup(models.Model):
    """Maps SAP plant codes to real-world locations."""
    plant_code = models.CharField(max_length=20, unique=True)
    location_name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['plant_code']

    def __str__(self):
        return f"{self.plant_code} — {self.location_name}, {self.country}"


class EmissionFactor(models.Model):
    """
    Emission factors in kg CO2e per unit.
    Source: DEFRA 2023 / IPCC AR6 / GHG Protocol.
    """
    CATEGORY_CHOICES = [
        ('FUEL', 'Fuel'),
        ('ELECTRICITY', 'Electricity'),
        ('FLIGHT', 'Flight'),
        ('HOTEL', 'Hotel'),
        ('GROUND', 'Ground Transport'),
        ('PROCUREMENT', 'Procurement'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    sub_type = models.CharField(max_length=100)      # e.g. 'diesel', 'petrol', 'natural_gas', 'economy_flight'
    unit = models.CharField(max_length=20)           # e.g. 'liter', 'kwh', 'km', 'usd'
    factor_kg_co2e = models.FloatField()             # kg CO2e per unit
    source = models.CharField(max_length=100, default='DEFRA 2023')
    year = models.IntegerField(default=2023)

    class Meta:
        unique_together = ['category', 'sub_type', 'unit']
        ordering = ['category', 'sub_type']

    def __str__(self):
        return f"{self.category}/{self.sub_type}: {self.factor_kg_co2e} kg CO2e/{self.unit}"
