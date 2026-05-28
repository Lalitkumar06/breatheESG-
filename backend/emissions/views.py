from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import AuditLog
from core.serializers import AuditLogSerializer
from ingestion.views import get_tenant
from .models import EmissionRecord
from .serializers import EmissionRecordSerializer, EmissionRecordListSerializer


def log_action(user, tenant, record, action_name, before=None, after=None, notes=''):
    AuditLog.objects.create(
        tenant=tenant,
        record=record,
        action=action_name,
        performed_by=user,
        before_state=before,
        after_state=after,
        notes=notes,
    )


class EmissionRecordListView(generics.ListAPIView):
    """GET /api/records/ — List with filters."""
    permission_classes = [IsAuthenticated]
    serializer_class = EmissionRecordListSerializer

    def get_queryset(self):
        user = self.request.user
        p = self.request.query_params

        if user.is_superuser:
            qs = EmissionRecord.objects.all()
        else:
            tenant = get_tenant(self.request)
            qs = EmissionRecord.objects.filter(tenant=tenant)

        # Filters
        if scope := p.get('scope'):
            qs = qs.filter(scope=scope)
        if src := p.get('source_type'):
            qs = qs.filter(source_type=src.upper())
        if stat := p.get('status'):
            qs = qs.filter(status=stat.upper())
        if cat := p.get('category'):
            qs = qs.filter(category=cat.upper())
        if date_from := p.get('date_from'):
            qs = qs.filter(activity_date__gte=date_from)
        if date_to := p.get('date_to'):
            qs = qs.filter(activity_date__lte=date_to)
        if job_id := p.get('job_id'):
            qs = qs.filter(ingestion_job_id=job_id)

        return qs.select_related('tenant', 'ingestion_job', 'reviewed_by')


class EmissionRecordDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET + PATCH + DELETE /api/records/{id}/"""
    permission_classes = [IsAuthenticated]
    serializer_class = EmissionRecordSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return EmissionRecord.objects.all()
        tenant = get_tenant(self.request)
        return EmissionRecord.objects.filter(tenant=tenant)

    def perform_destroy(self, instance):
        log_action(
            self.request.user,
            instance.tenant,
            instance,
            'REMOVED',
            before=EmissionRecordSerializer(instance).data,
        )
        instance.delete()

    def perform_update(self, serializer):
        record = self.get_object()
        if record.is_locked:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot edit a locked record.")

        before = EmissionRecordSerializer(record).data
        instance = serializer.save()
        after = EmissionRecordSerializer(instance).data

        log_action(
            self.request.user,
            instance.tenant,
            instance,
            'EDITED',
            before=before,
            after=after,
        )


class ApproveRecordView(APIView):
    """POST /api/records/{id}/approve/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            record = EmissionRecord.objects.get(pk=pk)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if record.is_locked:
            return Response({'error': 'Record is locked'}, status=status.HTTP_400_BAD_REQUEST)

        record.status = 'APPROVED'
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.review_notes = request.data.get('notes', '')
        record.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])

        log_action(request.user, record.tenant, record, 'APPROVED', notes=record.review_notes)

        return Response({'status': 'approved', 'id': str(pk)})


class RejectRecordView(APIView):
    """POST /api/records/{id}/reject/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            record = EmissionRecord.objects.get(pk=pk)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'Rejection reason is required'}, status=status.HTTP_400_BAD_REQUEST)

        record.status = 'REJECTED'
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.flag_reason = reason
        record.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'flag_reason'])

        log_action(request.user, record.tenant, record, 'REJECTED', notes=reason)

        return Response({'status': 'rejected', 'id': str(pk)})


class FlagRecordView(APIView):
    """POST /api/records/{id}/flag/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            record = EmissionRecord.objects.get(pk=pk)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'Flag reason is required'}, status=status.HTTP_400_BAD_REQUEST)

        record.status = 'FLAGGED'
        record.flag_reason = reason
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save(update_fields=['status', 'flag_reason', 'reviewed_by', 'reviewed_at'])

        log_action(request.user, record.tenant, record, 'FLAGGED', notes=reason)

        return Response({'status': 'flagged', 'id': str(pk)})


class BulkApproveView(APIView):
    """POST /api/records/bulk-approve/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)

        tenant = get_tenant(request)
        qs = EmissionRecord.objects.filter(id__in=ids, tenant=tenant, is_locked=False)
        count = qs.count()
        now = timezone.now()

        qs.update(
            status='APPROVED',
            reviewed_by=request.user,
            reviewed_at=now,
        )

        for record in qs:
            log_action(request.user, record.tenant, record, 'BULK_APPROVED')

        return Response({'approved': count, 'ids': ids})


class RecordHistoryView(APIView):
    """GET /api/records/{id}/history/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            record = EmissionRecord.objects.get(pk=pk)
        except EmissionRecord.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        audit_logs = AuditLog.objects.filter(record=record).order_by('-timestamp')
        return Response({
            'record_id': str(pk),
            'edit_history': record.edit_history,
            'audit_trail': AuditLogSerializer(audit_logs, many=True).data,
        })
