import os
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Tenant
from .models import DataSource, IngestionJob
from .serializers import IngestionJobSerializer, DataSourceSerializer
from .pipeline import start_ingestion_in_background


def get_tenant(request):
    """Return the tenant for the current user."""
    profile = getattr(request.user, 'userprofile', None)
    if profile and profile.tenant:
        return profile.tenant
    if request.user.is_superuser:
        # Superusers can pass tenant_id as query param
        tenant_id = request.query_params.get('tenant_id') or request.data.get('tenant_id')
        if tenant_id:
            try:
                return Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                pass
        # Default: first tenant
        return Tenant.objects.first()
    return None


class UploadView(APIView):
    """POST /api/ingest/upload/ — Upload a file and start ingestion."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get('file')
        source_type = request.data.get('source_type', '').upper()

        if not file_obj:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        if source_type not in ('SAP', 'UTILITY', 'TRAVEL'):
            return Response(
                {'error': f"Invalid source_type '{source_type}'. Choose SAP, UTILITY, or TRAVEL."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant = get_tenant(request)
        if not tenant:
            return Response({'error': 'User has no associated tenant'}, status=status.HTTP_403_FORBIDDEN)

        # Get or create DataSource
        data_source, _ = DataSource.objects.get_or_create(
            tenant=tenant,
            source_type=source_type,
            defaults={'display_name': f"{tenant.name} — {source_type}"},
        )

        job = IngestionJob.objects.create(
            tenant=tenant,
            data_source=data_source,
            uploaded_by=request.user,
            filename=file_obj.name,
            source_type=source_type,
            raw_file=file_obj,
            status='PENDING',
        )

        # Start background ingestion
        start_ingestion_in_background(str(job.id))

        return Response(
            IngestionJobSerializer(job).data,
            status=status.HTTP_202_ACCEPTED,
        )


class JobListView(generics.ListAPIView):
    """GET /api/jobs/ — List ingestion jobs for the current tenant."""
    serializer_class = IngestionJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = IngestionJob.objects.all()
        else:
            tenant = get_tenant(self.request)
            qs = IngestionJob.objects.filter(tenant=tenant)
        return qs.select_related('tenant', 'uploaded_by', 'data_source')


class JobDetailView(generics.RetrieveAPIView):
    """GET /api/jobs/{id}/ — Job detail with row counts."""
    serializer_class = IngestionJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return IngestionJob.objects.all()
        tenant = get_tenant(self.request)
        return IngestionJob.objects.filter(tenant=tenant)
