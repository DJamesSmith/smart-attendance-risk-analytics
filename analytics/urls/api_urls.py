from django.urls import path
from analytics.views import api_views

urlpatterns = [
    path("risk-scores/", api_views.risk_score_list, name="api-risk-score-list"),
]