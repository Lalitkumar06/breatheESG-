from django.db.models import Sum, Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from emissions.models import EmissionRecord
from ingestion.views import get_tenant


class DashboardSummaryView(APIView):
    """GET /api/dashboard/summary/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = get_tenant(request)
        if not tenant and not request.user.is_superuser:
            return Response({'error': 'No tenant'}, status=403)

        if request.user.is_superuser and not tenant:
            qs = EmissionRecord.objects.all()
        else:
            qs = EmissionRecord.objects.filter(tenant=tenant)

        # Overall totals by scope
        scope_totals = {}
        for scope in [1, 2, 3]:
            agg = qs.filter(scope=scope).aggregate(
                total_co2e=Sum('co2e_kg'),
                count=Count('id'),
            )
            scope_totals[f'scope_{scope}'] = {
                'total_co2e_kg': round(agg['total_co2e'] or 0, 2),
                'record_count': agg['count'],
            }

        # By source type
        source_breakdown = []
        for src in ['SAP', 'UTILITY', 'TRAVEL']:
            agg = qs.filter(source_type=src).aggregate(
                total_co2e=Sum('co2e_kg'),
                count=Count('id'),
            )
            source_breakdown.append({
                'source': src,
                'total_co2e_kg': round(agg['total_co2e'] or 0, 2),
                'record_count': agg['count'],
            })

        # By status
        status_counts = {}
        for stat in ['PENDING_REVIEW', 'APPROVED', 'REJECTED', 'FLAGGED']:
            status_counts[stat.lower()] = qs.filter(status=stat).count()

        # By category
        category_breakdown = (
            qs.values('category')
            .annotate(total_co2e=Sum('co2e_kg'), count=Count('id'))
            .order_by('-total_co2e')
        )


        # Pending review count (alert)
        pending_count = qs.filter(status='PENDING_REVIEW').count()
        flagged_count = qs.filter(status='FLAGGED').count()

        # Recent jobs
        from ingestion.models import IngestionJob
        from ingestion.serializers import IngestionJobSerializer
        recent_jobs_qs = IngestionJob.objects.filter(tenant=tenant).order_by('-uploaded_at')[:5]
        recent_jobs = IngestionJobSerializer(recent_jobs_qs, many=True).data

        total_co2e = qs.aggregate(t=Sum('co2e_kg'))['t'] or 0

        return Response({
            'tenant': tenant.slug if tenant else 'all',
            'total_co2e_kg': round(total_co2e, 2),
            'scope_totals': scope_totals,
            'source_breakdown': source_breakdown,
            'category_breakdown': list(category_breakdown),
            'status_counts': status_counts,
            'pending_review_count': pending_count,
            'flagged_count': flagged_count,
            'recent_jobs': recent_jobs,
        })
