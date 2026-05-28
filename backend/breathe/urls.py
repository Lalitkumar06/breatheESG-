from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('core.auth_urls')),
    path('api/', include('ingestion.urls')),
    path('api/', include('emissions.urls')),
    path('api/', include('dashboard.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all: serve React's index.html for every non-API route
# This enables client-side routing (React Router) to work correctly
urlpatterns += [
    re_path(r'^(?!api/|admin/|static/|media/).*$',
            TemplateView.as_view(
                template_name='index.html',
                extra_context={'settings': settings}
            )),
]
