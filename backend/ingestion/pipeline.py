"""
Ingestion Pipeline — Orchestrates parsing, normalization, flagging, and saving.

Runs in a background thread (TODO: migrate to Celery for production).
"""
import threading
import traceback
import logging
from django.utils import timezone

from .models import IngestionJob
from .parsers.sap_parser import parse_sap
from .parsers.utility_parser import parse_utility
from .parsers.travel_parser import parse_travel
from .flagging import apply_flagging, compute_category_stats
from emissions.models import EmissionRecord
from lookups.models import PlantLookup

logger = logging.getLogger(__name__)


def get_plant_lookup_map():
    """Fetch all plant codes from DB into a dict for parser use."""
    return {
        p.plant_code: {
            'location_name': p.location_name,
            'country': p.country,
            'region': p.region,
        }
        for p in PlantLookup.objects.all()
    }


def run_ingestion_pipeline(job_id: str):
    """
    Main pipeline function. Runs in a background thread.
    1. Reads raw file from IngestionJob
    2. Selects parser by source_type
    3. Normalizes + flags each record
    4. Saves EmissionRecord objects
    5. Updates IngestionJob status
    """
    try:
        job = IngestionJob.objects.get(id=job_id)
        job.status = 'PROCESSING'
        job.save(update_fields=['status'])

        file_bytes = job.raw_file.read()
        source_type = job.source_type
        tenant = job.tenant

        # Parse
        if source_type == 'SAP':
            plant_map = get_plant_lookup_map()
            parsed_rows = parse_sap(file_bytes, plant_map)
        elif source_type == 'UTILITY':
            parsed_rows = parse_utility(file_bytes)
        elif source_type == 'TRAVEL':
            parsed_rows = parse_travel(file_bytes)
        else:
            raise ValueError(f"Unknown source_type: {source_type}")

        # Compute stats for outlier detection from existing records
        existing = EmissionRecord.objects.filter(tenant=tenant)
        category_stats = compute_category_stats(existing)

        row_count = 0
        error_count = 0
        error_details = []

        for row_data in parsed_rows:
            row_count += 1
            row_errors = row_data.pop('errors', [])

            # Inject tenant ID for stats lookup
            row_data['_tenant_id'] = str(tenant.id)

            # Apply flagging logic
            row_data = apply_flagging(row_data, category_stats)

            # If has parse errors, still save but count as error
            if row_errors:
                error_count += 1
                for err in row_errors:
                    error_details.append({'row': row_count, 'error': err})

            # Strip internal keys
            internal_keys = [k for k in row_data if k.startswith('_')]
            for k in internal_keys:
                row_data.pop(k)

            # Remove non-model keys
            row_data.pop('used_fallback', None)

            try:
                EmissionRecord.objects.create(
                    tenant=tenant,
                    ingestion_job=job,
                    source_type=source_type,
                    scope=row_data.get('scope', 1),
                    category=row_data.get('category', 'FUEL'),
                    activity_date=row_data.get('activity_date'),
                    period_start=row_data.get('period_start'),
                    period_end=row_data.get('period_end'),
                    quantity=row_data.get('quantity'),
                    quantity_unit=row_data.get('quantity_unit', ''),
                    quantity_normalized=row_data.get('quantity_normalized'),
                    quantity_normalized_unit=row_data.get('quantity_normalized_unit', ''),
                    emission_factor=row_data.get('emission_factor'),
                    emission_factor_unit=row_data.get('emission_factor_unit', ''),
                    co2e_kg=row_data.get('co2e_kg'),
                    location=row_data.get('location', ''),
                    vendor=row_data.get('vendor', ''),
                    description=row_data.get('description', ''),
                    raw_data=row_data.get('raw_data', {}),
                    status=row_data.get('status', 'PENDING_REVIEW'),
                    flag_reason=row_data.get('flag_reason'),
                )
            except Exception as e:
                error_count += 1
                error_details.append({'row': row_count, 'error': str(e)})
                logger.error(f"Failed to save record from job {job_id}, row {row_count}: {e}")

        job.status = 'COMPLETE'
        job.row_count = row_count
        job.error_count = error_count
        job.error_details = error_details
        job.save(update_fields=['status', 'row_count', 'error_count', 'error_details'])

        logger.info(f"Job {job_id} complete: {row_count} rows, {error_count} errors")

    except Exception as e:
        logger.error(f"Pipeline failed for job {job_id}: {traceback.format_exc()}")
        try:
            job = IngestionJob.objects.get(id=job_id)
            job.status = 'FAILED'
            job.processing_log = traceback.format_exc()
            job.save(update_fields=['status', 'processing_log'])
        except Exception:
            pass


def start_ingestion_in_background(job_id: str):
    """
    Spawns a background thread to run the ingestion pipeline.
    TODO: Replace with Celery task for production:
        from .tasks import run_ingestion_task
        run_ingestion_task.delay(job_id)
    """
    thread = threading.Thread(
        target=run_ingestion_pipeline,
        args=(job_id,),
        daemon=True,
        name=f"ingestion-{job_id[:8]}"
    )
    thread.start()
    return thread
