from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework import status as http
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

from ..forms import APILoginForm, HRRegistrationForm, OTPVerifyForm, RefreshTokenForm
from ..models import User
from ..serializers import UserOutputSerializer
from ..services import OTPError, send_verification_otp, verify_otp
from ..tokens import ACCESS, REFRESH, TokenError, blacklist_token, create_token, create_token_pair, decode_token, get_user_from_payload
from ..utils import api_response, form_errors, get_role

INVALID_INPUT = "Please correct the errors below."


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def hr_register(request):
    form = HRRegistrationForm(request.data)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        user = form.save()
        send_verification_otp(user)

    data = {"user": UserOutputSerializer(user).data, "otp_expires_in_minutes": settings.OTP_LIFETIME_MINUTES}
    message = f"HR Admin account created. A 6-digit verification code was sent to {user.email}."
    return api_response("success", message, data=data, http_status=http.HTTP_201_CREATED)


def find_unverified_hr(email):
    return User.objects.filter(email__iexact=email, role=User.Role.HR_ADMIN, email_verified=False).first()


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def hr_verify_otp(request):
    form = OTPVerifyForm(request.data)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)

    user = find_unverified_hr(form.cleaned_data["email"])
    if user is None:
        return api_response("error", "No unverified HR Admin account uses this email.", errors={"email": ["Not found or already verified."]}, http_status=http.HTTP_404_NOT_FOUND)

    try:
        verify_otp(user, form.cleaned_data["otp"])
    except OTPError as error:
        return api_response("error", str(error), errors={"otp": [str(error)]}, http_status=http.HTTP_400_BAD_REQUEST)

    return api_response("success", "Email verified. Your HR Admin account is now active and you can log in.", data={"user": UserOutputSerializer(user).data})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    form = APILoginForm(request.data)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(username=form.cleaned_data["username"]).first()
    if user is None or not user.check_password(form.cleaned_data["password"]):
        return api_response("error", "Invalid username or password.", errors={"credentials": ["Invalid username or password."]}, http_status=http.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        needs_otp = get_role(user) == User.Role.HR_ADMIN and not user.email_verified
        message = "Please verify your email with the OTP before logging in." if needs_otp else "This account is inactive."
        return api_response("error", message, errors={"account": [message]}, http_status=http.HTTP_403_FORBIDDEN)

    update_last_login(None, user)
    data = {"tokens": create_token_pair(user), "user": UserOutputSerializer(user).data}
    return api_response("success", "Login successful.", data=data)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def refresh(request):
    form = RefreshTokenForm(request.data)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)

    try:
        payload = decode_token(form.cleaned_data["refresh"], REFRESH)
        user = get_user_from_payload(payload)
    except TokenError as error:
        return api_response("error", str(error), errors={"refresh": [str(error)]}, http_status=http.HTTP_401_UNAUTHORIZED)

    data = {"access": create_token(user, ACCESS), "token_type": "Bearer", "access_expires_in_minutes": settings.ACCESS_TOKEN_LIFETIME_MINUTES}
    return api_response("success", "New access token created.", data=data)


@api_view(["POST"])
def logout(request):
    form = RefreshTokenForm(request.data)
    if not form.is_valid():
        return api_response("error", INVALID_INPUT, errors=form_errors(form), http_status=http.HTTP_400_BAD_REQUEST)

    try:
        refresh_payload = decode_token(form.cleaned_data["refresh"], REFRESH)
    except TokenError as error:
        return api_response("error", str(error), errors={"refresh": [str(error)]}, http_status=http.HTTP_400_BAD_REQUEST)

    if refresh_payload["user_id"] != request.user.pk:
        return api_response("error", "This refresh token belongs to another user.", errors={"refresh": ["Token mismatch."]}, http_status=http.HTTP_400_BAD_REQUEST)

    blacklist_token(refresh_payload, request.user)
    blacklist_token(request.token_payload, request.user)
    return api_response("success", "Logged out. Both tokens are no longer valid.")