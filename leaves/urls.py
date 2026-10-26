from django.urls import path
from . import views

app_name = "leaves"

urlpatterns = [
    path("", views.leave_list, name="list"),
    path("apply/", views.leave_create, name="create"),
    path("<int:pk>/review/", views.leave_review, name="review"),
    path("<int:pk>/cancel/", views.leave_cancel, name="cancel"),
]