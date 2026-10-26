from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.permissions import AllowAny
from rest_framework.schemas import get_schema_view

schema_view = get_schema_view(
    title="Smart Attendance Risk Analytics API",
    version="1.0.0",
    public=True,
    permission_classes=[AllowAny],
    authentication_classes=[],
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls.urls")),
    path("attendance/", include("attendance.urls.urls")),
    path("employees/", include("organization.urls.urls")),
    path("leaves/", include("leaves.urls")),
    path("analytics/", include("analytics.urls.urls")),
    path("api/schema/", schema_view, name="api-schema"),

    # APIs
    path("api/v1/", include("accounts.urls.api_urls")),
    path("api/v1/", include("attendance.urls.api_urls")),
    path("api/v1/", include("organization.urls.api_urls")),
    path("api/v1/", include("analytics.urls.api_urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)