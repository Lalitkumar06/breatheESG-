from django.urls import path
from .views import UploadView, JobListView, JobDetailView

urlpatterns = [
    path('ingest/upload/', UploadView.as_view(), name='ingest-upload'),
    path('jobs/', JobListView.as_view(), name='job-list'),
    path('jobs/<uuid:pk>/', JobDetailView.as_view(), name='job-detail'),
]
