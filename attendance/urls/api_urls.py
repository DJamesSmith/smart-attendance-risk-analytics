from django.urls import path
from . import api_views

urlpatterns = [
    path("imports/", api_views.import_list, name="api-import-list"),
    path("imports/<int:pk>/", api_views.import_detail, name="api-import-detail"),
    path("corrections/", api_views.correction_list, name="api-correction-list"),
    path("corrections/<int:pk>/", api_views.correction_detail, name="api-correction-detail"),
    path("corrections/<int:pk>/manager-review/", api_views.correction_manager_review, name="api-correction-manager-review"),
    path("corrections/<int:pk>/finalize/", api_views.correction_finalize, name="api-correction-finalize"),
]