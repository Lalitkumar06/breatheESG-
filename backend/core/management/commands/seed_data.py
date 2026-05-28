"""
Management command: seed_data

Creates:
  - 2 Tenants: acme-corp, greentech-ltd
  - Superuser: admin / admin123
  - Analyst users: acme_analyst / greentech_analyst
  - PlantLookup entries for SAP plant codes
  - EmissionFactor entries from static data
  - Loads sample data files through the ingestion pipeline

Usage:
  python manage.py seed_data
"""
import os
import time
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile

from core.models import Tenant, UserProfile
from lookups.models import PlantLookup, EmissionFactor
from ingestion.models import DataSource, IngestionJob
from ingestion.pipeline import run_ingestion_pipeline  # sync call for seeding


SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / 'sample_data'


PLANT_LOOKUPS = [
    {'plant_code': '1000', 'location_name': 'Pune Manufacturing Plant', 'country': 'IN', 'region': 'Maharashtra'},
    {'plant_code': '2300', 'location_name': 'Mumbai Logistics Hub', 'country': 'IN', 'region': 'Maharashtra'},
    {'plant_code': '3100', 'location_name': 'Bangalore Technology Park', 'country': 'IN', 'region': 'Karnataka'},
    {'plant_code': '4000', 'location_name': 'Delhi NCR Office', 'country': 'IN', 'region': 'Delhi'},
    {'plant_code': '5200', 'location_name': 'Chennai Port Facility', 'country': 'IN', 'region': 'Tamil Nadu'},
]

EMISSION_FACTORS_DATA = [
    # Fuels (per liter)
    {'category': 'FUEL', 'sub_type': 'diesel', 'unit': 'liter', 'factor_kg_co2e': 2.6765, 'source': 'DEFRA 2023', 'year': 2023},
    {'category': 'FUEL', 'sub_type': 'petrol', 'unit': 'liter', 'factor_kg_co2e': 2.3127, 'source': 'DEFRA 2023', 'year': 2023},
    {'category': 'FUEL', 'sub_type': 'natural_gas', 'unit': 'liter', 'factor_kg_co2e': 2.0438, 'source': 'DEFRA 2023', 'year': 2023},
    {'category': 'FUEL', 'sub_type': 'lpg', 'unit': 'liter', 'factor_kg_co2e': 1.5557, 'source': 'DEFRA 2023', 'year': 2023},
    # Electricity (per kWh)
    {'category': 'ELECTRICITY', 'sub_type': 'india_grid', 'unit': 'kwh', 'factor_kg_co2e': 0.7082, 'source': 'CEA India 2022-23', 'year': 2023},
    {'category': 'ELECTRICITY', 'sub_type': 'uk_grid', 'unit': 'kwh', 'factor_kg_co2e': 0.2070, 'source': 'DEFRA 2023', 'year': 2023},
    {'category': 'ELECTRICITY', 'sub_type': 'us_grid', 'unit': 'kwh', 'factor_kg_co2e': 0.3866, 'source': 'EPA 2023', 'year': 2023},
    # Flights (per passenger-km, incl. RFI)
    {'category': 'FLIGHT', 'sub_type': 'economy', 'unit': 'pax_km', 'factor_kg_co2e': 0.1555, 'source': 'DEFRA 2023', 'year': 2023},
    {'category': 'FLIGHT', 'sub_type': 'business', 'unit': 'pax_km', 'factor_kg_co2e': 0.4292, 'source': 'DEFRA 2023', 'year': 2023},
    {'category': 'FLIGHT', 'sub_type': 'first', 'unit': 'pax_km', 'factor_kg_co2e': 0.6019, 'source': 'DEFRA 2023', 'year': 2023},
    # Ground (per km)
    {'category': 'GROUND', 'sub_type': 'car_average', 'unit': 'km', 'factor_kg_co2e': 0.1867, 'source': 'DEFRA 2023', 'year': 2023},
    {'category': 'GROUND', 'sub_type': 'rail', 'unit': 'km', 'factor_kg_co2e': 0.0369, 'source': 'DEFRA 2023', 'year': 2023},
    {'category': 'GROUND', 'sub_type': 'taxi', 'unit': 'km', 'factor_kg_co2e': 0.2178, 'source': 'DEFRA 2023', 'year': 2023},
    # Hotel (spend-based)
    {'category': 'HOTEL', 'sub_type': 'spend_based', 'unit': 'usd', 'factor_kg_co2e': 0.290, 'source': 'DEFRA 2023 spend-based', 'year': 2023},
    {'category': 'HOTEL', 'sub_type': 'night_based', 'unit': 'room_night', 'factor_kg_co2e': 17.5, 'source': 'DEFRA 2023', 'year': 2023},
]


class Command(BaseCommand):
    help = 'Seed the database with sample tenants, users, plant lookups, and emission data'

    def add_arguments(self, parser):
        parser.add_argument('--no-ingest', action='store_true', help='Skip ingestion of sample data')

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Seeding Breathe ESG database ==='))

        # 1. Create tenants
        acme, _ = Tenant.objects.get_or_create(
            slug='acme-corp',
            defaults={'name': 'Acme Corporation'}
        )
        greentech, _ = Tenant.objects.get_or_create(
            slug='greentech-ltd',
            defaults={'name': 'GreenTech Limited'}
        )
        self.stdout.write(self.style.SUCCESS(f'[OK] Tenants: {acme.name}, {greentech.name}'))

        # 2. Create superuser
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@breathe.io', 'admin123')
            UserProfile.objects.create(user=admin, tenant=acme)
            self.stdout.write(self.style.SUCCESS('[OK] Superuser: admin / admin123'))

        # 3. Analyst users
        for username, tenant in [('acme_analyst', acme), ('greentech_analyst', greentech)]:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(username, f'{username}@breathe.io', 'analyst123')
                UserProfile.objects.create(user=user, tenant=tenant)
                self.stdout.write(self.style.SUCCESS(f'[OK] User: {username} / analyst123 -> {tenant.name}'))

        # 4. Plant lookup
        for pl in PLANT_LOOKUPS:
            PlantLookup.objects.get_or_create(plant_code=pl['plant_code'], defaults=pl)
        self.stdout.write(self.style.SUCCESS(f'[OK] Plant lookups: {len(PLANT_LOOKUPS)} entries'))

        # 5. Emission factors
        for ef in EMISSION_FACTORS_DATA:
            EmissionFactor.objects.get_or_create(
                category=ef['category'],
                sub_type=ef['sub_type'],
                unit=ef['unit'],
                defaults=ef,
            )
        self.stdout.write(self.style.SUCCESS(f'[OK] Emission factors: {len(EMISSION_FACTORS_DATA)} entries'))

        if options.get('no_ingest'):
            self.stdout.write(self.style.WARNING('Skipping sample data ingestion (--no-ingest)'))
            return
            return

        # 6. Ingest sample data for acme-corp
        admin_user = User.objects.get(username='admin')
        sample_files = [
            ('sap_sample.tsv', 'SAP', acme),
            ('utility_sample.csv', 'UTILITY', acme),
            ('travel_sample.csv', 'TRAVEL', acme),
        ]

        for filename, source_type, tenant in sample_files:
            filepath = SAMPLE_DATA_DIR / filename
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(f'[WARN] Sample file not found: {filepath}'))
                continue

            ds, _ = DataSource.objects.get_or_create(
                tenant=tenant,
                source_type=source_type,
                defaults={'display_name': f'{tenant.name} — {source_type}'}
            )

            with open(filepath, 'rb') as f:
                file_bytes = f.read()

            job = IngestionJob.objects.create(
                tenant=tenant,
                data_source=ds,
                uploaded_by=admin_user,
                filename=filename,
                source_type=source_type,
                status='PENDING',
            )
            job.raw_file.save(filename, ContentFile(file_bytes))
            job.save()

            self.stdout.write(f'  Ingesting {filename}...')
            run_ingestion_pipeline(str(job.id))  # synchronous for seeding

            job.refresh_from_db()
            self.stdout.write(
                self.style.SUCCESS(
                    f'  [OK] {filename}: {job.row_count} rows, {job.error_count} errors [{job.status}]'
                )
            )

        self.stdout.write(self.style.SUCCESS('\n=== Seeding complete! ==='  ))
        self.stdout.write('  Admin login: admin / admin123')
        self.stdout.write('  ACME analyst: acme_analyst / analyst123')
        self.stdout.write('  GreenTech analyst: greentech_analyst / analyst123')
