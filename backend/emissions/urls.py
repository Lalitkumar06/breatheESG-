from django.urls import path
from .views import (
    EmissionRecordListView, EmissionRecordDetailView,
    ApproveRecordView, RejectRecordView, FlagRecordView,
    BulkApproveView, RecordHistoryView,
)

urlpatterns = [
    path('records/', EmissionRecordListView.as_view(), name='record-list'),
    path('records/bulk-approve/', BulkApproveView.as_view(), name='record-bulk-approve'),
    path('records/<uuid:pk>/', EmissionRecordDetailView.as_view(), name='record-detail'),
    path('records/<uuid:pk>/approve/', ApproveRecordView.as_view(), name='record-approve'),
    path('records/<uuid:pk>/reject/', RejectRecordView.as_view(), name='record-reject'),
    path('records/<uuid:pk>/flag/', FlagRecordView.as_view(), name='record-flag'),
    path('records/<uuid:pk>/history/', RecordHistoryView.as_view(), name='record-history'),
]
