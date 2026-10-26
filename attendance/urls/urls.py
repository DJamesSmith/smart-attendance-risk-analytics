from django.urls import path
from ..views import views

app_name = "attendance"

urlpatterns = [
    path("upload/", views.attendance_upload, name="upload"),
    path("imports/", views.batch_list, name="batch_list"),
    path("imports/<int:pk>/", views.batch_detail, name="batch_detail"),
    path("daily/", views.daily_attendance_list, name="daily_list"),
    path("corrections/", views.correction_list, name="correction_list"),
    path("corrections/new/", views.correction_create, name="correction_create"),
    path("corrections/<int:pk>/", views.correction_detail, name="correction_detail"),
    path("corrections/<int:pk>/edit/", views.correction_update, name="correction_update"),
    path("corrections/<int:pk>/delete/", views.correction_delete, name="correction_delete"),
    path("corrections/<int:pk>/manager-review/", views.correction_manager_review, name="correction_manager_review"),
    path("corrections/<int:pk>/finalize/", views.correction_finalize, name="correction_finalize"),
]