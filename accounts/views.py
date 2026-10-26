from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status as http_status

from .serializers import APIResponseSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    payload = {
        "status": "success",
        "message": "Smart Attendance Risk Analytics API is available.",
        "data": {"service": "smart-attendance-risk-analytics", "phase": 1},
        "errors": None,
    }
    serializer = APIResponseSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.validated_data, status=http_status.HTTP_200_OK)