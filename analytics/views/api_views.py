from rest_framework.decorators import api_view
from accounts.utils import api_response
from organization.views import visible_employees
from .serializers import RiskScoreSerializer
from .services import latest_risk_scores


@api_view(["GET"])
def risk_score_list(request):
    scores = latest_risk_scores(visible_employees(request.user))
    data = RiskScoreSerializer(scores, many=True).data
    return api_response("success", f"{len(data)} latest risk scores.", data=data)